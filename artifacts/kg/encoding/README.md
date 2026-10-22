# Encoding inputs of the per-paper KG

Each paper encoded since the population run of ranks 201–700 (2026-10-22) has a hand-written input here, and its Turtle file `artifacts/kg/papers/<id>.ttl` is generated from it:

- `specs/<id>.yaml` — the facts the encoder extracted from the paper, organised by the 12 questions of the protocol (`artifacts/kg/README.md`);
- `bib/<id>.json` — the author list (names, ORCIDs) deposited with the DOI at Crossref or DataCite, fetched once when the spec is started and kept so that generation needs no network.

`make encode PAPERS="<id> …"` regenerates papers (`artifacts/scripts/encode_paper.py`); `make encoding-check` regenerates every paper that has a spec in memory and fails if a committed Turtle file differs. A paper file is therefore never edited by hand once it has a spec: change the spec and regenerate. Generation reads only committed files (the spec, the bib cache, `methods-registry.csv`, `datasets-registry.csv`) and appends the result-label block of `add_result_labels.py`, so the output is exactly the committed file.

The inputs hold extracted values, short quotes and locations only, no copied paragraphs, because the repository is public. The 178 papers of the run of 2026-10-08/09 and the 20 earlier ones have no committed input (their files were written before inputs were kept, and several have been edited since).

## Spec format

Keys follow the 12 questions. Names of methods and pretrained models are registry keys (`artifacts/kg/METHODS.md`); every other key is local to the file and becomes part of a `-<id>`-suffixed IRI.

| key | content |
|---|---|
| `id` | the paper id |
| `source` | the corpus manifest row as read (rank, year, first author, title, venue, DOI, relevance class, arXiv id, PDF version and SHA-256), copied by `encode_paper.py --new` |
| `authors` | optional; replaces the bib cache when the deposited metadata are wrong (each `{given, family, orcid}`) |
| `title` | optional; replaces the deposited title |
| `study_label`, `scope` | the study label, and the encoding scope written into the file header |
| `materials` | `key: {label, formula, class, feature, comment, wikidata}` |
| `reference` | `key: {type: DFT\|WF\|REF, code, xc, pp, dft_basis, wf, basis, cutoff, kpoints, comment}`; vocabulary values by name, or `{local: <label>, comment}` for a candidate individual |
| `sampling`, `datasets` | sampling strategies; data sets `key: {label, materials, properties, provenance, n, calc, sampling, comment}` |
| `hyperparameters`, `methods` | candidate hyperparameters; per registry method the hyperparameters, loss, algorithm, implementation and demonstrated simulation types |
| `runs` | `key: {label, method, dataset, settings, model, registry, gpuHours, trainingDuration, trainingHardware, base_model}` |
| `external_models` | registry models evaluated but not trained here |
| `results` | `[{key, model, material, comment, metrics, role, eval_data}]`, each metric `[type, property, value, unit, label, location]` |
| `timings`, `resources` | inference timings (below); prose for Q11 |
| `gaps` | Q12, one item per gap |

## Fields kept in the input until the schema has terms for them

These are decided to come (programme questions on evaluation sets, fine-tuning, issue #2 on timings and source locators). They are recorded now so that a later issue only adds the term and regenerates, and no paper is read twice. They do not appear in the generated Turtle; the Q12 section of every generated file says that they are held here.

1. **Evaluation role and data of a result.**
   - `role`: `training`, `validation`, `test` or `external` (a benchmark set from outside the paper's own split), as the paper states it. Omitted when the paper does not say; never assumed to be `test`.
   - `eval_data`: `{label, registry, location}`. The label names the test set or split as the paper does. `registry` is the key in `datasets-registry.csv` when it is a registered data set (for example `rMD17`, `MPtrj`), checked by the generator.
2. **Base model of a fine-tuned or distilled model.** `base_model` on the run that produced it: `{registry: <registry model key>}`, `{run: <local run key>}`, or `{label: <checkpoint as named in the paper>}` when it is neither; `relation: fine-tuned | distilled` and `location` are optional.
3. **Inference timings.** `timings`: a list of `{model, system, atoms, value, unit, per_atom_us, hardware, result, location}`. `system` is the timed system and `atoms` its size, both as the paper gives them; `value` and `unit` are the figure as printed and `per_atom_us` its conversion to microseconds per atom, only when the paper's figure allows it without assumptions. `result` names the BenchmarkResult of the same model on the timed system: the generator then writes `mlips:inferenceTimePerAtom` and `mlips:inferenceHardware` on that result (issue #1). Timings without such a result have `result` empty and stay in the input (issue #2 may make them timing-only results).
4. **Source location of each value.** A table, figure, equation or section, as `location` in the dicts above, as the sixth element of a metric, or by writing a scalar as `{v: <value>, loc: <location>}` (settings, data-set sizes, training cost). The generator uses the value and ignores the location.
