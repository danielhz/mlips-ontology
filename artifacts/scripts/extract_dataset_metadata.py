#!/usr/bin/env python3
"""Extract aggregate metadata from the collected training datasets.

Full-scale extractor (extraction epic, design approved in 5d098d5 /
green-light note-20260726-224002): runs on kg1 against ~/mlips-datasets
and emits one Turtle file per paper-id into derived-out/, destined for
artifacts/kg/datasets/derived/ and the …/graph/datasets named graph.

Aggregate-only, per EXTRACTION-DESIGN.md: config counts (per split),
species coverage, atoms-per-config range, E/F/S label coverage
(existing mlips:coversProperty), plus a dcat:Distribution per
downloaded file (URL, byteSize, sha256, retrieval date from the
PROVENANCE.txt sidecars) and a prov:Activity per paper. Existing mlips
terms + DCAT/PROV/SPDX only — no schema changes. Aggregates lacking an
mlips term (species, atom range) ride in a structured rdfs:comment
pending the v0.2.0 term review.

Handlers: extxyz (ase streaming), extxyz-fast (text scan, for the
145k-file MACE-MP-0 copy), MD17/rMD17 npz, ANI HDF5, MTP .cfg,
monty/pymatgen JSON, MPF pickle, MPtrj streaming JSON, pacemaker JSON.

Usage: extract_dataset_metadata.py [--base ~/mlips-datasets]
                                   [--out-dir derived-out] [paper-id ...]
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

PREFIXES = """@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .
@prefix dcat:    <http://www.w3.org/ns/dcat#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix prov:    <http://www.w3.org/ns/prov#> .
@prefix spdx:    <http://spdx.org/rdf/terms#> .
@prefix mlips:   <https://w3id.org/mlips#> .
@prefix entity:  <https://w3id.org/mlips/entity/> .

"""


# ----------------------------------------------------------------- utils
def agg(splits, species, nat_min, nat_max, covers, note=None, total=None):
    """total overrides the sum of splits when splits overlap (e.g. a
    labelled subset of a larger pool)."""
    return dict(splits=splits, species=sorted(species), nat_min=nat_min,
                nat_max=nat_max, covers=covers, note=note, total=total)


def parse_provenance_all(prov_path):
    """All entries of a PROVENANCE.txt -> list of dicts."""
    entries = []
    cur = {}
    for line in prov_path.read_text().splitlines():
        if not line.strip():
            if cur:
                entries.append(cur)
                cur = {}
            continue
        m = re.match(r"^([a-z0-9-]+): (.*)$", line)
        if m:
            cur[m.group(1)] = m.group(2).strip()
    if cur:
        entries.append(cur)
    return [e for e in entries if "source-url" in e]


# ------------------------------------------------------------- handlers
def h_extxyz_ase(base, files):
    from ase.io import iread
    splits = []
    species = set()
    nat_min, nat_max = None, 0
    cov = set()
    for rel, role in files:
        n = 0
        for atoms in iread(str(base / rel), format="extxyz"):
            n += 1
            na = len(atoms)
            nat_min = na if nat_min is None else min(nat_min, na)
            nat_max = max(nat_max, na)
            species.update(atoms.get_chemical_symbols())
            if n == 1 or n % 997 == 0:
                info = {k.lower() for k in atoms.info}
                arrays = {k.lower() for k in atoms.arrays}
                calc = ({k.lower() for k in atoms.calc.results}
                        if atoms.calc is not None else set())
                if (info | calc) & {"energy", "free_energy", "dft_energy"}:
                    cov.add("Energy")
                if (arrays | calc) & {"forces", "force", "dft_force", "dft_forces"}:
                    cov.add("Forces")
                if (info | calc) & {"stress", "virial", "dft_virial"}:
                    cov.add("Stresses")
        splits.append((role, n))
    return agg(splits, species, nat_min, nat_max, cov)


def h_extxyz_fast(base, dirrel):
    """Text-scan a directory of *.extxyz (one per compound)."""
    d = base / dirrel
    frames = 0
    nfiles = 0
    species = set()
    nat_min, nat_max = None, 0
    cov = set()
    sym = re.compile(rb"^([A-Z][a-z]?)\s")
    for f in d.glob("*.extxyz"):
        nfiles += 1
        expect_header = True
        pending = 0
        with open(f, "rb") as fh:
            for line in fh:
                s = line.strip()
                if pending:
                    m = sym.match(line)
                    if m:
                        species.add(m.group(1).decode())
                    pending -= 1
                    continue
                if s.isdigit():
                    frames += 1
                    na = int(s)
                    nat_min = na if nat_min is None else min(nat_min, na)
                    nat_max = max(nat_max, na)
                    pending = -1  # next line is the comment header
                elif pending == 0 and expect_header:
                    pass
                if pending == -1:
                    pending = 0
                    continue
        # label coverage from the first comment line of each 500th file
        if nfiles % 500 == 1:
            with open(f, "rb") as fh:
                fh.readline()
                header = fh.readline().lower()
                if b"energy" in header:
                    cov.add("Energy")
                if b"forces" in header:
                    cov.add("Forces")
                if b"stress" in header or b"virial" in header:
                    cov.add("Stresses")
                # species from the first frame's atom lines
                first = fh.readline()
                m = sym.match(first)
                if m:
                    species.add(m.group(1).decode())
    # per-atom species collection above is partial (perf); do a full
    # species pass over first-column tokens with grep-like scan
    return agg([("all (%d per-compound files)" % nfiles, frames)],
               species, nat_min, nat_max, cov,
               note="fast text scan; species sampled per file header block")


def h_npz(base, files, keys):
    import numpy as np
    from ase.data import chemical_symbols
    ck, ek, fk, zk = keys
    splits = []
    species = set()
    nat_min, nat_max = None, 0
    cov = set()
    for rel, role in files:
        a = np.load(base / rel)
        n = int(a[ck].shape[0])
        splits.append((role, n))
        z = np.atleast_1d(a[zk]).astype(int).ravel()
        species.update(chemical_symbols[i] for i in set(z.tolist()))
        na = a[ck].shape[1] if a[ck].ndim >= 2 else len(z)
        nat_min = na if nat_min is None else min(nat_min, na)
        nat_max = max(nat_max, na)
        if ek in a:
            cov.add("Energy")
        if fk in a:
            cov.add("Forces")
    return agg(splits, species, nat_min, nat_max, cov)


def h_ani1(base, dirrel):
    import h5py
    files = sorted((base / dirrel).rglob("*.h5"))
    total = 0
    species = set()
    nat_min, nat_max = None, 0
    for h5 in files:
        with h5py.File(h5) as f:
            def visit(name, obj):
                nonlocal total, nat_min, nat_max
                if isinstance(obj, h5py.Dataset) and name.endswith("/energies"):
                    total += obj.shape[0]
                if isinstance(obj, h5py.Dataset) and name.endswith("/species"):
                    sp = {s.decode() if isinstance(s, bytes) else str(s)
                          for s in obj[:]}
                    species.update(sp)
                    na = obj.shape[0]
                    nat_min = na if nat_min is None else min(nat_min, na)
                    nat_max = max(nat_max, na)
            f.visititems(visit)
    return agg([("all (%d h5 files)" % len(files), total)],
               species, nat_min, nat_max, {"Energy"},
               note="ANI-1 release carries energies only (no forces)")


def h_ani1x(base, h5rel):
    import h5py
    import numpy as np
    from ase.data import chemical_symbols
    total = 0
    ccsd = 0
    species = set()
    nat_min, nat_max = None, 0
    with h5py.File(base / h5rel) as f:
        for mol in f.values():
            e = mol["wb97x_dz.energy"][:]
            total += e.shape[0]
            z = mol["atomic_numbers"][:]
            species.update(chemical_symbols[int(i)] for i in set(z.tolist()))
            na = len(z)
            nat_min = na if nat_min is None else min(nat_min, na)
            nat_max = max(nat_max, na)
            if "ccsd(t)_cbs.energy" in mol:
                ccsd += int(np.sum(~np.isnan(mol["ccsd(t)_cbs.energy"][:])))
    return agg([("DFT (ANI-1x) conformation pool", total),
                ("CCSD(T)*/CBS-labelled (ANI-1ccx)", ccsd)],
               species, nat_min, nat_max, {"Energy", "Forces"},
               note="the ccsd-labelled set is a SUBSET of the DFT pool; "
                    "numConfigurations counts the ANI-1ccx subset (this "
                    "KG entity); forces are at the DFT level",
               total=ccsd)


def h_cfg(base, groups, species_note):
    """MTP .cfg blocks; groups = [(role, [paths])]."""
    splits = []
    nat_min, nat_max = None, 0
    cov = set()
    species = set()
    for role, paths in groups:
        n = 0
        for p in paths:
            with open(p, "rb") as fh:
                in_block = False
                for line in fh:
                    s = line.strip()
                    if s == b"BEGIN_CFG":
                        n += 1
                        in_block = True
                        expect_size = False
                    elif in_block and s == b"Size":
                        expect_size = True
                    elif in_block and expect_size and s.isdigit():
                        na = int(s)
                        nat_min = na if nat_min is None else min(nat_min, na)
                        nat_max = max(nat_max, na)
                        expect_size = False
                    elif s.startswith(b"Energy"):
                        cov.add("Energy")
                    elif s.startswith(b"AtomData") and b"fx" in s:
                        cov.add("Forces")
                    elif s.startswith(b"PlusStress"):
                        cov.add("Stresses")
                    elif s == b"END_CFG":
                        in_block = False
        splits.append((role, n))
    return agg(splits, species, nat_min, nat_max, cov, note=species_note)


def h_monty_json(base, files):
    splits = []
    species = set()
    nat_min, nat_max = None, 0
    for rel, role in files:
        data = json.load(open(base / rel))
        splits.append((role, len(data)))
        for s in data:
            sites = s.get("sites", [])
            na = len(sites)
            if na:
                nat_min = na if nat_min is None else min(nat_min, na)
                nat_max = max(nat_max, na)
            for site in sites:
                for sp in site.get("species", []):
                    species.add(sp.get("element"))
    return agg(splits, species, nat_min, nat_max, {"Energy", "Forces"},
               note="energies/forces in the companion "
                    "train/test_energies+forces JSON files")


def h_mpf_pickle(base, files):
    import pandas as pd
    compounds = 0
    steps = 0
    species = set()
    nat_min, nat_max = None, 0
    for rel, _role in files:
        d = pd.read_pickle(base / rel)
        compounds += len(d)
        for v in d.values():
            steps += len(v["energy"])
            for struct in v["structure"]:
                # entries are live pymatgen Structure objects
                na = len(struct)
                if na:
                    nat_min = na if nat_min is None else min(nat_min, na)
                    nat_max = max(nat_max, na)
                species.update(el.symbol for el in struct.composition.elements)
    return agg([("compounds", compounds), ("ionic steps", steps)],
               species, nat_min, nat_max,
               {"Energy", "Forces", "Stresses"},
               note="dict[mp-id -> per-ionic-step lists] pickle; "
                    "numConfigurations counts ionic steps",
               total=steps)


def h_mptrj_stream(base, jsonrel):
    frames = 0
    species = set()
    elem = re.compile(rb'"element":\s*"([A-Z][a-z]?)"')
    tail = b""
    with open(base / jsonrel, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 24), b""):
            buf = tail + chunk
            frames += buf.count(b'"uncorrected_total_energy"')
            for m in elem.finditer(buf):
                species.add(m.group(1).decode())
            tail = buf[-64:]
            # avoid double counting the key across the overlap
            frames -= tail.count(b'"uncorrected_total_energy"')
    frames += tail.count(b'"uncorrected_total_energy"')
    return agg([("frames (by energy key)", frames)], species, None, 0,
               {"Energy", "Forces", "Stresses"},
               note="streaming scan of the 12 GB JSON; atoms-per-config "
                    "range not computed at this scale")


def h_pace_json(base, jsonrel):
    data = json.load(open(base / jsonrel))
    species = set()
    nat_min, nat_max = None, 0
    cov = set()
    for e in data:
        na = int(e.get("NUMBER_OF_ATOMS", 0))
        if na:
            nat_min = na if nat_min is None else min(nat_min, na)
            nat_max = max(nat_max, na)
        for s in e.get("_OCCUPATION", []):
            species.add(s)
        if "energy" in e or "energy_corrected" in e:
            cov.add("Energy")
        if "forces" in e:
            cov.add("Forces")
    return agg([("all", len(data))], species, nat_min, nat_max, cov,
               note="pacemaker dataframe JSON (FHI-aims/PBE)")


# ------------------------------------------------------------- registry
def R(base):
    g = base / "gubaev2023/tavcrw-darus3516"
    split0 = sorted(p for p in g.rglob("*")
                    if p.is_file() and (p.name.endswith("_train_0")
                                        or p.name.endswith("_valid_0")))
    deformed = sorted((g / "x-CFG_in_distribution_splits").rglob("deformed/*.cfg"))
    ood = sorted((g / "x-CFG_out_of_distribution").rglob("*.cfg"))
    return {
        "shapeev2016": {
            "ds-W-shapeev2016": dict(
                slug="w14", prov=["shapeev2016/w14"], fmt="extxyz",
                run=lambda: h_extxyz_ase(base, [("shapeev2016/w14/x/w-14.xyz", "all")])),
        },
        "kumar2025": {
            "ds-TiCr2H-c14": dict(
                slug="ticr2h-c14", prov=["kumar2025/ticr2h-darus5169"], fmt="extxyz",
                run=lambda: h_extxyz_ase(base, [
                    ("kumar2025/ticr2h-darus5169/x/database/Training_db/C14/training_dataset.xyz", "train"),
                    ("kumar2025/ticr2h-darus5169/x/database/Test_db/C14/test.xyz", "test")])),
            "ds-TiCr2H-c15": dict(
                slug="ticr2h-c15", prov=["kumar2025/ticr2h-darus5169"], fmt="extxyz",
                run=lambda: h_extxyz_ase(base, [
                    ("kumar2025/ticr2h-darus5169/x/database/Training_db/C15/training_dataset.xyz", "train"),
                    ("kumar2025/ticr2h-darus5169/x/database/Test_db/C15/test.xyz", "test")])),
        },
        "bartok2018si": {
            "ds-Si-bartok2018": dict(
                slug="si-gap-db", prov=["bartok2018si/si-gap-db"], fmt="extxyz",
                run=lambda: h_extxyz_ase(base, [
                    ("bartok2018si/si-gap-db/x/gp_iter6_sparse9k.xml.xyz", "all")])),
        },
        "lysogorskiy2021ace": {
            "ds-Si-lysogorskiy2021ace": dict(
                slug="si-gap-db-shared", prov=["bartok2018si/si-gap-db"], fmt="extxyz",
                run=lambda: h_extxyz_ase(base, [
                    ("bartok2018si/si-gap-db/x/gp_iter6_sparse9k.xml.xyz", "all")]),
                extra="Same physical dataset as ds-Si-bartok2018 (the paper "
                      "fits ACE to the published Bartok-2018 Si GAP DB)."),
            "ds-Cu-lysogorskiy2021ace": dict(
                slug="cu-pace", prov=["lysogorskiy2021ace/cu-pace"], fmt="JSON (pacemaker)",
                run=lambda: h_pace_json(
                    base, "lysogorskiy2021ace/cu-pace/x/Cu_FHIaims-PBE-dataset.json")),
        },
        "nitol2024nial": {
            "ds-NiAl-nitol2024nial": dict(
                slug="nial-mtp", prov=["nitol2024nial/mtp-dataset-github"], fmt="extxyz",
                run=lambda: h_extxyz_ase(base, [
                    ("nitol2024nial/mtp-dataset-github/MTP_dataset/train.1.xyz", "train (part 1)"),
                    ("nitol2024nial/mtp-dataset-github/MTP_dataset/train.2.xyz", "train (part 2)"),
                    ("nitol2024nial/mtp-dataset-github/MTP_dataset/valid.xyz", "valid")])),
        },
        "musaelian2023allegro": {
            "ds-Li3PO4": dict(
                slug="li3po4", prov=["musaelian2023allegro/li3po4"], fmt="extxyz",
                run=lambda: h_extxyz_ase(base, [
                    ("musaelian2023allegro/li3po4/x/li3po4-joint-together.xyz", "all (full 50k AIMD pool)")]),
                extra="KG models the sampled 10k train + 1k validation "
                      "subset of this 50k-frame deposited pool."),
        },
        "batatia2024mp0": {
            "ds-MPtrj-batatia2024mp0": dict(
                slug="mptrj-gga-ggapu", prov=["batatia2024mp0/mptrj-gga-ggapu"], fmt="extxyz",
                run=lambda: h_extxyz_fast(
                    base, "batatia2024mp0/mptrj-gga-ggapu/x/mptrj-gga-ggapu")),
        },
        "schutt2018": {
            "ds-md17-schutt2018": dict(
                slug="md17", prov=["schutt2018/md17"], fmt="npz",
                run=lambda: h_npz(base, [
                    ("schutt2018/md17/md17_%s.npz" % m, m) for m in
                    ("aspirin", "benzene2017", "ethanol", "malonaldehyde",
                     "naphthalene", "salicylic", "toluene", "uracil")],
                    ("R", "E", "F", "z")),
                extra="KG's 50000 is the training size used by SchNet, "
                      "not the corpus size."),
        },
        "batatia2022": {
            "ds-rMD17": dict(
                slug="rmd17", prov=["batatia2022/rmd17"], fmt="npz",
                run=lambda: h_npz(base, [
                    ("batatia2022/rmd17/x/rmd17/npz_data/rmd17_%s.npz" % m, m)
                    for m in ("aspirin", "azobenzene", "benzene", "ethanol",
                              "malonaldehyde", "naphthalene", "paracetamol",
                              "salicylic", "toluene", "uracil")],
                    ("coords", "energies", "forces", "nuclear_charges")),
                extra="KG's 1000 is the 950+50 per-molecule split used by "
                      "MACE (split index CSVs are in the deposit)."),
        },
        "gubaev2023": {
            "ds-TaVCrW": dict(
                slug="tavcrw", prov=["gubaev2023/tavcrw-darus3516"], fmt="MTP .cfg",
                run=lambda: h_cfg(base, [
                    ("in-distribution (split 0 of 10 redundant splits)", split0),
                    ("deformed", deformed),
                    ("out-of-distribution", ood)],
                    "atom species are integer-coded in the deposit (.cfg "
                    "types / npz 'types'); elements Ta, V, Cr, W per the "
                    "dataset identity"),
            ),
        },
        "qi2023": {
            "ds-TiAl": dict(
                slug="tial", prov=["qi2023/tial-mtp"], fmt="monty/pymatgen JSON",
                run=lambda: h_monty_json(base, [
                    ("qi2023/tial-mtp/x/MTP_TiAl/training_data/with_surface/train_structures.json", "train (with_surface)"),
                    ("qi2023/tial-mtp/x/MTP_TiAl/training_data/with_surface/test_structures.json", "test (with_surface)")]),
                extra="The deposit also carries a without_surface variant "
                      "of the train/test JSONs."),
        },
        "chen2022": {
            "ds-MPF-2021-2-8": dict(
                slug="mpf", prov=["chen2022/mpf-2021-2-8"], fmt="pymatgen pickle",
                run=lambda: h_mpf_pickle(base, [
                    ("chen2022/mpf-2021-2-8/block_0.p", "block 0"),
                    ("chen2022/mpf-2021-2-8/block_1.p", "block 1")])),
        },
        "deng2023": {
            "ds-MPtrj": dict(
                slug="mptrj", prov=["deng2023/mptrj"], fmt="JSON (12 GB)",
                run=lambda: h_mptrj_stream(base, "deng2023/mptrj/MPtrj_2022.9_full.json")),
        },
        "smith2017": {
            "ds-ANI1-smith2017": dict(
                slug="ani1", prov=["smith2017/ani1"], fmt="HDF5",
                run=lambda: h_ani1(base, "smith2017/ani1/x")),
        },
        "smith2019ccx": {
            "ds-ani1ccx-smith2019ccx": dict(
                slug="ani1x", prov=["smith2019ccx/ani1x-release"], fmt="HDF5",
                run=lambda: h_ani1x(base, "smith2019ccx/ani1x-release/ani1x-release.h5")),
        },
    }


# ----------------------------------------------------------------- emit
def emit(paper, specs, base, out_dir):
    today = date.today().isoformat()
    lines = [PREFIXES]
    act = "entity:extract-%s-%s" % (paper, today)
    lines.append("%s a prov:Activity ;\n"
                 "    rdfs:label \"aggregate metadata extraction from the "
                 "collected %s dataset artifact(s)\" ;\n"
                 "    prov:startedAtTime \"%s\"^^xsd:date ;\n"
                 "    rdfs:comment \"extract_dataset_metadata.py; run on kg1 "
                 "against ~/mlips-datasets (see PROVENANCE sidecars)\" .\n"
                 % (act, paper, today))
    for ent, spec in specs.items():
        a = spec["run"]()
        dists = []
        for pdir in spec["prov"]:
            for i, p in enumerate(parse_provenance_all(base / pdir / "PROVENANCE.txt")):
                dist = "entity:dist-%s-%d" % (spec["slug"], i)
                dists.append(dist)
                url = p["source-url"].split(" ")[0]
                lines.append("%s a dcat:Distribution ;\n" % dist
                             + "    dcat:downloadURL <%s> ;\n" % url
                             + ("    dcat:byteSize \"%s\"^^xsd:nonNegativeInteger ;\n"
                                % p["size-bytes"] if p.get("size-bytes") else "")
                             + "    dcterms:format %s ;\n" % json.dumps(spec["fmt"])
                             + ("    spdx:checksum [ a spdx:Checksum ;\n"
                                "        spdx:algorithm spdx:checksumAlgorithm_sha256 ;\n"
                                "        spdx:checksumValue \"%s\" ] ;\n" % p["sha256"]
                                if p.get("sha256") else "")
                             + "    prov:generatedAtTime \"%s\"^^xsd:dateTime .\n"
                             % p["retrieved"])
        covers = ["mlips:%s" % c for c in sorted(a["covers"])]
        total = a.get("total") or sum(n for _r, n in a["splits"])
        split_txt = "; ".join("%s: %d" % (r, n) for r, n in a["splits"])
        comment = "Artifact-derived aggregates: %s. Species: {%s}" % (
            split_txt, ", ".join(a["species"]))
        if a["nat_min"] is not None:
            comment += "; atoms/config %d-%d" % (a["nat_min"], a["nat_max"])
        if a.get("note"):
            comment += ". " + a["note"]
        if spec.get("extra"):
            comment += " " + spec["extra"]
        lines.append("entity:%s\n" % ent
                     + "    mlips:numConfigurations %d ;\n" % total
                     + ("    mlips:coversProperty %s ;\n" % " , ".join(covers)
                        if covers else "")
                     + "".join("    dcat:distribution %s ;\n" % d for d in dists)
                     + "    prov:wasGeneratedBy %s ;\n" % act
                     + "    rdfs:comment %s .\n" % json.dumps(comment))
    out = out_dir / ("%s.ttl" % paper)
    out.write_text("".join(lines))
    print("wrote", out, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=str(Path.home() / "mlips-datasets"))
    ap.add_argument("--out-dir", default="derived-out")
    ap.add_argument("papers", nargs="*")
    args = ap.parse_args()
    base = Path(args.base)
    registry = R(base)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    papers = args.papers or list(registry)
    failed = []
    for paper in papers:
        if paper not in registry:
            sys.exit("unknown paper-id: %s" % paper)
        try:
            emit(paper, registry[paper], base, out_dir)
        except Exception as e:
            failed.append((paper, repr(e)))
            print("FAILED", paper, repr(e), flush=True)
    print("done; %d failed" % len(failed), flush=True)
    for p, e in failed:
        print("  ", p, e)


if __name__ == "__main__":
    main()
