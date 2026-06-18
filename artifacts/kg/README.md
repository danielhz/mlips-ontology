# Worked-examples KG and extraction protocol

This directory implements the per-paper extraction protocol defined in
§I.2 of the ISWC paper (`sections/appendix-examples.tex`).

## Layout

```
artifacts/kg/
├── papers/                    Per-paper canonical Turtle files.
│   └── <paper-id>.ttl
├── queries/                   The 11 CONSTRUCT queries (paper-agnostic).
│   ├── q01-bibliographic.rq
│   ├── q02-material.rq
│   ├── q03-reference-method-type.rq
│   ├── q04-reference-settings.rq
│   ├── q05-dataset.rq
│   ├── q06-sampling.rq
│   ├── q07-method.rq
│   ├── q08-hyperparameter-settings.rq
│   ├── q09-run-and-model.rq
│   ├── q10-benchmark-results.rq
│   └── q11-resources.rq
├── listings/<paper-id>/       Auto-generated, do not edit by hand.
│   └── qNN-*.ttl              One Turtle file per question, ready
│                              to embed as lstlisting in the appendix.
├── check-roundtrip.sh         Round-trip validator (paper-id).
├── build-listings.sh          Listing generator (paper-id).
└── README.md                  (this file)
```

## Workflow per paper

1. Encode the paper's facts into `papers/<paper-id>.ttl`, organised by
   the 12 questions of the protocol.
2. Run `./check-roundtrip.sh <paper-id>` to verify the 11 queries
   reproduce every triple in the canonical file. If it fails, fix the
   .ttl or revise a query.
3. Run `./build-listings.sh <paper-id>` to generate
   `listings/<paper-id>/qNN-*.ttl`.
4. Compose the paper's appendix subsection by interleaving the prose
   answers with `\lstinputlisting` directives that pull each
   `listings/<paper-id>/qNN-*.ttl`.

## Tools used

- `sparql` (Rust CLI) for CONSTRUCT execution.
- `rapper` for Turtle parsing and abbreviation.
- POSIX shell.

## Round-trip semantics

The 11 queries together must exhaustively cover every triple in the
canonical file. If a paper introduces a predicate the protocol does
not capture, the round-trip diff exposes it; the fix is either to
widen one of the existing queries (preferred) or to add a question.
The 12th question (gaps) is prose-only and is excluded.

## Naming conventions

- `<paper-id>` is `firstauthor` + `year`, e.g., `kumar2025`.
- For papers training multiple potentials over different systems or
  phases, a suffix disambiguates: `kumar2025-c14`, `kumar2025-c15`.
- Identifiers inside the .ttl use the `ex:` prefix
  (`https://w3id.org/mlips/entity/`). Shared ontology individuals
  (`mlips:Energy`, `mlips:Published`, `mlips:RMSE`, ...) are referenced
  by their canonical IRI but not redeclared.

## Simulation types (`mlips:supportsSimulation`, CQ8)

CQ8 ("which simulation types has each MLIP been used for?") was empty
until 2026-06-18 because `mlips:supportsSimulation` was defined in the
ontology but never instantiated, and `mlips-vocab.ttl` had no
`mlips:SimulationType` individuals. Both gaps are now filled. Modelling
decisions:

- **Controlled vocabulary.** Six `SimulationType` individuals live in
  `mlips-vocab.ttl`: `MolecularDynamics`, `MonteCarlo`,
  `GeometryOptimization`, `PhononCalculation`, `ThermodynamicIntegration`
  (the five named in the CQ8 text / ontology comment) plus
  `NudgedElasticBand`, added because three corpus papers demonstrate
  MLIP-driven NEB / CI-NEB minimum-energy-path calculations — a
  chain-of-states method distinct from single-structure relaxation.
- **Evidence anchor = demonstrated-in-corpus.** A type is attached only
  where a corpus paper shows that method *itself* performing the
  simulation. Capability claims ("can be used for MD"), future-work
  statements, and DFT/AIMD runs used only to generate training data do
  **not** qualify. Each PDF in `../related-work/` was read for this.
- **Attach to the method, union across papers.** Triples are asserted on
  the method individual in each per-paper file (so per-paper round-trip
  is unaffected — Q7 already pulls every predicate of an `MLIPMethod`).
  Methods shared across papers (notably `entity:MTP`, in gubaev2023 /
  qi2023 / kumar2025) accumulate the **union** of their per-paper
  evidence when the corpus is merged.

After this change CQ8 returns 38 rows over 15 methods (was 0); all other
CQ counts are unchanged. Re-run `cq-queries/run-all.sh` and
`check-roundtrip.sh <paper-id>` with the `sparql`/`rapper` toolchain to
confirm (the edits were verified here with an rdflib reimplementation of
both checks where that toolchain was unavailable).
