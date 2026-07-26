# Extraction epic — design proposal (for coordinator + Daniel review)

Status: PROPOSAL. Nothing here changes the schema; the spike
(`spike/`) emits data using existing `mlips:` terms plus externally
defined vocabularies (DCAT/PROV/SPDX), which requires no schema edit.
The one genuine schema addition (§3) is proposed for v0.2.0 review.

## 1. Where artifact-derived triples live

A dedicated consumer-uploaded named graph:
**`https://w3id.org/mlips/graph/datasets`**, sourced from committed
files under `artifacts/kg/datasets/derived/*.ttl` (one per paper-id,
assembled by the uploader like `kg` assembles the paper files).

- Paper-text metadata stays in `…/graph/kg` (untouched); artifact-
  derived metadata lives only in `…/graph/datasets`. The same subject
  IRIs (`entity:ds-*`) are used, so queries can join, and the named
  graph *is* the provenance boundary: `GRAPH <…/graph/datasets>`
  triples are by definition read-from-the-artifact. No paper-text
  triple is overwritten, ever; both `mlips:numConfigurations`
  assertions can coexist (one per graph) and the discrepancy dossier
  (§5) records disagreements.
- Every per-paper derived file carries an extraction activity:
  `entity:extract-<paper-id>-<date> a prov:Activity` with
  `prov:used <download URL>`, `prov:startedAtTime`, and the emitting
  parser + version; each derived dataset description gets
  `prov:wasDerivedFrom` (the distribution) and
  `prov:wasGeneratedBy` (the activity).

## 2. Aggregate vs per-config (per dataset)

Default: **aggregate only** — for every collected dataset in this
epic. Extracted per dataset: true config count (per split where the
deposit splits), element/species coverage, atoms-per-config min/max,
label coverage (energy/forces/stress present, using existing
`mlips:coversProperty`), container format, byte size, checksum.

| dataset | configs | mode | note |
|---|---|---|---|
| MPtrj (deng, batatia2024mp0), MPF, ANI-1, ANI-1x/ccx, MD17, rMD17 | 190k–22M | aggregate | per-config IRIs would dwarf the whole KG |
| Li₃PO₄, nitol NiAl, w-14, kumar C14/C15, gubaev, si-GAP, qi TiAl, Cu-PACE | 2.5k–50k | aggregate | per-config adds no query value for current CQs |

Per-config IRIs are deliberately out of scope; if a future CQ needs
config-level querying for a small set (≤ ~10k), that's a follow-up
decision per dataset, not a default.

## 3. Schema addition (PROPOSED, v0.2.0): dataset distribution

Reuse **DCAT** rather than minting mlips terms:
`mlips:TrainingDataset` gets (documented in the XHTML source when
approved):

```turtle
entity:ds-W-shapeev2016 dcat:distribution [
    a dcat:Distribution ;
    dcat:downloadURL <https://qmml.org/Datasets/w-14.zip> ;
    dcat:byteSize "9761412"^^xsd:nonNegativeInteger ;
    dcat:mediaType "application/zip" ;
    dcterms:format "extxyz" ;
    dcterms:license <...> ;          # when the deposit declares one
    spdx:checksum [ a spdx:Checksum ;
        spdx:algorithm spdx:checksumAlgorithm_sha256 ;
        spdx:checksumValue "..." ] ;
    prov:generatedAtTime "2026-07-26T09:47:12Z"^^xsd:dateTime ]  # retrieval date
```

Only `dcat:distribution` needs schema-level documentation (annotation
of external-vocab usage, like the existing qudt/prov reuse); no new
mlips IRI is required. Until approved, the spike puts distribution
data in the derived graph only (allowed: data, not schema).

## 4. Parser plan (order = coverage per effort)

1. **extxyz** (spiked below) — 7 entities: w-14, si-GAP(×2 entities),
   kumar(×2), nitol, Li₃PO₄, batatia2024mp0.
2. **npz** — MD17, rMD17 (+ gubaev GM-NN mirrors as cross-check).
3. **MTP .cfg** — gubaev (dedup the 10 redundant splits).
4. **HDF5** — ANI-1, ANI-1x/ccx.
5. **monty/pymatgen JSON** — qi2023.
6. **pymatgen pickle** — MPF (pinned pymatgen).
7. **streaming JSON** — MPtrj.

One driver script (`extract_dataset_metadata.py`) with per-format
handlers, run on kg1 against `~/mlips-datasets`, emitting
`artifacts/kg/datasets/derived/<paper-id>.ttl`; committed here, and
`rapper -c` + a small parity check gate them.

## 5. Count corrections & ambiguities (folded in, not guessed)

- batatia2024mp0 → 1,580,395 (full MPtrj) — asserted in the derived
  graph; the kg-graph label/count correction is a separate KG edit
  after review.
- qi2023 → 3,797 (3,420 train + 377 test) in derived graph; dossier
  notes the off-by-one vs paper-text 3,798.
- ANI-1 → derived graph asserts the measured 22,057,374; paper-text
  17.2M stays in kg graph; dossier flags the open modeling decision.
- kumar2025 → derived graph models what the deposit contains
  (19,877 C14 / 18,902 C15 train + 1,995 test each); dossier notes
  the step-1 subsets (1,019/3,766) are not present as such in the
  deposit — pending Daniel × Pranav Kumar.
- nitol2024nial attribution → dossier item (KG bibliography vs the
  actual arXiv:2411.01282 authorship), needs investigation + possibly
  co-author input; no KG edit until resolved.

Dossier file: `artifacts/kg/datasets/DISCREPANCIES.md`, one entry per
disagreement: paper-text value, artifact value, evidence, status
(open/decided), decision owner.

## 6. Status

APPROVED (coordinator note 2026-07-26 22:40; Daniel). The spike
(`shapeev2016`, `kumar2025`) validated the pipeline; `spike/` is now
**`derived/`** — one TTL per paper for every collected dataset,
emitted by `artifacts/scripts/extract_dataset_metadata.py` on kg1 and
uploaded as the `datasets` unit (`…/graph/datasets`) by
`upload_to_concon.py`. The `dcat:distribution` schema documentation
is deferred to the v0.2.0 modeling set; disagreements live in
`DISCREPANCIES.md`.
