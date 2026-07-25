# MLIPs Ontology — Schema, Knowledge Graph, and Tooling

This repository hosts the source artefacts behind the **MLIPs
Ontology**, a Semantic Web resource for describing Machine Learning
Interatomic Potentials (training data, methods, benchmarks). It is
the upstream dataset/tooling repo for the ISWC 2026 paper and its
planned sequels (SWJ, npj Comp. Mat.); each paper's prose lives in
its own sibling repo and consumes generated artefacts from here via
a vendoring step.

## Layout

```
artifacts/
├── ontology/                # Schema source-of-truth.
│   ├── mlips.xhtml          #   XHTML+RDFa source (edit here).
│   ├── mlips.owl            #   Generated RDF/XML.
│   └── mlips.ttl            #   Generated Turtle.
├── kg/                      # Per-paper canonical KG and protocol.
│   ├── papers/<id>.ttl      #   Encoded paper KGs (one per paper).
│   ├── queries/q01..q11.rq  #   The 11 protocol CONSTRUCT queries.
│   ├── mlips-vocab.ttl      #   Controlled vocabulary individuals.
│   ├── build-listings.sh    #   Generate per-question Turtle fragments.
│   ├── check-roundtrip.sh   #   Round-trip validator.
│   └── listings/            #   Build output (gitignored).
├── shapes/
│   └── mlips-shapes.ttl     # SHACL shapes for schema validation.
├── scripts/
│   └── generate_term_appendix.py  # Generates the term appendices
│                                  # (vendored to paper repo).
├── tools/
│   ├── ontology_to_dot.py   # Render ontology as Graphviz DOT.
│   ├── dot_to_tikz.py       # Convert DOT to TikZ for LaTeX.
│   └── render_figures.sh    # Pipeline entry point.
└── doc/
    └── mlips-ontology.org   # Human-readable ontology documentation.
```

## What this repo produces

Three classes of artefact end up vendored into a paper repo:

1. **Per-question Turtle fragments** under `artifacts/kg/listings/`
   — produced by `build-listings.sh` from each canonical
   `papers/<id>.ttl`. Vendored to `artifacts/kg/listings/` in the
   paper repo, included via `\lstinputlisting` in
   `sections/catalogue/`.

2. **Term appendices** (`appendix-classes.tex`,
   `appendix-object-properties.tex`, `appendix-data-properties.tex`)
   — produced by `scripts/generate_term_appendix.py` from
   `mlips.ttl` into `dist/sections/`. Vendored into the paper repo
   under `sections/` as `\input` targets.

3. **Rendered figures** (`mlips-overview.tex` and friends) —
   produced by `tools/` from `mlips.ttl` into `artifacts/figures/`.
   Vendored into the paper repo under `artifacts/figures/`.

The paper repo's `make sync-from-dataset` target performs the
vendoring and writes the upstream commit hash to its
`data-pinning.json`. This decouples Overleaf compile-time from any
tooling installation — the paper repo is buildable from a fresh
clone with only LaTeX.

## Workflow

### Encoding a new paper

```sh
# 1. Encode the paper into a canonical .ttl (see kg/README.md).
$EDITOR artifacts/kg/papers/<paper-id>.ttl

# 2. Verify the 11 CONSTRUCT queries reproduce every triple.
./artifacts/kg/check-roundtrip.sh <paper-id>

# 3. Regenerate the per-question listings.
./artifacts/kg/build-listings.sh <paper-id>

# 4. Commit canonical + listings outputs.
```

### Releasing a vendor-able snapshot

```sh
make release          # roundtrip-check + listings + term-appendices + figures
git commit -am "Release: ..."
# (optionally) git tag v<n>
```

In a sibling paper repo:

```sh
make sync-from-dataset DATASET_PATH=/abs/path/to/this/repo
```

## Tooling dependencies

- `rapper` (raptor2) — Turtle parsing and serialisation.
- SPARQL execution (round-trip checker, listings, CQ harness) is
  self-contained: the scripts use an installed `sparql` CLI if one is
  on the PATH, and otherwise fall back to the bundled
  `artifacts/tools/sparql` shim — `oxigraph_server` when available,
  else a pure-Python rdflib driver on the build venv (no extra
  install needed beyond `make venv`).
- Python 3 — `scripts/generate_term_appendix.py` and `tools/`.
- Saxon-HE — XHTML→OWL extraction (`make ontology`).
- Graphviz — `tools/render_figures.sh`.

## See also

- `agent-chat/` in the paper repo — discussion threads and the
  `issues/` tracker for ongoing data/schema work.
- `artifacts/doc/mlips-ontology.org` — human-readable schema doc.
- `artifacts/kg/README.md` — protocol details for the per-paper
  encoding workflow.

## License, citation, and governance

- **License** — two products, two licenses: the *ontology and knowledge
  graph* (`artifacts/`) under [CC BY 4.0](LICENSE) (matching the
  `dcterms:license` in the ontology header); the *software* (`src/`,
  `artifacts/scripts/`, `tools/`, `Makefile`) under dual
  [MIT](LICENSE-MIT) OR [Apache-2.0](LICENSE-APACHE). See
  [`GOVERNANCE.md`](GOVERNANCE.md).
- **Citation** — [`CITATION.cff`](CITATION.cff) (GitHub shows a "Cite
  this repository" button). A `preferred-citation` to the ISWC paper
  will be added once it is published.
- **Contributing** — [`CONTRIBUTING.md`](CONTRIBUTING.md): filing issues,
  proposing terms, and the XHTML-source-of-truth → regenerate workflow.
- **Governance, versioning, maintenance** — [`GOVERNANCE.md`](GOVERNANCE.md).
