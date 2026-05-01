use axum::{
    Router,
    extract::Path,
    http::{HeaderMap, StatusCode, header},
    response::{Html, IntoResponse, Response},
    routing::get,
};
use std::path::PathBuf;

const ARTIFACTS_DIR: &str = "artifacts/ontology";

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

#[tokio::main]
async fn main() {
    let port = std::env::var("PORT").unwrap_or_else(|_| "3006".to_string());
    let addr = format!("0.0.0.0:{port}");

    let app = Router::new()
        .route("/", get(index))
        .route("/{id}/", get(serve_ontology))
        .route("/{id}/{file}", get(serve_static));

    let listener = tokio::net::TcpListener::bind(&addr).await.unwrap();
    println!("Listening on {addr}");
    axum::serve(listener, app).await.unwrap();
}
