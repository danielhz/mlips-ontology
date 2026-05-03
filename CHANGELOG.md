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
| `0.1.0` | V1.0    | 2026-05-?? | `10.18419/darus-NNNN` *(reserved for upload)*  | Initial public release accompanying the ISWC 2026 Resources Track paper. |

Each row is updated when a release is cut. New rows append at the
bottom; the most recent SemVer release is the topmost
non-pre-release entry.

## Releases

### 0.1.0 — 2026-05-?? *(pending DaRUS upload)*

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
