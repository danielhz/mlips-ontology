# Data-set identity in the per-paper KG: the data-set registry

Well-known data sets (ISO17, QM9, MD17, MPtrj, OC20, ...) had no entity of their own: each paper mints paper-local `mlips:TrainingDataset` nodes for the split or subset it trained on, so "which papers used MD17" could only be answered by matching label text (see `IDENTITY.md`). This file describes the registry that gives each original data set one shared entity. It was started on 2026-10-09 at the coordinator's request; it changes no paper file and adds no schema term.

## What is registered

`datasets-registry.csv`, one row per **original** data set as its authors published it, not per split:

| column | meaning |
|---|---|
| `key`, `iri` | short key and the local name under `https://w3id.org/mlips/entity/` (`ds-<Name>`) |
| `label` | the label of the shared entity |
| `size`, `size_source` | number of configurations, only where an encoded paper states it, and which paper file says so |
| `level_of_theory`, `level_source` | reference level, only where an encoded paper states it, and which one |
| `origin` | the paper that introduced the data set: a corpus paper-id, or a key of `origin-papers.csv` |
| `location` | DOI or URL of the deposit where known and checked |
| `aliases`, `exclude` | regular expressions matched against paper-local data-set labels (an `exclude` hit suppresses the match) |
| `note` | caveats |

Nothing in `size`, `level_of_theory` or `location` comes from memory: sizes and levels are copied from an encoded paper file (named in the `_source` column), deposit DOIs were resolved against DataCite, and the two plain URLs were fetched and checked to list the data set. A blank cell means "not stated by an encoded paper", not "unknown to the literature".

## Rules

1. **One shared entity per original data set**, IRI `entity:ds-<Name>` without a paper suffix. Two legacy files already use such IRIs for the original itself (`entity:ds-MPtrj` in deng2023, `entity:ds-MPF-2021-2-8` in chen2022); the registry adopts them as they are. `entity:ds-rMD17` is taken by the batatia2022 training split, so the revised MD17 set is registered as `entity:ds-revMD17`.
2. **Paper-local data sets stay as they are.** A paper's training split, subset or combination keeps its `-<paper-id>` node with its own size and sampling; it is not renamed, merged or deleted.
3. **The correspondence is recorded in a table, not in triples.** `datasets-splits.csv` (generated) lists every paper-local data-set node with the registry key or keys its label matches and a coarse relation: `original` (the registry IRI itself), `original-or-part (origin paper)`, `split-or-subset`, or `combination` (several keys). Schema 0.1.2 has no predicate for "is a split of"; one is proposed for v0.2.0, and until it is decided no triple links a split to its data set.
4. **A registered data set points to the paper that introduced it** (`schema:citation`). If that paper is in the corpus, the target is its existing article node. If not, the target is a **stub** from `origin-papers.csv`: an article entity only (title, year, DOI, a comment), kept in `shared/origin-papers.ttl`. A stub has no `mlips:BenchmarkStudy`, lives outside `papers/`, and is not counted among the corpus papers; that is what distinguishes it from the bibliographic-only files of the corpus.
5. **Look it up before describing a data set.** When encoding a paper, search `aliases` for the name the paper uses and make the local label contain the registry name, so the generated table picks it up.

## Generated files

`make datasets-registry` (`artifacts/scripts/datasets_registry.py`) writes `shared/datasets.ttl` (the shared entities), `shared/origin-papers.ttl` (the stubs) and `datasets-splits.csv`, and prints a coverage report with the unmapped label stems that more than one paper uses (candidates for new rows). `make datasets-check` fails if a generated file is stale. This is a report, not a gate on the paper files: an unmapped local data set is legitimate (most data sets are built for one paper).

The files under `shared/` are not part of the per-paper round-trip and are not read by `cq-queries/run-all.sh`, so no competency-question count moves. Whether and into which named graph they are uploaded is the uploader's decision.

## Coverage on 2026-10-09 (198 files)

21 data sets are registered. Of the 449 paper-local data-set nodes in 154 papers, 169 nodes in 49 papers map to a registered data set: MD17 61 nodes in 9 papers, rMD17 20 in 4, MPtrj 17 in 10, MD17 at coupled-cluster level 10 in 2, OC20 8 in 7, 3BPA 7 in 6, MD22 7 in 1, SPICE 6 in 5, QM9 5 in 5, ANI-1x 5 in 5, MPF.2021.2.8 5 in 4, OMat24, sAlex and MatPES 4 each, QM7-X 4 in 1, ANI-1 3, ANI-1ccx 2, HME21 2, ISO17, COLL and OC22 1 each. The remaining 280 nodes are data sets built for a single paper, apart from a handful of stems shared by two or three papers (liquid-water sets, H2/Cu, Ag-Pd) that the report lists; those need a look at the papers before they can be called the same data set.

Matching is by label and was reviewed by hand for this first version, but it is only as good as the labels: lubbers2018's "MD conformations" sets are probably MD17 and are left unmapped because the file does not say so; the smith2019ccx fine-tuning set is flagged `combination` because its label mentions ANI-1x pretraining.

## Origin papers outside the corpus

Eight registered data sets were introduced by papers that are not in Blazej's list; they are stubs in `origin-papers.csv` (metadata from Crossref and DataCite). The column `full_encoding` is the encoder's expectation, from general knowledge of the paper and not from reading the PDF, of whether the paper also reports MLIP results and would deserve the 12-question encoding once it is in the corpus:

| key | paper | introduces | full encoding? |
|---|---|---|---|
| schutt2017 | Schütt et al., SchNet: A continuous-filter convolutional neural network for modeling quantum interactions (NeurIPS 2017; arXiv:1706.08566) | ISO17 | yes (SchNet results on MD17 and ISO17; not the same paper as schutt2018) |
| christensen2020 | Christensen and von Lilienfeld, On the role of gradients for machine learning of molecular energies and forces (Mach. Learn.: Sci. Technol. 2020) | rMD17 | probably |
| chmiela2023 | Chmiela et al., Accurate global machine learning force fields for molecules with hundreds of atoms (Sci. Adv. 2023) | MD22 | yes |
| tran2023 | Tran et al., The Open Catalyst 2022 (OC22) Dataset and Challenges for Oxide Electrocatalysts (ACS Catal. 2023) | OC22 | yes |
| barrosoluque2024 | Barroso-Luque et al., Open Materials 2024 (OMat24) Inorganic Materials Dataset and Models (arXiv:2410.12771) | OMat24, sAlex | yes |
| gasteiger2020coll | Gasteiger et al., Fast and Uncertainty-Aware Directional Message Passing for Non-Equilibrium Molecules (arXiv:2011.14115) | COLL | yes |
| kaplan2025 | Kaplan et al., A Foundational Potential Energy Surface Dataset for Materials (arXiv:2503.04070) | MatPES | yes |
| hoja2021 | Hoja et al., QM7-X (Sci. Data 2021) | QM7-X | no (data descriptor) |

Two origins are approximations worth knowing about: ANI-1 points to smith2017 (the ANI-1 potential paper, in the corpus) although a separate data descriptor exists, and ANI-1x points to smith2018 although its public release is described in smith2020.

## Not done here

- No predicate links a split to its data set, and a result still does not say on which evaluation set it was measured; both are schema questions (proposal sent to the coordinator on 2026-10-09).
- Materials that merely carry a benchmark name (for example `mat-ISO17-unke2019`) are untouched; a material registry is a separate question (`IDENTITY.md`).
- The Alexandria database, QM7, DES370K, GDB-based sets and water benchmarks are not registered yet.
