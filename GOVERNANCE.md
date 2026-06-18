# Governance and maintenance

This document states how the **Ontology for Machine Learning Interatomic
Potentials** (`https://w3id.org/mlips`) is maintained, so that users and
reviewers can rely on it as a living resource.

## Maintainers

The resource is maintained by the authors at the University of Stuttgart
(Institute for Artificial Intelligence and Institute for Materials
Science), with collaborators at Ruhr-Universität Bochum and the
Max-Planck-Institut for Sustainable Materials. Daniel Hernández is the
lead maintainer; see `CITATION.cff` for the full author list.

Contact and issue tracker: <https://github.com/danielhz/mlips-ontology>.

## Versioning policy

- The ontology is versioned with **semantic versioning** (`MAJOR.MINOR.PATCH`);
  the current version is **0.1.0**.
  - **MAJOR** — incompatible changes to existing term IRIs or semantics
    (renames, removals, domain/range narrowing).
  - **MINOR** — backward-compatible additions (new classes, properties,
    controlled-vocabulary individuals, newly encoded papers).
  - **PATCH** — documentation, annotations, and non-semantic fixes.
- Each release carries an `owl:versionInfo` and an `owl:versionIRI`
  (`https://w3id.org/mlips/<version>`); the unversioned IRI
  `https://w3id.org/mlips` always resolves to the latest release.
- Term IRIs are **stable**: published terms are not renamed or removed
  within a MAJOR version; deprecated terms are marked `owl:deprecated`
  and retained.

## Release cadence

Releases are made as the corpus and schema grow — driven by the
encoded-paper corpus and the planned journal extensions (SWJ, npj). We
aim for at least one reviewed release per significant addition rather
than on a fixed calendar; each release passes the round-trip check, the
competency-question harness, the SHACL module shape, and an OWL 2 DL
reasoner consistency check before publication.

## Change process

The XHTML source is authoritative; OWL/TTL are regenerated (see
`CONTRIBUTING.md`). Changes flow through pull requests with the
validation gates above green. Substantive modelling changes are
discussed on the issue tracker first.

## Licensing

This repository has **two products under two licenses**:

- **Ontology and knowledge graph** (`artifacts/`) — **CC BY 4.0**
  (`LICENSE`), matching the `dcterms:license` in the ontology header.
- **Software** (`src/`, `artifacts/scripts/`, `tools/`, `Makefile`) —
  dual **MIT OR Apache-2.0** at the user's option (`LICENSE-MIT`,
  `LICENSE-APACHE`); declared as `license = "MIT OR Apache-2.0"` in
  `Cargo.toml`. This is the idiomatic Rust-ecosystem choice: the
  permissive MIT option plus the Apache-2.0 explicit patent grant.
