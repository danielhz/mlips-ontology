# Changelog

All notable changes to the MLIPs Ontology and the accompanying
knowledge graph and tooling are documented here.

The schema follows [Semantic Versioning](https://semver.org/): the
version IRI `https://w3id.org/mlips/<MAJOR>.<MINOR>.<PATCH>` is
bound to each release.

  * **MAJOR** — breaking changes (term removals, range changes that
    invalidate existing data, namespace moves).
  * **MINOR** — backwards-compatible extensions (new classes,
    properties, vocabulary individuals).
  * **PATCH** — annotation-only fixes (labels, comments, metadata
    errata).

## DaRUS version mapping

Each release is also deposited at DaRUS, the University of Stuttgart's
research-data repository.  DaRUS uses simple sequential
versioning (V1, V2, …) rather than SemVer.  We map the two as
follows:

  * a SemVer MAJOR or MINOR bump produces a new DaRUS major
    version (V2.0, V3.0, …);
  * a SemVer PATCH bump produces a new DaRUS minor version
    (V2.1, V2.2, …).

The mapping table below resolves any SemVer release to its DaRUS
version-specific landing page.

| SemVer  | DaRUS V | Released   | DOI                                            | Notes |
|---------|---------|------------|------------------------------------------------|-------|
| `0.1.0` | —       | 2026-05-?? | —                                              | Initial public release; superseded by 0.1.1 before the first DaRUS upload, so it has no DaRUS version of its own. |
| `0.1.1` | V1.0    | 2026-07-25 | `10.18419/darus-5948` *(draft, pending publication)* | Errata release; first version actually deposited at DaRUS (DARUS-5948). |

Each row is updated when a release is cut. New rows append at the
bottom; the most recent SemVer release is the topmost
non-pre-release entry.

## Releases

### 0.1.1 — 2026-07-25

Errata release (PATCH): data and annotation corrections since 0.1.0;
no schema term additions, removals, or semantic changes.

* **Term descriptions (`mlips.source.xhtml`):** the RDFa
  `rdfs:comment` paragraphs of 10 terms (classes `FunctionalForm`,
  `DftBasisSet`, `PseudopotentialType`, `WfMethod`, `XCFunctional`;
  object properties `candidateForVocabulary`, `dftBasisSet`,
  `pseudopotentialType`, `wfMethod`, `xcFunctional`) carried raw
  paper-only LaTeX macros that rendered verbatim on the served doc;
  rewritten to plain text matching the OWL/XML copies
  (`FunctionalForm`'s formula is now Unicode "E(cfg; ξ)").
* **Wikidata alignment (KG):** two wrong QIDs fixed —
  shapeev2016's tungsten material `wd:Q655` ("Chihuahua") →
  `wd:Q743` (tungsten); qi2023's Ti–Al material `wd:Q3520520`
  ("The Dave Days Show") → `wd:Q408746` (titanium aluminide).
* **Units (KG + vocabulary):** the per-paper files used five
  fabricated QUDT unit IRIs (`unit:MeV-PER-ATOM`,
  `unit:MeV-PER-ANGSTROM`, `unit:MilliEV`, `unit:MilliEV-PER-ATOM`,
  `unit:MilliEV-PER-ANGSTROM`, `unit:KiloCAL-PER-MOL-ANGSTROM`) —
  QUDT defines none of them, and the `MeV-` spellings read as
  MEGA-electronvolt, a 10⁹ mis-scale for the milli-eV metric
  values. Replaced by units minted in `mlips-vocab.ttl`
  (`mlips:MilliEV`, `mlips:MilliEV-PER-ATOM`,
  `mlips:MilliEV-PER-ANGSTROM`, `mlips:KiloCAL-PER-MOL-ANGSTROM`)
  as `qudt:Unit` instances with QUDT conversion annotations; all
  metric values kept exactly as the source papers print them.
* **Served resource:** the templated `rdfs:label` triples for
  reified instances moved from the concon-owned `computed` named
  graph to the consumer-owned `…/graph/labels`
  (concon ≥ v0.2.0 derives the `computed` graph itself).
* **Tooling:** the SPARQL execution needed by the round-trip
  checker, listings, and CQ harness is now self-contained
  (`artifacts/tools/sparql`: oxigraph fast path with a pure-Python
  rdflib fallback); reproducible DaRUS packaging added
  (`make darus`).

### 0.1.0 — 2026-05-?? *(not deposited; superseded by 0.1.1)*

Initial public release.

* **Schema (`mlips.owl`, `mlips.ttl`, `mlips.source.xhtml`):** 35
  classes, 53 object properties, 31 datatype properties, organised
  into three modules (Algorithm, Training Data, Benchmark).
* **Controlled vocabulary (`mlips-vocab.ttl`):** named individuals
  for XC functionals, pseudopotential families, wave-function
  methods, and software libraries; recurring entities carry
  `mlips:sameAsWikidata` triples where Wikidata coverage exists.
* **Knowledge graph (`artifacts/kg/papers/`):** 20 expert-validated
  per-paper canonical Turtle files spanning the major MLIP method
  families (BPNN, MTP, ACE, GAP, NequIP, Allegro, MACE, foundation
  models including CHGNet and MACE-MP-0).
* **SHACL shapes (`artifacts/shapes/mlips-shapes.ttl`):**
  instance-level validation; aligned with the prose semantics
  (issue-0006 in the paper repo).
* **Extraction protocol:** 11 SPARQL `CONSTRUCT` queries
  (`artifacts/kg/queries/q01.rq`–`q11.rq`) realising the round-trip
  validator over the per-paper canonicals; competency-question
  queries (`artifacts/kg/cq-queries/cq01.rq`–`cq09.rq`) realising
  the §3 CQs of the paper.
* **Tooling:** XHTML enrichment (`artifacts/scripts/enrich_xhtml.py`),
  ontology header annotation merge
  (`artifacts/scripts/merge_rdfa_into_owl.py`), local OOPS! pitfall
  scanner (`artifacts/tools/oops-run.sh`), Rust Axum content-
  negotiation server (`src/main.rs`).
* **Persistent IRI:** `https://w3id.org/mlips`
  (PURL pending registration; see PR
  <https://github.com/perma-id/w3id.org/pull/6004>).
* **Editors:** Daniel Hernández (KI Institute), Jong Hyun Jung,
  Blazej Grabowski (IMW).
* **Licence:** ontology and knowledge graph CC BY 4.0; tooling
  Apache 2.0.
