# Discrepancy dossier — paper-text KG vs dataset artifacts

One entry per disagreement between what the papers say (the `…/graph/kg`
triples) and what the collected dataset artifacts contain (the
`…/graph/datasets` triples). Policy (EXTRACTION-DESIGN.md §1/§5):
nothing is silently overwritten — both values stay queryable in their
graphs; entries are closed only by an explicit decision recorded here.

Status values: OPEN (needs a decision), DOCUMENTED (no KG change
needed; both values are correct in their own graph), DECIDED
(resolution recorded, KG edit done or scheduled).

## 1. kumar2025 configuration counts — OPEN (decision: Daniel × Pranav Kumar)

- Paper-text KG: `ds-TiCr2H-c15` **1,019**, `ds-TiCr2H-c14` **3,766**
  configurations, labels say "step 1" (first active-learning iteration).
- Artifact (DaRUS DARUS-5169): final training databases — C14
  **18,902** train + 1,995 test; C15 **19,877** train + 1,995 test.
  The step-1 subsets are not identifiable as such in the deposit.
- Derived graph models what the deposit contains (per green-light);
  the kg graph keeps the paper-text step-1 numbers. Daniel is asking
  co-author Pranav Kumar which the KG should canonically describe.

## 2. nitol2024nial attribution — DOCUMENTED (KG is correct; corpus-plan label is not)

- Investigated 2026-07-26: the KG's bibliographic entity
  (`entity:article-nitol2024nial`) already encodes the actual paper —
  "Efficient moment tensor machine-learning interatomic potential for
  accurate description of defects in Ni-Al alloys", **Wang, Liu, Zhu,
  Liu, Ma, Chen, Sun, Chen (IMR CAS)**, arXiv:2411.01282 — verified
  against the arXiv API. The study label even says "Wang et al.".
- The misattribution exists only in the research-env corpus plan
  (`related-work/CORPUS.md` cites it as "Nitol et al., PRMaterials
  2024") and in the `nitol2024nial` paper-id slug.
- Proposed resolution: no KG change; fix the CORPUS.md citation line
  (coordinator/researcher-side file); keep the slug as an opaque
  stable identifier (renaming it would churn 20+ cross-references for
  no data gain). Coordinator sign-off pending, then → DECIDED.
- Related: the dataset deposit (github.com/wftao1995/MTP_dataset)
  carries **no license**.

## 3. ANI-1 conformation count — OPEN (which number should the kg graph carry?)

- Paper-text KG: ~**17,200,000** (the paper's figure).
- Artifact (figshare release, s01–s08): **22,057,374** conformations
  counted. The paper's ~17.2M appears to be a post-filtering figure.
- Derived graph asserts the measured 22,057,374. Options for the kg
  graph: keep the paper figure (it is what the paper says) or annotate
  it as paper-reported. Recommendation: keep, since the kg graph is
  paper-text by definition — then this entry becomes DOCUMENTED.

## 4. qi2023 off-by-one — DOCUMENTED

- Paper-text KG: **3,798**; artifact (figshare, with_surface
  train+test): 3,420 + 377 = **3,797**.
- Both stay; the kg graph is faithful to the paper's own arithmetic
  (33+2160+185+580+840 = 3,798). Likely one configuration was dropped
  between the paper's accounting and the deposited JSONs.

## 5. batatia2024mp0 "subset" label — DOCUMENTED (kg label correction suggested for v0.2.0 pass)

- Paper-text KG: "~1.5M subset" of MPtrj, numConfigurations 1,500,000.
- Artifact (MACE-MP-0 training_data.zip): the **full** MPtrj —
  **1,580,395** frames across 145,923 per-compound extxyz files.
- Derived graph asserts 1,580,395. Suggested kg-side edit (with the
  v0.2.0 data-quality pass): label "the MPtrj dataset (full)" and
  count 1,580,395.

## 6. MPtrj energy-key gap — RETRACTED (was a scan artifact)

- The recon-phase scan reported 1,580,388 frames carrying
  `uncorrected_total_energy` (7 fewer than the extxyz repackaging).
  The extraction-phase scan with chunk-boundary overlap handling finds
  all **1,580,395** — the "gap" was keys split across read-chunk
  boundaries in the earlier naive count. No discrepancy exists.

## 7. batzner2022 water/ice provenance citation — OPEN (kg comment fix, small)

- The KG note credits the 140k-frame source set to "Cheng et al. 2019
  PNAS"; the paper's own references for that set are **Zhang et al.
  2018 PRL** and **Ko et al. 2019 Mol. Phys.** (Cheng 2019 is a
  different water dataset). One-line `rdfs:comment` fix in
  batzner2022.ttl; batched for the v0.2.0 data-quality pass.

## 8. KG counts a training split; the deposit is a larger corpus — DOCUMENTED (class entry)

Not disagreements, but systematic semantic differences the two graphs
now express side by side (kg = what the paper used; datasets = what
the deposit contains):

| entity | kg (split used) | datasets (deposit) |
|---|---|---|
| ds-rMD17 | 1,000 (950+50 per molecule) | 999,988 frames |
| ds-md17-schutt2018 | 50,000 (training size) | 3,611,115 frames |
| ds-Li3PO4 | 10,000 (+1k valid sampled) | 50,000-frame AIMD pool |
| ds-NiAl-nitol2024nial | 8,450 (train only) | 9,265 (train + valid) |

## 9. `datasetProvenance` semantics — OPEN (deferred to v0.2.0 modeling set, per coordinator)

- Four entities are `InHouse` yet published deposits exist
  (bartok2018si, smith2017, musaelian2023allegro Li₃PO₄,
  lysogorskiy-Cu); bartok2018si's DB is simultaneously `Published` in
  lysogorskiy2021ace.ttl. In-house-at-creation vs published-later are
  different dimensions; vocabulary redesign deferred to v0.2.0.
