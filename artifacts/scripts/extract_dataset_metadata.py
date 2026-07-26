#!/usr/bin/env python3
"""Extract aggregate metadata from collected training datasets (spike).

Runs on kg1 against ~/mlips-datasets (see artifacts/kg/datasets/
EXTRACTION-DESIGN.md) and emits one Turtle file per paper-id with
artifact-derived aggregate metadata for the …/graph/datasets named
graph. Spike scope: the extxyz handler, datasets shapeev2016 and
kumar2025. Uses only existing mlips terms plus DCAT/PROV/SPDX
(externally defined; no schema change). Aggregate facts that have no
mlips term yet (species coverage, atoms-per-config range) are carried
in a structured rdfs:comment pending the v0.2.0 term review.

Usage:  extract_dataset_metadata.py [--base ~/mlips-datasets]
                                    [--out-dir spike-out] [paper-id ...]
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

from ase.io import iread

# --- spike dataset registry: paper-id -> datasets -> entity + files ---
REGISTRY = {
    "shapeev2016": {
        "ds-W-shapeev2016": {
            "slug": "w14",
            "files": [("w14/x/w-14.xyz", "all")],
            "distribution": "w14",     # PROVENANCE.txt under this dir
        },
    },
    "kumar2025": {
        "ds-TiCr2H-c14": {
            "slug": "ticr2h-c14",
            "files": [
                ("ticr2h-darus5169/x/database/Training_db/C14/training_dataset.xyz", "train"),
                ("ticr2h-darus5169/x/database/Test_db/C14/test.xyz", "test"),
            ],
            "distribution": "ticr2h-darus5169",
        },
        "ds-TiCr2H-c15": {
            "slug": "ticr2h-c15",
            "files": [
                ("ticr2h-darus5169/x/database/Training_db/C15/training_dataset.xyz", "train"),
                ("ticr2h-darus5169/x/database/Test_db/C15/test.xyz", "test"),
            ],
            "distribution": "ticr2h-darus5169",
        },
    },
}

PREFIXES = """@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .
@prefix dcat:    <http://www.w3.org/ns/dcat#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix prov:    <http://www.w3.org/ns/prov#> .
@prefix spdx:    <http://spdx.org/rdf/terms#> .
@prefix mlips:   <https://w3id.org/mlips#> .
@prefix entity:  <https://w3id.org/mlips/entity/> .

"""


def aggregate_extxyz(path):
    """Stream one extxyz file: frames, species, atom range, labels."""
    frames = 0
    species = set()
    nat_min = None
    nat_max = 0
    has_energy = has_forces = has_stress = False
    for atoms in iread(str(path), format="extxyz"):
        frames += 1
        n = len(atoms)
        nat_min = n if nat_min is None else min(nat_min, n)
        nat_max = max(nat_max, n)
        species.update(atoms.get_chemical_symbols())
        if frames == 1 or frames % 997 == 0:
            info = {k.lower() for k in atoms.info}
            arrays = {k.lower() for k in atoms.arrays}
            # ase's extxyz reader moves standard keys (energy, forces,
            # stress) out of info/arrays into a SinglePointCalculator.
            calc = ({k.lower() for k in atoms.calc.results}
                    if atoms.calc is not None else set())
            if (info | calc) & {"energy", "free_energy", "dft_energy"}:
                has_energy = True
            if (arrays | calc) & {"forces", "force", "dft_force", "dft_forces"}:
                has_forces = True
            if (info | calc) & {"stress", "virial", "dft_virial"}:
                has_stress = True
    return dict(frames=frames, species=sorted(species), nat_min=nat_min,
                nat_max=nat_max, energy=has_energy, forces=has_forces,
                stress=has_stress)


def parse_provenance(prov_path):
    """First entry of a PROVENANCE.txt -> (url, retrieved, sha256, size)."""
    text = prov_path.read_text()
    def first(field):
        m = re.search(r"^%s: (.+)$" % field, text, re.M)
        return m.group(1).strip() if m else None
    return (first("source-url"), first("retrieved"),
            first("sha256"), first("size-bytes"))


def emit(paper, base, out_dir):
    today = date.today().isoformat()
    lines = [PREFIXES]
    act = "entity:extract-%s-%s" % (paper, today)
    lines.append("%s a prov:Activity ;\n"
                 "    rdfs:label \"aggregate metadata extraction from the "
                 "collected %s dataset artifact(s)\" ;\n"
                 "    prov:startedAtTime \"%s\"^^xsd:date ;\n"
                 "    rdfs:comment \"extract_dataset_metadata.py (extxyz spike); "
                 "ase streaming reader; run on kg1 against ~/mlips-datasets\" .\n"
                 % (act, paper, today))
    for ent, spec in REGISTRY[paper].items():
        url, retrieved, sha, size = parse_provenance(
            base / paper / spec["distribution"] / "PROVENANCE.txt")
        dist = "entity:dist-%s" % spec["slug"]
        per_split = []
        total = 0
        agg_all = dict(species=set(), nat_min=None, nat_max=0,
                       energy=False, forces=False, stress=False)
        for rel, role in spec["files"]:
            a = aggregate_extxyz(base / paper / rel)
            per_split.append((role, rel, a))
            total += a["frames"]
            agg_all["species"].update(a["species"])
            agg_all["nat_min"] = (a["nat_min"] if agg_all["nat_min"] is None
                                  else min(agg_all["nat_min"], a["nat_min"]))
            agg_all["nat_max"] = max(agg_all["nat_max"], a["nat_max"])
            for k in ("energy", "forces", "stress"):
                agg_all[k] = agg_all[k] or a[k]
        covers = []
        if agg_all["energy"]:
            covers.append("mlips:Energy")
        if agg_all["forces"]:
            covers.append("mlips:Forces")
        if agg_all["stress"]:
            covers.append("mlips:Stresses")
        split_txt = "; ".join("%s: %d configs (%s)" % (r, a["frames"], rel)
                              for r, rel, a in per_split)
        lines.append("entity:%s\n" % ent
                     + "    mlips:numConfigurations %d ;\n" % total
                     + ("    mlips:coversProperty %s ;\n" % " , ".join(covers)
                        if covers else "")
                     + "    dcat:distribution %s ;\n" % dist
                     + "    prov:wasGeneratedBy %s ;\n" % act
                     + "    rdfs:comment \"Artifact-derived aggregates: %s. "
                       "Species: {%s}; atoms/config %d-%d.\" .\n"
                     % (split_txt, ", ".join(sorted(agg_all["species"])),
                        agg_all["nat_min"], agg_all["nat_max"]))
        lines.append("%s a dcat:Distribution ;\n" % dist
                     + "    dcat:downloadURL <%s> ;\n" % url
                     + ("    dcat:byteSize \"%s\"^^xsd:nonNegativeInteger ;\n" % size
                        if size else "")
                     + "    dcterms:format \"extxyz\" ;\n"
                     + ("    spdx:checksum [ a spdx:Checksum ;\n"
                        "        spdx:algorithm spdx:checksumAlgorithm_sha256 ;\n"
                        "        spdx:checksumValue \"%s\" ] ;\n" % sha
                        if sha else "")
                     + "    prov:generatedAtTime \"%s\"^^xsd:dateTime .\n" % retrieved)
    out = out_dir / ("%s.ttl" % paper)
    out.write_text("".join(lines))
    print("wrote", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=str(Path.home() / "mlips-datasets"))
    ap.add_argument("--out-dir", default="spike-out")
    ap.add_argument("papers", nargs="*", default=list(REGISTRY))
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for paper in (args.papers or list(REGISTRY)):
        if paper not in REGISTRY:
            sys.exit("unknown paper-id: %s" % paper)
        emit(paper, Path(args.base), out_dir)


if __name__ == "__main__":
    main()
