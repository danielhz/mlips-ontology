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

## Code licensing (note)

The **ontology and knowledge-graph data** are licensed CC BY 4.0
(`LICENSE`). The repository also contains build/serving **source code**
(Python scripts, the Rust onto-server). A permissive code license
(**Apache-2.0** is the proposed default) applies to that code; the exact
choice is being finalised by the maintainers and will be recorded in a
`LICENSE-CODE` file. Until then, the code is provided for use alongside
the dataset under the same project.
