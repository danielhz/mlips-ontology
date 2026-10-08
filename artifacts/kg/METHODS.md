# Method identity in the per-paper KG

How a per-paper file names the MLIP method and the trained models it talks about, so that the merged graph has one node per method however many papers use it. Fixed on 2026-10-08, before the population run over the 200-paper corpus; stays within schema 0.1.2. The registry is `methods-registry.csv`; the gate is `make methods-check` (`artifacts/scripts/check_methods.py`).

## The rules

1. **One IRI per method family, reused across papers.** A method is a functional form plus its descriptor, as the literature names it: MTP, GAP, ACE, SNAP, HDNNP, DeePMD, SchNet, NequIP, Allegro, MACE, M3GNet, CHGNet. Its IRI is `entity:<Name>` with no paper suffix, and it is listed in the registry.

2. **Look it up before minting.** Before writing a `mlips:MLIPMethod`, search the `aliases` column of `methods-registry.csv` for the name the paper uses. A hit means reuse. A miss means a new registry row first, then the file. Nothing is a method unless it is a registry row.

3. **When a new method IRI is justified.** Only for a different functional form or descriptor that the literature treats as a method of its own (CACE next to ACE, quadratic SNAP next to SNAP, Allegro next to NequIP). **Not** for: a hyperparameter choice (cutoff, level, body order, a small/medium/large size), a different training set, a retrained or fine-tuned instance, a software package or version, or a pretrained checkpoint. Those are runs, settings, implementations and trained models (rules 5–7).

4. **Identity triples are registry-fixed and repeated verbatim.** Every file that uses a method asserts `a mlips:MLIPMethod`, the registry `rdfs:label`, and, where the registry has them, `mlips:hasDescriptor` and `mlips:hasFunctionalForm` (a shared `entity:ff-<Name>` node with the registry label). Because every file writes the same strings, the merge has one label and one form per method, and each file still stands on its own for the round-trip and the listings. A registry label never contains a value that belongs to one paper.

5. **Per-paper values go on that paper's run.** Every numeric or structural choice (cutoff, level, layers, channels, learning rate, epochs) is a `mlips:HyperparameterSetting` attached to the paper's `mlips:MLIPRun` with `mlips:hasHyperparameterSetting`. The shared method only says *which* hyperparameters it has (`mlips:hasHyperparameter`), which is a union that cannot contradict itself.

6. **What a paper may add to a shared method.** Only statements that read as a union of attested uses: `mlips:hasHyperparameter`, `mlips:supportsSimulation` (demonstrated in that paper, as before), `mlips:hasImplementation`, `mlips:hasLossFunction`, `mlips:hasTrainingAlgorithm`, `mlips:inferenceComplexity`/`mlips:trainingComplexity`. The implementation, loss and algorithm nodes are paper-local (`entity:impl-<Name>-<paper-id>`, `entity:loss-…`, `entity:alg-…`), so "MTP has been trained with these losses" stays attributable to its papers by the suffix. Schema 0.1.2 has no run-level loss or optimizer property; see the v0.2.0 proposals.

7. **A pretrained or foundation model is a `mlips:TrainedModel`, not a method.** MACE-MP-0, the CHGNet release and M3GNet-MPF-2021.2.8 are models produced by a run that applies the family method. Each has one canonical model IRI in the registry (`kind=model`), with the exact checkpoint in its label; two checkpoints are two models. A paper that only evaluates such a model points `mlips:evaluatesModel` at the registry IRI and does not redeclare it. If the paper that trained it is not in the KG, the evaluating paper writes a **registry stub**: the registry run IRI with its label, `mlips:appliesMethod` and `mlips:produces`, and the model with its registry label, all verbatim, so that CQ6/CQ7 can walk result → model → run → method. When the training paper is encoded later it adds its dataset and settings to that same run.

8. **A model a paper trains itself** is paper-local: `entity:run-<key>-<paper-id>` applies the registry method and produces `entity:model-<key>-<paper-id>`. A benchmark that trains four methods on six elements has twenty-four runs and four method IRIs.

9. **Every other node is paper-local and carries the `-<paper-id>` suffix** (materials, datasets, sampling strategies, reference calculations, settings, results, metrics, candidate hyperparameters and libraries). Two files can then never merge two different things by accident. Materials are not shared yet either; see below.

## Lookup

`methods-registry.csv`, one row per canonical method (`kind=method`) or pretrained model (`kind=model`):

| column | meaning |
|---|---|
| `key`, `iri` | short key and the local name under `https://w3id.org/mlips/entity/` |
| `label` | the one label every file repeats |
| `descriptor`, `form_iri`, `form_label` | registry-fixed descriptor (a vocabulary individual) and functional form, where set |
| `method`, `run_iri` | for a model: the method its run applies, and the run IRI |
| `aliases` | names used in papers, `|`-separated; this is the column to search |
| `origin` | paper-id of the file that introduces the method, or that holds the model's full run; empty for a model known only through stubs |
| `note` | status and alignment remarks |

`make methods-check` fails if a non-legacy file declares or applies a method that is not in the registry, changes a registry label, descriptor or form, evaluates a model that is neither local nor registered, or has a paper-local subject without its suffix.

## The 20 files encoded before this convention

They are exempt from the gate (listed as `LEGACY` in the checker) and were not rewritten. New files reuse the legacy shared IRIs as they are, so the new papers join the live graph today. Bringing the 20 in line would take:

| file | now | change |
|---|---|---|
| `shapeev2016` | `entity:MTP-shapeev2016` | rename to `entity:MTP`; drop its own label and form node |
| `nitol2024nial` | `entity:MTP-nitol2024nial` | rename to `entity:MTP` (the optimised contraction is an implementation detail); move the label remark to the implementation |
| `gubaev2023`, `qi2023`, `kumar2025` | `entity:MTP`, but `entity:mtp-functional-form` has two different labels and un-suffixed local nodes (`entity:mlip-package`, `entity:setting-rcut-4_8`, `entity:aimd-sampling`, …) | one value-free form label; suffix the local nodes |
| `bartok2010` | `entity:GAP-bartok2010` (bispectrum, typed `SOAPDescriptor`) | rename to `entity:GAP`; generalise the registry label (now "… with SOAP kernel"); the bispectrum descriptor needs a vocabulary individual |
| `bartok2018si` | `entity:GAP` | suffix the local nodes; form label without paper values |
| `behler2007` | `entity:HDNNP-behler2007` | rename to `entity:HDNNP` |
| `lysogorskiy2021ace` | `entity:ACE-lysogorskiy2021ace` | rename to `entity:ACE` |
| `smith2017`, `smith2019ccx` | `entity:ANI-smith2017`, `entity:ANI-smith2019ccx` | rename both to `entity:ANI` |
| `batatia2024mp0` | `entity:MACE-MP-0` typed as a method, with its own label and form | its run applies `entity:MACE`; MACE-MP-0b3 stays the trained model `entity:model-mace-mp-0-batatia2024mp0`; drop the second method |
| `batatia2022`, `batzner2022`, `musaelian2023allegro`, `chen2022`, `deng2023`, `wang2018dpkit`, `schutt2018`, `eckhoff2021spin` | canonical IRI already | form labels carry paper values (layer counts, widths) that belong on the run; un-suffixed local nodes |

Until then the merged graph has `entity:MACE-MP-0` beside `entity:MACE`, and four MTP method nodes; results on the registry model MACE-MP-0b3 are reported by CQ6/CQ7 under `entity:MACE-MP-0`. The renames are mechanical (about 30 IRIs in 12 files) and touch vendored listings in the paper repos, which is why they wait for sign-off.

## Proposals for v0.2.0 (need a schema change, not done here)

- `mlips:hasLossFunction` and `mlips:hasTrainingAlgorithm` on `mlips:MLIPRun` (or a run-level settings node), so that a loss and an optimizer belong to the run that used them.
- A relation between a method and the method it derives from (MACE → ACE, Allegro → NequIP, quadratic SNAP → SNAP), and between a fine-tuned model and its base model.
- Shared material systems (one `entity:mat-Si`), with their own registry; today each paper declares its own.
- More `mlips:MetricProperty` individuals (phonon frequencies, elastic constants, formation and defect energies, lattice parameters). Only energy, force and stress errors can be encoded as metrics now; everything else is listed as a gap in the file.
- A unit for errors stated in eV/atom, kbar or meV/Å³ (files give the unit in the metric label and omit `mlips:hasUnit` when the vocabulary has none; values are never converted).
