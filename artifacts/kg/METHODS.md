# Method identity in the per-paper KG

How a per-paper file names the MLIP method and the trained models it talks about, so that the merged graph has one node per method however many papers use it. Fixed on 2026-10-08, before the population run over the 200-paper corpus; stays within schema 0.1.2. The registry is `methods-registry.csv`; the gate is `make methods-check` (`artifacts/scripts/check_methods.py`). Since issue #4 the registry also records which method a method derives from (`mlips:derivedFromMethod`); see [Method derivation](#method-derivation).

## The rules

1. **One IRI per method family, reused across papers.** A method is a functional form plus its descriptor, as the literature names it: MTP, GAP, ACE, SNAP, HDNNP, DeePMD, SchNet, NequIP, Allegro, MACE, M3GNet, CHGNet. Its IRI is `entity:<Name>` with no paper suffix, and it is listed in the registry.

2. **Look it up before minting.** Before writing a `mlips:MLIPMethod`, search the `aliases` column of `methods-registry.csv` for the name the paper uses. A hit means reuse. A miss means a new registry row first, then the file. Nothing is a method unless it is a registry row. **When the new row is a method that this paper introduces, fill `derived_from` and `derived_from_source` from the same paper:** if the paper states that its method is built on an earlier one ("we build on", "extends", "is based on", "we augment X with"), put the parent's registry key in `derived_from` (several keys `|`-separated; a parent that is not in the registry gets its own row first) and `<paper-id>, <section>` in `derived_from_source`, and quote the sentence in the file's gaps or the run comment. Leave both empty when the paper only compares with, cites or resembles another method, and when the paper is not the one that introduced the method (`origin` empty or another paper): say in the gaps which parent the paper mentions, so it can be confirmed when the introducing paper is encoded. Never write `mlips:derivedFromMethod` in the paper file; `make methods-registry` generates it.

3. **When a new method IRI is justified.** Only for a different functional form or descriptor that the literature treats as a method of its own (CACE next to ACE, quadratic SNAP next to SNAP, Allegro next to NequIP). **Not** for: a hyperparameter choice (cutoff, level, body order, a small/medium/large size), a different training set, a retrained or fine-tuned instance, a software package or version, or a pretrained checkpoint. Those are runs, settings, implementations and trained models (rules 5–7).

4. **Identity triples are registry-fixed and repeated verbatim.** Every file that uses a method asserts `a mlips:MLIPMethod`, the registry `rdfs:label`, and, where the registry has them, `mlips:hasDescriptor` and `mlips:hasFunctionalForm` (a shared `entity:ff-<Name>` node with the registry label). Because every file writes the same strings, the merge has one label and one form per method, and each file still stands on its own for the round-trip and the listings. A registry label never contains a value that belongs to one paper.

5. **Per-paper values go on that paper's run.** Every numeric or structural choice (cutoff, level, layers, channels, learning rate, epochs) is a `mlips:HyperparameterSetting` attached to the paper's `mlips:MLIPRun` with `mlips:hasHyperparameterSetting`. The shared method only says *which* hyperparameters it has (`mlips:hasHyperparameter`), which is a union that cannot contradict itself.

6. **What a paper may add to a shared method.** Only statements that read as a union of attested uses: `mlips:hasHyperparameter`, `mlips:supportsSimulation` (demonstrated in that paper, as before), `mlips:hasImplementation`, `mlips:hasLossFunction`, `mlips:hasTrainingAlgorithm`, `mlips:inferenceComplexity`/`mlips:trainingComplexity`. The implementation, loss and algorithm nodes are paper-local (`entity:impl-<Name>-<paper-id>`, `entity:loss-…`, `entity:alg-…`), so "MTP has been trained with these losses" stays attributable to its papers by the suffix. Schema 0.1.2 has no run-level loss or optimizer property; see the v0.2.0 proposals.

7. **A pretrained or foundation model is a `mlips:TrainedModel`, not a method.** MACE-MP-0, the CHGNet release and M3GNet-MPF-2021.2.8 are models produced by a run that applies the family method. Each has one canonical model IRI in the registry (`kind=model`), with the exact checkpoint in its label; two checkpoints are two models. A paper that only evaluates such a model points `mlips:evaluatesModel` at the registry IRI and does not redeclare it. If the paper that trained it is not in the KG, the evaluating paper writes a **registry stub**: the registry run IRI with its label, `mlips:appliesMethod` and `mlips:produces`, and the model with its registry label, all verbatim, so that CQ6/CQ7 can walk result → model → run → method. When the training paper is encoded later it adds its dataset and settings to that same run.

8. **A model a paper trains itself** is paper-local: `entity:run-<key>-<paper-id>` applies the registry method and produces `entity:model-<key>-<paper-id>`. A benchmark that trains four methods on six elements has twenty-four runs and four method IRIs. When a second paper evaluates such a model, the model gets a registry row that points at its existing paper-local IRI (`origin` = the training paper); the IRI does not change. A result that the paper gives only as an aggregate over several models (one RMSE over six per-element fits) links `mlips:evaluatesModel` to each of them and says so in its `rdfs:comment`.

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
| `derived_from` | methods only: registry keys of the methods this method is built on, `|`-separated; empty unless the introducing paper states it (rule 2) |
| `derived_from_source` | the paper and location that state the derivation, e.g. `ji2026, Abstract and Introduction`; set exactly when `derived_from` is |
| `note` | status and alignment remarks |

`make methods-check` fails if a non-legacy file declares or applies a method that is not in the registry, changes a registry label, descriptor or form, evaluates a model that is neither local nor registered, or has a paper-local subject without its suffix. It also fails if any paper file (legacy ones included) asserts `mlips:derivedFromMethod`, if a `derived_from` key is not a registry method, if `derived_from` and `derived_from_source` are not set together, if the derivation has a cycle, or if `shared/methods.ttl` is stale.

## The convention as applied in the population run (2026-10-08/09)

178 files were encoded under these rules; `make methods-check` passes on all of them (56 registry methods, 19 registry models). What the run added to the picture:

- **Registry growth.** The registry went from 12 seeded families to 56 methods. A row was added whenever a paper's method matched no alias; papers that introduce a method are its `origin` (for example MatRIS, franken, MACE-QEq, CliffordIP, AIMNet2, SUS2-MLIP, BOTNet, DimeNet). PET was added on first use although its originating paper is not in the KG, so its `origin` is empty.
- **Variants are settings, consistently.** Model sizes, body orders, descriptor choices inside one package (the five DeePMD-kit descriptors, GAP with 2b+3b instead of SOAP, tabGAP), optimisers, cutoff schemes (dynamic cutoffs), frozen layers and fine-tuning from a checkpoint are all paper-local string or numeric settings on the run. Each file that does this says so in its gaps, with what a separate method would cost (one registry row and re-pointing the runs).
- **Architectures hosted by another family.** SevenNet models apply `entity:NequIP`, MatterSim models apply `entity:M3GNet`, PFP applies `entity:TeaNet`, following the registry rows of the corresponding pretrained models.
- **Pretrained models are linked only when the checkpoint is pinned.** A result on "MACE-MP-0" or "CHGNet" without a release is not linked to a registry model; the values stay in a result comment and the file's gaps say what is missing. Several files flag disagreements between a paper's description of a checkpoint and the registry label (parameter counts, training-set sizes) instead of linking.
- **Models with no matching method are left out, not forced.** Feed-forward networks on descriptors other than symmetry functions (bispectrum, GMP, PINN-style structural parameters) match neither `entity:SNAP` nor `entity:HDNNP`; they are named in the gaps of purjapun2019, montesdeoca2022 and hu2022 with "decision wanted".
- **Fine-tuning has no relation.** Schema 0.1.2 cannot say that a model starts from another model; the base model is a string-valued setting (`initialisation`). This is the most frequent schema limit met in 2025-2026 papers and is the second v0.2.0 proposal below.

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
| `lysogorskiy2021ace` | `entity:ACE` (renamed from `entity:ACE-lysogorskiy2021ace` in issue #4) | done; the file still attaches its own functional form node to `entity:ACE`, which the registry does not fix |
| `smith2017`, `smith2019ccx` | `entity:ANI-smith2017`, `entity:ANI-smith2019ccx` | rename both to `entity:ANI` |
| `batatia2024mp0` | `entity:MACE-MP-0` typed as a method, with its own label and form | its run applies `entity:MACE`; MACE-MP-0b3 stays the trained model `entity:model-mace-mp-0-batatia2024mp0`; drop the second method |
| `batatia2022`, `batzner2022`, `musaelian2023allegro`, `chen2022`, `deng2023`, `wang2018dpkit`, `schutt2018`, `eckhoff2021spin` | canonical IRI already | form labels carry paper values (layer counts, widths) that belong on the run; un-suffixed local nodes |

Until then the merged graph has `entity:MACE-MP-0` beside `entity:MACE`, and four MTP method nodes; results on the registry model MACE-MP-0b3 are reported by CQ6/CQ7 under `entity:MACE-MP-0`. The renames are mechanical (about 30 IRIs in 12 files) and touch vendored listings in the paper repos, which is why they wait for sign-off.

## Proposals for v0.2.0 (need a schema change, not done here)

- `mlips:hasLossFunction` and `mlips:hasTrainingAlgorithm` on `mlips:MLIPRun` (or a run-level settings node), so that a loss and an optimizer belong to the run that used them.
- A relation between a fine-tuned model and its base model. (The relation between a method and the method it derives from is in place since issue #4: `mlips:derivedFromMethod`.)
- Shared material systems (one `entity:mat-Si`), with their own registry; today each paper declares its own.
- More `mlips:MetricProperty` individuals (phonon frequencies, elastic constants, formation and defect energies, lattice parameters). Only energy, force and stress errors can be encoded as metrics now; everything else is listed as a gap in the file.
- A unit for errors stated in eV/atom, kbar or meV/Å³ (files give the unit in the metric label and omit `mlips:hasUnit` when the vocabulary has none; values are never converted).

## Method derivation

`mlips:derivedFromMethod` (domain and range `mlips:MLIPMethod`, a subproperty of `prov:wasDerivedFrom`; `mlips:MLIPMethod` is a `prov:Plan`) links a method to an earlier method it is built on. An edge is recorded only when the paper that introduced the derived method states it; similarity of names or architectures is not enough. The edges live in the registry (`derived_from`, `derived_from_source`) and nowhere else: `make methods-registry` (`artifacts/scripts/methods_registry.py`) generates `shared/methods.ttl`, one statement per method with its source as a comment, and `make methods-check` fails if that file is stale. Paper files never assert the property, so per-paper round-trips and listings are unchanged. Like the other files under `shared/`, `shared/methods.ttl` is not read by `cq-queries/run-all.sh`; it is read by `make consistency-check` and `make reason-kg`.

Edges confirmed against the introducing paper (issue #4, 2026-10-22):

| method | derived from | stated in |
|---|---|---|
| CACE | ACE | cheng2024, Introduction: CACE "has the same mathematical foundation as the ACE framework, so it also adopts the nice properties of ACE" |
| CACE-SOG | CACE, SOG-Net | ji2026, Abstract and Introduction: "we extend the SOG-Net framework by integrating it with the Cartesian atomic cluster expansion (CACE) descriptor" |
| sGDML | GDML | chmiela2018, Results: "The sGDML model is built on the previously introduced GDML model" |
| 4G-HDNNP | HDNNP | ko2021, Introduction and Method: "a fourth generation (4G) HDNNP", with "short-range atomic energies similar to those used in 2G-HDNNPs" |
| mHDNNP | HDNNP | eckhoff2021spin, Introduction: "employing second-generation HDNNPs [9], extending these potentials by an explicit dependence on the full spin configuration" |
| MACE-QEq | MACE | vondrak2026, Abstract and Methods: "we extend the short-range MACE model by introducing additional readout heads" |
| GemNet | DimeNet | gasteiger2021, Sec. 6: "GemNet is a significantly refined architecture based on DimeNet++" |

Candidates not recorded:

- Introducing paper not in the corpus yet (to be confirmed when it is encoded): qSNAP → SNAP (Wood and Thompson 2018), GRACE → ACE (Bochkarev et al. 2024), TACE → ACE (Xu et al. 2025), CACE-LES → CACE (Cheng 2025), 3G-HDNNP → HDNNP (Artrith et al. 2011).
- Introducing paper in the corpus but the derivation is not stated in it: none left (MACE → ACE and Allegro → NequIP are recorded on expert confirmation, below).

Edges confirmed by domain experts (2026-10-22). The introducing paper does not state these derivations in so many words, so they were recorded first as provisional (Daniel) and then confirmed by the two domain experts Daniel asked:

| method | derived from | basis |
|---|---|---|
| MACE | ACE | batatia2022 places MACE in the multi-ACE framework of its related work ("extending the ACE framework to include methods built on equivariant MPNNs") and builds its many-body features with the ACE construction. Confirmed by Jong Hyun Jung: "MACE was derived from ACE, as MACE added the message passing feature." |
| Allegro | NequIP | musaelian2023allegro shares NequIP's irreps representation ("In both the present work and in NequIP, …") and compares with it. Confirmed by Blazej Grabowski: NequIP came first, with message passing; it was slow, so the same group developed Allegro as a faster, strictly local model that approximates NequIP. The derived method removes a feature here (message passing) rather than adding one; the property covers both directions of change. |

Method families, not paper versions, are related: later papers on NequIP (e.g. framework or software updates by the same group) do not create an edge back from NequIP to Allegro, and `make methods-check` rejects cycles.

Example: every method derived, directly or not, from ACE (the merged graph, or `shared/methods.ttl` alone):

```sparql
PREFIX mlips: <https://w3id.org/mlips#>
PREFIX entity: <https://w3id.org/mlips/entity/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?method ?label WHERE {
  ?method mlips:derivedFromMethod+ entity:ACE .
  OPTIONAL { ?method rdfs:label ?label }
}
ORDER BY ?method
```

On the merged graph this returns `entity:CACE`, `entity:CACE-SOG`, `entity:MACE` and `entity:MACE-QEq`. Because the property is a subproperty of `prov:wasDerivedFrom`, a reasoner (or a query over the RDFS closure) also finds these edges through `prov:wasDerivedFrom`.
