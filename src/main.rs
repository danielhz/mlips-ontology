use axum::{
    Router,
    extract::{Path, State},
    http::{HeaderMap, StatusCode, header},
    response::{Html, IntoResponse, Response},
    routing::get,
};
use minijinja::{Environment, context};
use oxigraph::io::{RdfFormat, RdfSerializer};
use oxigraph::model::GraphNameRef;
use oxigraph::sparql::QueryResults;
use oxigraph::store::Store;
use std::path::PathBuf;
use std::sync::Arc;
use tower_http::cors::{Any, CorsLayer};

const ARTIFACTS_DIR: &str = "artifacts/ontology";
const ENTITY_BASE: &str = "https://w3id.org/mlips/entity/";

struct Ontology {
    id: &'static str,
    label: &'static str,
    description: &'static str,
}

const ONTOLOGIES: &[Ontology] = &[Ontology {
    id: "mlips",
    label: "MLIPs Ontology",
    description: "An ontology for Machine Learning Interatomic Potentials.",
}];

#[derive(Clone)]
struct AppState {
    store: Arc<Store>,
    env: Arc<Environment<'static>>,
}

fn negotiate_format(headers: &HeaderMap) -> &'static str {
    let accept = headers
        .get(header::ACCEPT)
        .and_then(|v| v.to_str().ok())
        .unwrap_or("text/html");

    let types: Vec<&str> = accept
        .split(',')
        .map(|s| s.split(';').next().unwrap().trim())
        .collect();

    for t in &types {
        match *t {
            "text/turtle" => return "ttl",
            "application/rdf+xml" | "application/owl+xml" => return "owl",
            "text/html" | "application/xhtml+xml" => return "xhtml",
            _ => {}
        }
    }

    "xhtml"
}

fn content_type_for(format: &str) -> &'static str {
    match format {
        "ttl" => "text/turtle; charset=utf-8",
        "owl" => "application/rdf+xml; charset=utf-8",
        "xhtml" => "application/xhtml+xml; charset=utf-8",
        _ => "application/octet-stream",
    }
}

async fn index() -> Html<String> {
    let mut items = String::new();
    for onto in ONTOLOGIES {
        items.push_str(&format!(
            r#"<li><a href="/{id}/">{label}</a> — {desc}</li>"#,
            id = onto.id,
            label = onto.label,
            desc = onto.description,
        ));
    }

    Html(format!(
        r#"<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Ontology Server</title>
  <style>
    body {{ font-family: sans-serif; max-width: 50em; margin: 2em auto; padding: 0 1em; }}
    h1 {{ border-bottom: 1px solid #ccc; padding-bottom: 0.3em; }}
    li {{ margin: 0.5em 0; }}
  </style>
</head>
<body>
  <h1>Ontology Server</h1>
  <p>Available ontologies:</p>
  <ul>{items}</ul>
  <h2>Content negotiation</h2>
  <p>Each ontology supports content negotiation via the <code>Accept</code> header:</p>
  <ul>
    <li><code>text/html</code>, <code>application/xhtml+xml</code> — XHTML+RDFa documentation</li>
    <li><code>text/turtle</code> — Turtle serialization</li>
    <li><code>application/rdf+xml</code>, <code>application/owl+xml</code> — OWL/XML serialization</li>
  </ul>
  <h2>Entity pages</h2>
  <p>Per-paper instance data is hosted at <code>/mlips/entity/{{id}}</code>
  with the same content-negotiation across XHTML, Turtle, and RDF/XML.</p>
</body>
</html>"#
    ))
}

async fn serve_ontology(Path(id): Path<String>, headers: HeaderMap) -> Response {
    if ONTOLOGIES.iter().all(|o| o.id != id) {
        return (StatusCode::NOT_FOUND, "Ontology not found").into_response();
    }

    let format = negotiate_format(&headers);
    let file_path = PathBuf::from(ARTIFACTS_DIR).join(format!("{id}.{format}"));

    match tokio::fs::read(&file_path).await {
        Ok(content) => {
            let content_type = content_type_for(format);
            (
                StatusCode::OK,
                [(header::CONTENT_TYPE, content_type)],
                content,
            )
                .into_response()
        }
        Err(_) => (StatusCode::INTERNAL_SERVER_ERROR, "File not found").into_response(),
    }
}

async fn serve_static(Path((id, file)): Path<(String, String)>) -> Response {
    if ONTOLOGIES.iter().all(|o| o.id != id) {
        return (StatusCode::NOT_FOUND, "Ontology not found").into_response();
    }

    let file_path = PathBuf::from(ARTIFACTS_DIR).join(&file);

    let content_type = if file.ends_with(".css") {
        "text/css; charset=utf-8"
    } else {
        "application/octet-stream"
    };

    match tokio::fs::read(&file_path).await {
        Ok(content) => (
            StatusCode::OK,
            [(header::CONTENT_TYPE, content_type)],
            content,
        )
            .into_response(),
        Err(_) => (StatusCode::NOT_FOUND, "File not found").into_response(),
    }
}

// ---- Entity routes ------------------------------------------------------

/// Render an IRI as an abbreviated short form for display, when it matches
/// one of a few well-known prefixes; otherwise return the full IRI.
fn short_form(iri: &str) -> String {
    const PREFIXES: &[(&str, &str)] = &[
        ("https://w3id.org/mlips/entity/", "entity:"),
        ("https://w3id.org/mlips#", "mlips:"),
        ("http://www.w3.org/ns/mls#", "mls:"),
        ("http://www.w3.org/ns/prov#", "prov:"),
        ("http://www.w3.org/2000/01/rdf-schema#", "rdfs:"),
        ("http://www.w3.org/1999/02/22-rdf-syntax-ns#", "rdf:"),
        ("https://schema.org/", "schema:"),
        ("http://qudt.org/schema/qudt/", "qudt:"),
        ("http://qudt.org/vocab/unit/", "unit:"),
        ("https://w3id.org/mdo/core/", "mdo:"),
        ("https://w3id.org/mdo/calculation/", "mdo-calc:"),
        ("https://orcid.org/", "orcid:"),
        ("https://doi.org/", "doi:"),
    ];
    for (uri, prefix) in PREFIXES {
        if let Some(rest) = iri.strip_prefix(uri) {
            return format!("{prefix}{rest}");
        }
    }
    iri.to_string()
}

/// Local name (everything after the last / or #) for fallback display
/// when no rdfs:label is available.
fn local_name(iri: &str) -> String {
    iri.rsplit_once(['#', '/'])
        .map(|(_, last)| last.to_string())
        .unwrap_or_else(|| iri.to_string())
}

fn lookup_label(store: &Store, iri: &str) -> Option<String> {
    let q = format!(
        r#"SELECT ?l WHERE {{ <{iri}> <http://www.w3.org/2000/01/rdf-schema#label> ?l }} LIMIT 1"#
    );
    if let Ok(QueryResults::Solutions(mut sols)) = store.query(&q) {
        if let Some(Ok(s)) = sols.next() {
            if let Some(v) = s.get("l") {
                return Some(v.to_string().trim_matches('"').to_string());
            }
        }
    }
    None
}

#[derive(serde::Serialize)]
struct PropertyRow {
    predicate_iri: String,
    predicate_short: String,
    predicate_label: Option<String>,
    /// Either "iri" or "literal".
    kind: &'static str,
    /// IRI value for kind="iri".
    target_iri: String,
    /// Display text for the object cell.
    target_display: String,
    /// rdfs:label of the target IRI (kind="iri" only).
    target_label: Option<String>,
    /// Literal datatype/lang annotation for kind="literal".
    annotation: String,
}

fn forward_rows(store: &Store, subject_iri: &str) -> Vec<PropertyRow> {
    let q = format!(
        r#"SELECT ?p ?o WHERE {{ <{subject_iri}> ?p ?o }} ORDER BY ?p ?o"#
    );
    let mut rows = Vec::new();
    if let Ok(QueryResults::Solutions(sols)) = store.query(&q) {
        for sol in sols.flatten() {
            let p = sol.get("p").map(|t| t.to_string()).unwrap_or_default();
            let o = sol.get("o").map(|t| t.to_string()).unwrap_or_default();
            let p_iri = strip_iri(&p);
            let predicate_label = lookup_label(store, &p_iri);
            let predicate_short = short_form(&p_iri);
            if o.starts_with('<') && o.ends_with('>') {
                let iri = strip_iri(&o);
                let label = lookup_label(store, &iri);
                let display = label.clone().unwrap_or_else(|| short_form(&iri));
                rows.push(PropertyRow {
                    predicate_iri: p_iri,
                    predicate_short,
                    predicate_label,
                    kind: "iri",
                    target_iri: iri.clone(),
                    target_display: display,
                    target_label: label,
                    annotation: String::new(),
                });
            } else {
                let (display, annotation) = parse_literal(&o);
                rows.push(PropertyRow {
                    predicate_iri: p_iri,
                    predicate_short,
                    predicate_label,
                    kind: "literal",
                    target_iri: String::new(),
                    target_display: display,
                    target_label: None,
                    annotation,
                });
            }
        }
    }
    rows
}

#[derive(serde::Serialize)]
struct ReverseRow {
    source_iri: String,
    source_short: String,
    source_label: Option<String>,
    predicate_iri: String,
    predicate_short: String,
    predicate_label: Option<String>,
}

fn reverse_rows(store: &Store, object_iri: &str) -> Vec<ReverseRow> {
    let q = format!(
        r#"SELECT ?s ?p WHERE {{ ?s ?p <{object_iri}> }} ORDER BY ?p ?s"#
    );
    let mut rows = Vec::new();
    if let Ok(QueryResults::Solutions(sols)) = store.query(&q) {
        for sol in sols.flatten() {
            let s = sol.get("s").map(|t| t.to_string()).unwrap_or_default();
            let p = sol.get("p").map(|t| t.to_string()).unwrap_or_default();
            if !s.starts_with('<') || !s.ends_with('>') {
                continue;
            }
            let s_iri = strip_iri(&s);
            let p_iri = strip_iri(&p);
            rows.push(ReverseRow {
                source_iri: s_iri.clone(),
                source_short: short_form(&s_iri),
                source_label: lookup_label(store, &s_iri),
                predicate_iri: p_iri.clone(),
                predicate_short: short_form(&p_iri),
                predicate_label: lookup_label(store, &p_iri),
            });
        }
    }
    rows
}

/// Strip <...> wrapper from an Oxigraph-formatted IRI string.
fn strip_iri(s: &str) -> String {
    s.trim_start_matches('<').trim_end_matches('>').to_string()
}

/// Split an Oxigraph-formatted literal "value"^^<dt> or "value"@lang into a
/// display string and a datatype/language annotation.
fn parse_literal(literal: &str) -> (String, String) {
    if let Some((value, rest)) = literal.rsplit_once('"') {
        let value = value.trim_start_matches('"').to_string();
        if let Some(dt) = rest.strip_prefix("^^") {
            return (value, format!("^^{}", short_form(&strip_iri(dt))));
        } else if let Some(lang) = rest.strip_prefix('@') {
            return (value, format!("@{lang}"));
        }
        return (value, String::new());
    }
    (literal.to_string(), String::new())
}

fn types_of(store: &Store, subject_iri: &str) -> Vec<(String, String)> {
    let q = format!(
        r#"SELECT ?t WHERE {{ <{subject_iri}> a ?t }} ORDER BY ?t"#
    );
    let mut out = Vec::new();
    if let Ok(QueryResults::Solutions(sols)) = store.query(&q) {
        for sol in sols.flatten() {
            if let Some(term) = sol.get("t") {
                let s = term.to_string();
                if s.starts_with('<') {
                    let iri = strip_iri(&s);
                    out.push((iri.clone(), short_form(&iri)));
                }
            }
        }
    }
    out
}

async fn serve_entity(
    Path(id): Path<String>,
    State(state): State<AppState>,
    headers: HeaderMap,
) -> Response {
    let subject_iri = format!("{ENTITY_BASE}{id}");

    let format = negotiate_format(&headers);

    // Existence check: at least one forward or reverse triple.
    let has_forward = format!(
        r#"ASK {{ <{subject_iri}> ?p ?o }}"#
    );
    let has_reverse = format!(
        r#"ASK {{ ?s ?p <{subject_iri}> }}"#
    );
    let exists = matches!(state.store.query(&has_forward), Ok(QueryResults::Boolean(true)))
        || matches!(state.store.query(&has_reverse), Ok(QueryResults::Boolean(true)));

    if !exists {
        return entity_not_found(&state, &subject_iri, format);
    }

    match format {
        "ttl" | "owl" => {
            // CBD: forward triples only (per design decision 1 in issue-0012).
            let q = format!(
                r#"CONSTRUCT {{ <{subject_iri}> ?p ?o }} WHERE {{ <{subject_iri}> ?p ?o }}"#
            );
            let result = state.store.query(&q);
            let triples = match result {
                Ok(QueryResults::Graph(triples)) => triples,
                _ => {
                    return (StatusCode::INTERNAL_SERVER_ERROR, "Query error").into_response();
                }
            };
            let rdf_format = if format == "ttl" {
                RdfFormat::Turtle
            } else {
                RdfFormat::RdfXml
            };
            let mut buf: Vec<u8> = Vec::new();
            let mut serializer = RdfSerializer::from_format(rdf_format).for_writer(&mut buf);
            for t in triples.flatten() {
                if serializer.serialize_triple(&t).is_err() {
                    return (StatusCode::INTERNAL_SERVER_ERROR, "Serialize error")
                        .into_response();
                }
            }
            if serializer.finish().is_err() {
                return (StatusCode::INTERNAL_SERVER_ERROR, "Finish error").into_response();
            }
            (
                StatusCode::OK,
                [(header::CONTENT_TYPE, content_type_for(format))],
                buf,
            )
                .into_response()
        }
        _ => {
            // HTML view (default).
            let forward = forward_rows(&state.store, &subject_iri);
            let reverse = reverse_rows(&state.store, &subject_iri);
            let types = types_of(&state.store, &subject_iri);
            let label = lookup_label(&state.store, &subject_iri);

            let tmpl = match state.env.get_template("entity") {
                Ok(t) => t,
                Err(_) => return (StatusCode::INTERNAL_SERVER_ERROR, "Template missing")
                    .into_response(),
            };
            let html = match tmpl.render(context! {
                subject_iri => &subject_iri,
                subject_short => short_form(&subject_iri),
                subject_local => local_name(&subject_iri),
                label => label,
                types => types.iter().map(|(iri, short)| context! { iri => iri, short => short }).collect::<Vec<_>>(),
                forward => &forward,
                reverse => &reverse,
                forward_count => forward.len(),
                reverse_count => reverse.len(),
            }) {
                Ok(s) => s,
                Err(e) => return (StatusCode::INTERNAL_SERVER_ERROR, format!("Render error: {e}"))
                    .into_response(),
            };
            (
                StatusCode::OK,
                [(header::CONTENT_TYPE, content_type_for("xhtml"))],
                html,
            )
                .into_response()
        }
    }
}

fn entity_not_found(state: &AppState, subject_iri: &str, format: &str) -> Response {
    if format == "ttl" || format == "owl" {
        return (StatusCode::NOT_FOUND, format!("No triples for <{subject_iri}>"))
            .into_response();
    }
    let body = match state
        .env
        .get_template("entity_not_found")
        .and_then(|t| t.render(context! { subject_iri => subject_iri }))
    {
        Ok(s) => s,
        Err(_) => format!(
            "<!DOCTYPE html><html><body><h1>404 Not Found</h1><p>No triples for <code>{}</code> in the current release.</p></body></html>",
            html_escape::encode_text(subject_iri),
        ),
    };
    (
        StatusCode::NOT_FOUND,
        [(header::CONTENT_TYPE, content_type_for("xhtml"))],
        body,
    )
        .into_response()
}

// ---- Templates ----------------------------------------------------------

const ENTITY_TEMPLATE: &str = r##"<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{{ subject_short }} — MLIPs entity</title>
  <style>
    body { font-family: sans-serif; max-width: 70em; margin: 2em auto; padding: 0 1em; color: #222; }
    h1 { border-bottom: 1px solid #ccc; padding-bottom: 0.3em; word-break: break-all; }
    h2 { margin-top: 1.5em; border-bottom: 1px solid #eee; }
    .iri { font-family: monospace; word-break: break-all; }
    .label { font-style: italic; color: #555; margin: 0.4em 0 0.8em; }
    table { border-collapse: collapse; width: 100%; margin: 0.5em 0; }
    th, td { text-align: left; padding: 0.4em 0.6em; border-bottom: 1px solid #eee; vertical-align: top; }
    th { background: #f7f7f7; font-weight: 600; }
    .pred { white-space: nowrap; }
    .literal { white-space: pre-wrap; }
    .annot { color: #888; font-size: 0.85em; margin-left: 0.4em; }
    .nolabel { font-family: monospace; font-style: italic; color: #888; }
    .types span { display: inline-block; margin: 0 0.4em 0.2em 0; padding: 0.15em 0.5em; background: #eef; border-radius: 0.4em; font-family: monospace; }
    .formats { font-size: 0.9em; margin-top: 2em; color: #555; }
    .formats a { font-family: monospace; }
    .empty { color: #888; font-style: italic; }
  </style>
</head>
<body>
  <h1>{{ subject_short }}</h1>
  <p class="iri">&lt;{{ subject_iri }}&gt;</p>
  {% if label %}<p class="label">{{ label }}</p>{% endif %}
  {% if types %}
  <p class="types">
    <strong>Type:</strong>
    {% for t in types %}<span><a href="{{ t.iri }}">{{ t.short }}</a></span>{% endfor %}
  </p>
  {% endif %}

  <h2>Forward properties ({{ forward_count }})</h2>
  {% if forward %}
  <table>
    <thead><tr><th>Predicate</th><th>Value</th></tr></thead>
    <tbody>
    {% for r in forward %}
      <tr>
        <td class="pred">
          <a href="{{ r.predicate_iri }}" title="{{ r.predicate_iri }}">
            {% if r.predicate_label %}{{ r.predicate_label }}{% else %}<span class="nolabel">{{ r.predicate_short }}</span>{% endif %}
          </a>
        </td>
        <td>
          {% if r.kind == "iri" %}
            <a href="{{ r.target_iri }}" title="{{ r.target_iri }}">
              {% if r.target_label %}{{ r.target_label }}{% else %}<span class="nolabel">{{ r.target_display }}</span>{% endif %}
            </a>
          {% else %}
            <span class="literal">{{ r.target_display }}</span>{% if r.annotation %}<span class="annot">{{ r.annotation }}</span>{% endif %}
          {% endif %}
        </td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  {% else %}<p class="empty">No forward triples.</p>{% endif %}

  <h2>Reverse properties ({{ reverse_count }})</h2>
  {% if reverse %}
  <table>
    <thead><tr><th>Subject</th><th>Predicate</th></tr></thead>
    <tbody>
    {% for r in reverse %}
      <tr>
        <td>
          <a href="{{ r.source_iri }}" title="{{ r.source_iri }}">
            {% if r.source_label %}{{ r.source_label }}{% else %}<span class="nolabel">{{ r.source_short }}</span>{% endif %}
          </a>
        </td>
        <td class="pred">
          <a href="{{ r.predicate_iri }}" title="{{ r.predicate_iri }}">
            {% if r.predicate_label %}{{ r.predicate_label }}{% else %}<span class="nolabel">{{ r.predicate_short }}</span>{% endif %}
          </a>
        </td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  {% else %}<p class="empty">No reverse triples.</p>{% endif %}

  <p class="formats">
    Other formats:
    <a href="{{ subject_iri }}" onclick="event.preventDefault(); fetch('{{ subject_iri }}', {headers: {Accept: 'text/turtle'}}).then(r=>r.text()).then(t=>{document.body.innerText=t}); return false;">Turtle</a> ·
    <a href="{{ subject_iri }}" onclick="event.preventDefault(); fetch('{{ subject_iri }}', {headers: {Accept: 'application/rdf+xml'}}).then(r=>r.text()).then(t=>{document.body.innerText=t}); return false;">RDF/XML</a>
    (or send <code>Accept: text/turtle</code> / <code>Accept: application/rdf+xml</code> with curl).
  </p>
</body>
</html>"##;

const ENTITY_NOT_FOUND_TEMPLATE: &str = r##"<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>404 — entity not in current release</title>
  <style>
    body { font-family: sans-serif; max-width: 50em; margin: 2em auto; padding: 0 1em; }
    h1 { border-bottom: 1px solid #ccc; padding-bottom: 0.3em; }
    code { background: #f4f4f4; padding: 0.05em 0.3em; border-radius: 0.2em; word-break: break-all; }
  </style>
</head>
<body>
  <h1>404 — entity not in current release</h1>
  <p>No triples were found for <code>&lt;{{ subject_iri }}&gt;</code>
  in the current Knowledge Graph release.</p>
  <p>The MLIPs Knowledge Graph encodes a curated corpus of 20 papers; an
  entity IRI under this prefix may exist in a future release but is not
  currently dereferenced.</p>
  <p><a href="/">Server index</a> ·
     <a href="/mlips/">MLIPs ontology</a></p>
</body>
</html>"##;

// ---- Store loading ------------------------------------------------------

fn load_store() -> std::io::Result<Store> {
    let store = Store::new().map_err(|e| std::io::Error::other(e.to_string()))?;

    // Load the ontology and its alignments.
    load_ttl(&store, "artifacts/ontology/mlips.ttl")?;

    // Load the controlled vocabulary.
    load_ttl(&store, "artifacts/kg/mlips-vocab.ttl")?;

    // Load every paper canonical.
    let papers_dir = std::path::Path::new("artifacts/kg/papers");
    if let Ok(entries) = std::fs::read_dir(papers_dir) {
        let mut paths: Vec<_> = entries
            .flatten()
            .map(|e| e.path())
            .filter(|p| p.extension().is_some_and(|x| x == "ttl"))
            .collect();
        paths.sort();
        for p in paths {
            load_ttl(&store, p.to_str().unwrap())?;
        }
    }

    // Materialise computed labels for reified-relation instances. The
    // CONSTRUCT mirrors artifacts/kg/computed/labels.rq and produces the
    // carrier-aware "<hp> = <value> [<unit>] for <carrier>" labels that
    // make the entity pages much more readable.
    let labels_rq = std::fs::read_to_string("artifacts/kg/computed/labels.rq").ok();
    if let Some(q) = labels_rq {
        if let Ok(QueryResults::Graph(triples)) = store.query(&q) {
            for t in triples.flatten() {
                let _ = store.insert(t.as_ref().in_graph(GraphNameRef::DefaultGraph));
            }
        }
    }

    let count = store
        .query("SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }")
        .ok();
    if let Some(QueryResults::Solutions(mut sols)) = count {
        if let Some(Ok(s)) = sols.next() {
            if let Some(n) = s.get("n") {
                println!("Loaded {n} triples into the in-memory store.");
            }
        }
    }
    Ok(store)
}

fn load_ttl(store: &Store, path: &str) -> std::io::Result<()> {
    let bytes = std::fs::read(path)?;
    store
        .load_from_reader(RdfFormat::Turtle, &bytes[..])
        .map_err(|e| std::io::Error::other(e.to_string()))?;
    Ok(())
}

// ---- main ---------------------------------------------------------------

#[tokio::main]
async fn main() {
    let port = std::env::var("PORT").unwrap_or_else(|_| "3006".to_string());
    let addr = format!("0.0.0.0:{port}");

    let store = match load_store() {
        Ok(s) => s,
        Err(e) => {
            eprintln!("Failed to load Oxigraph store: {e}");
            std::process::exit(1);
        }
    };

    let mut env = Environment::new();
    env.add_template("entity", ENTITY_TEMPLATE).expect("entity template");
    env.add_template("entity_not_found", ENTITY_NOT_FOUND_TEMPLATE)
        .expect("not-found template");

    let state = AppState {
        store: Arc::new(store),
        env: Arc::new(env),
    };

    // Permissive CORS: the ontology is public Linked Open Data, and
    // browser-based tools such as WebVOWL (hosted at service.tib.eu)
    // need to fetch our serialisations cross-origin. Allow any origin
    // for GET/HEAD; do not echo credentials.
    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    let app = Router::new()
        .route("/", get(index))
        .route("/mlips/entity/{id}", get(serve_entity))
        .route("/{id}/", get(serve_ontology))
        .route("/{id}/{file}", get(serve_static))
        .with_state(state)
        .layer(cors);

    let listener = tokio::net::TcpListener::bind(&addr).await.unwrap();
    println!("Listening on {addr}");
    axum::serve(listener, app).await.unwrap();
}
