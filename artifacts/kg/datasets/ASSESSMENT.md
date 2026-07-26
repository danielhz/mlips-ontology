# Training-dataset format & effort assessment (reconnaissance phase)

Companion to `inventory.csv` (all 22 `mlips:TrainingDataset` entities
with verified locations). This file assesses the **collected** subset:
real formats, structure, configuration counts cross-checked against the
KG's `mlips:numConfigurations`, per-format parser effort, and disk
footprint. Collected 2026-07-26 to `research-dev@kg1:~/mlips-datasets/`
(one directory per paper-id; every download carries a `PROVENANCE.txt`
sidecar with source URL, retrieval date, and sha256). Raw data stays
local and uncommitted; licenses are in the inventory — several deposits
(nitol2024nial, MD17, w-14) carry **no license**, so even derived
per-config metadata should be reviewed before publication.

**Headline numbers:** 16 downloads serving **17 of 22** KG entities
(the Bartók-2018 Si DB serves two entities; the Kumar DaRUS deposit
serves two); **5 entities uncollectable**; total footprint
**44 GB** (extracted); ~26.6M configurations on disk across 8 format
families; **7 parser implementations** would cover everything
collected, estimated **9–13 person-days** for metadata-level
extraction.

## 1. Formats and parser effort

| # | Format family | Datasets (entities) | Parser route | Effort |
|---|---|---|---|---|
| 1 | **extxyz** | bartok2018si (2 entities), shapeev2016/w-14, kumar2025 (2 entities), nitol2024nial, musaelian2023allegro/Li₃PO₄, batatia2024mp0 (145,923 per-compound files) | `ase.io.iread` streaming; per-producer comment-line key mapping (energy/stress/virial keys differ) | 2–3 d for all 7 entities |
| 2 | **npz (MD17 family)** | schutt2018/MD17 (8 molecules), batatia2022/rMD17 (10 molecules + split CSVs) | `numpy.load`; fixed keys (R/E/F/z resp. coords/energies/forces/nuclear_charges) | 0.5 d |
| 3 | **HDF5 (ANI)** | smith2017/ANI-1 (8 files, per-molecule groups), smith2019ccx/ani1x-release (single file, DFT + CCSD(T) properties) | `h5py` traversal; property-name mapping (`wb97x_dz.*` vs `ccsd(t)_cbs.*`, NaN = unlabelled) | 1–1.5 d |
| 4 | **MTP `.cfg`** | gubaev2023 (10× redundant train/valid splits named `*.cfg_train_N`, + deformed + OOD) | ~100-line text parser (`BEGIN_CFG` blocks); dedup across the 10 splits | 1 d |
| 5 | **monty/pymatgen JSON** | qi2023 (train/test structures+energies+forces JSONs) | `monty.serialization.loadfn` / pymatgen `Structure.from_dict` | 0.5 d |
| 6 | **pymatgen pickle** | chen2022/MPF.2021.2.8 (`block_0.p`+`block_1.p`: `dict[mp-id → dict(structure/energy/force/stress/id: per-ionic-step lists)]`) | `pandas.read_pickle` with pinned pymatgen (unpickle needs the classes); most fragile format | 1–2 d |
| 7 | **large single JSON** | deng2023/MPtrj (12.2 GB, `dict[mp-id → dict[frame-id → frame]]`) | streaming (`ijson`) or per-compound chunking; overlaps #6/#1 content-wise | 1–2 d |
| 8 | **JSON (FHI-aims/pacemaker)** | lysogorskiy2021ace/Cu (59 MB `Cu_FHIaims-PBE-dataset.json`) | bespoke but small; pacemaker's dataframe-JSON layout (~50,000 list entries; needs a structure-vs-property disambiguation pass) | 0.5–1 d |
| — | **DeepMD npy/raw** | wang2018dpkit — *format documented via the bundled demo only; the actual 40k-frame dataset is uncollectable* | (`type.raw` + `set.*/coord,energy,force,box.npy`) — no parser needed this epic | 0 |

Total: **9–13 person-days** for a metadata-level extractor family
(config counts, elements/composition, energy/force presence and units,
per-config provenance linkage). Full per-configuration KG ingestion
(one IRI per config) is a different order of magnitude and should be
decided per dataset — for the two MPtrj-scale corpora (1.58M frames)
per-config IRIs are likely undesirable versus dataset-level aggregate
metadata.

Cross-format observation: three deposits (chen2022, deng2023,
batatia2024mp0) are the *same physical content family* (Materials
Project trajectories) in three different containers (pickle, big JSON,
extxyz) — a single canonical internal representation with three
loaders avoids triple work downstream.

## 2. Configuration counts: deposit vs KG `numConfigurations`

Exact matches (KG value confirmed against the deposit):

| entity | KG | counted in deposit |
|---|---|---|
| ds-Si-bartok2018 / ds-Si-lysogorskiy2021ace | 2475 | 2475 frames (`gp_iter6_sparse9k.xml.xyz`) |
| ds-W-shapeev2016 | 9693 | 9693 frames (`w-14.xyz`) |
| ds-TaVCrW (gubaev2023) | 6711 | 6711 (in-distribution split 0; + 6 deformed + 117 OOD extra in deposit) |
| ds-MPF-2021-2-8 (chen2022) | 187687 | 187687 ionic steps over 62,783 compounds |
| ds-MPtrj (deng2023) | 1580395 | 1,580,388 by energy-key scan of the JSON (7 frames lack the key); the extxyz repackaging (below) confirms 1,580,395 |
| ds-MPtrj-batatia2024mp0 | 1500000 (KG "~1.5M subset") | **1,580,395** frames / 145,923 compounds — it is the *full* MPtrj, not a subset; KG label/count should say 1,580,395 |
| ds-NiAl-nitol2024nial | 8450 | 8450 train (4225+4225) + 815 valid — KG counts train only, consistent |
| ds-ani1ccx-smith2019ccx | 500000 (~) | 489,571 CCSD(T)-labelled conformations (of 4,956,005 DFT ones in the file) |

Semantic differences (KG counts a *training split*, the deposit is the
full corpus — not errors, but the extraction epic must model the
distinction):

| entity | KG | deposit | reading |
|---|---|---|---|
| ds-rMD17 (batatia2022) | 1000 | 999,988 frames (10 molecules; azobenzene 99,988) + 10 split-index CSV sets | KG = 950+50 per-molecule split used by MACE |
| ds-md17-schutt2018 | 50000 | 3,611,115 frames (8 molecules, 73–412 MB npz each) | KG = training size used by SchNet |
| ds-Li3PO4 (musaelian2023allegro) | 10000 | 50,000 frames deposited | KG = sampled 10k train (+1k valid) of the 50k AIMD pool |
| ds-TiAl (qi2023) | 3798 | 3420 train + 377 test = **3797** | off by one vs KG — worth a KG-side recheck |

Mismatches to flag:

| entity | KG | deposit | issue |
|---|---|---|---|
| **ds-TiCr2H-c15 / -c14 (kumar2025)** | 1019 / 3766 | **19,877 / 18,902** training frames (+1995 test each) | KG labels say "step 1" (first active-learning iteration); the DaRUS deposit carries the *final* training databases. Either the KG should model the final DBs, or the deposit does not contain the step-1 subsets at all. Needs resolution before extraction. |
| ds-ANI1-smith2017 | 17200000 (~17.2M, the paper's figure) | **22,057,374** conformations in the figshare release | The release (s01–s08) is larger than the paper's ~17.2M; the paper figure appears to be after energy filtering. Decide which number the KG should carry. |

Uncollectable (5 entities, reasons verified):
`ds-Si-bartok2010` and `ds-Si-behler2007` (never deposited, 2007/2010-era),
`ds-MnO-eckhoff2021` (on-request only from the Behler group),
`ds-water-ice` (batzner2022; the exact 133-frame subset was never
published and the underlying 140k-frame DP-library set is link-dead),
`ds-water-wang2018` (the 40k-frame set never shipped; only a
few-hundred-frame demo exists, kept locally as a format reference).

## 3. Disk footprint (extracted, kg1)

| paper-id | size | | paper-id | size |
|---|---|---|---|---|
| deng2023 | 12 GB | | chen2022 | 1.1 GB |
| smith2017 | 9.8 GB | | gubaev2023 | 865 MB |
| batatia2024mp0 | 8.2 GB | | kumar2025 | 468 MB |
| smith2019ccx | 5.3 GB | | bartok2018si | 302 MB |
| batatia2022 | 2.1 GB | | nitol2024nial | 182 MB |
| schutt2018 | 1.9 GB | | qi2023 | 123 MB |
| musaelian2023allegro | 1.3 GB | | lysogorskiy2021ace | 57 MB |
| | | | shapeev2016 | 36 MB |
| | | | wang2018dpkit | 4.3 MB |

**Total: 44 GB** (downloads + in-place extractions), well within kg1's
~1.6 TB free.

## 4. Operational notes for the extraction epic

- **Link rot is real**: the libatoms.org tungsten links are dead
  (qmml.org mirror used); Materials Cloud migrated to InvenioRDM
  (record IDs changed; old `/record/file?...` URLs 404); the DP
  library (dplibrary.deepmd.net) is gone entirely. The KG's future
  location/distribution predicate should record retrieval date +
  sha256, exactly as the sidecars do.
- **APIs that worked well programmatically**: figshare
  (`api.figshare.com/v2/articles/<id>`), DaRUS/Dataverse
  (`/api/datasets/:persistentId` + `/api/access/datafile/<id>`),
  GitHub releases; Apollo (Cambridge) needs a plain GET (HEAD lies).
- **Licenses**: CC0 (ANI×2, rMD17), CC BY 4.0 (DaRUS×2, Zenodo Cu,
  Materials Cloud Li₃PO₄, figshare TiAl/MPF), MIT (MPtrj, MACE copy),
  GPL-3.0 (Si GAP deposit), **none** (nitol2024nial GitHub, MD17,
  w-14 mirror).
