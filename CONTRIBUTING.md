# Contributing to the MLIPs Ontology

Thanks for your interest in the **Ontology for Machine Learning
Interatomic Potentials** (`https://w3id.org/mlips`). Contributions —
new terms, corrections, additional encoded papers, alignment fixes —
are welcome.

## Where to start: issues

File issues on the GitHub tracker:
<https://github.com/danielhz/mlips-ontology/issues>.

Good issues to open:

- **Propose a term** — a class, property, or controlled-vocabulary
  individual the ontology is missing. Say what it models, where it fits
  (which module), and a real paper that needs it.
- **Report a modelling problem** — an axiom that is wrong, too strong,
  or missing.
- **Suggest an alignment** — a mapping to an external vocabulary
  (schema.org, PROV-O, QUDT, ML-Schema, MDO, …).

## Source of truth and the build

The ontology has a **single hand-edited source**:
`artifacts/ontology/mlips.source.xhtml` (XHTML + RDFa, with the term
axioms in `<pre class="owl-xml">` blocks). The OWL and Turtle
serialisations (`mlips.owl`, `mlips.ttl`) and the published HTML
(`mlips.xhtml`) are **generated** — do **not** hand-edit them.

```sh
make ontology      # regenerate mlips.{xhtml,owl,ttl} from the source
```

Python build dependencies install automatically into a local, gitignored
`.venv` (pinned in `requirements.lock`); no global install is needed.

## The knowledge graph and its encoding protocol

Per-paper data lives in `artifacts/kg/papers/<paper-id>.ttl`, encoded
with the round-trip-validated protocol documented in
`artifacts/kg/README.md`. Every paper file must reproduce exactly under
the extraction queries:

```sh
artifacts/kg/check-roundtrip.sh <paper-id>     # must PASS
artifacts/kg/cq-queries/run-all.sh             # competency-question counts
```

Shared controlled-vocabulary individuals (functionals, libraries,
simulation types, …) go in `artifacts/kg/mlips-vocab.ttl`, not in
per-paper files.

## Submitting a change

1. Branch from `main`; keep the change focused.
2. Regenerate any affected generated artifacts (`make ontology`) and
   commit them alongside the source.
3. Make sure the round-trip check, the competency-question harness, and
   (where modules/shapes are touched) SHACL validation pass.
4. Open a pull request describing the change and the issue it addresses.

## Licensing of contributions

The ontology and knowledge graph are released under **CC BY 4.0** (see
`LICENSE`). By contributing, you agree your contributions are provided
under the same terms. See `GOVERNANCE.md` for the code-licensing note.
