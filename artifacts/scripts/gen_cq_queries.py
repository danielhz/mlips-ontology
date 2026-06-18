#!/usr/bin/env python3
"""Generate the competency-question .rq files from cq.ttl.

cq.ttl (the CQ RDF) is the source of truth (Epic C): each
cq:CompetencyQuestion carries its runnable query verbatim in
cq:sparqlQuery. This script writes each query to
artifacts/kg/cq-queries/cq<NN>.rq (zero-padded from dcterms:identifier),
so the .rq files the round-trip harness and the paper appendix consume
are derived, not hand-maintained.

Modes:
  (default)   write the .rq files from cq.ttl.
  --check     regenerate in memory and diff against the on-disk .rq;
              exit non-zero if any differ (RDF and .rq are out of sync).

Usage:
  python3 artifacts/scripts/gen_cq_queries.py [--check]
      [--cq artifacts/kg/cq.ttl] [--out-dir artifacts/kg/cq-queries]
"""
import argparse
import re
import sys
from pathlib import Path

import rdflib

CQ = rdflib.Namespace("https://w3id.org/mlips/cq#")
DCTERMS = rdflib.Namespace("http://purl.org/dc/terms/")


def queries(cq_path):
    """Yield (filename, query_text) for each CompetencyQuestion, ordered
    by the numeric part of its dcterms:identifier."""
    g = rdflib.Graph()
    g.parse(str(cq_path), format="turtle")
    rows = []
    for s in g.subjects(rdflib.RDF.type, CQ.CompetencyQuestion):
        ident = str(g.value(s, DCTERMS.identifier))      # "CQ8"
        n = int(re.sub(r"\D", "", ident))
        text = str(g.value(s, CQ.sparqlQuery))
        rows.append((n, f"cq{n:02d}.rq", text))
    rows.sort()
    return [(fn, text) for _, fn, text in rows]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    base = Path(__file__).resolve().parent.parent / "kg"
    ap.add_argument("--cq", type=Path, default=base / "cq.ttl")
    ap.add_argument("--out-dir", type=Path, default=base / "cq-queries")
    ap.add_argument("--check", action="store_true",
                    help="verify on-disk .rq match cq.ttl; do not write")
    args = ap.parse_args()

    qs = queries(args.cq)
    if args.check:
        drift = []
        for fn, text in qs:
            p = args.out_dir / fn
            on_disk = p.read_text() if p.exists() else None
            if on_disk != text:
                drift.append(fn)
        if drift:
            print("OUT OF SYNC: cq.ttl does not match these .rq files: "
                  f"{', '.join(drift)}. Run gen_cq_queries.py to regenerate.",
                  file=sys.stderr)
            sys.exit(1)
        print(f"  cq-queries in sync with cq.ttl ({len(qs)} queries)")
    else:
        for fn, text in qs:
            (args.out_dir / fn).write_text(text)
        print(f"  Wrote {len(qs)} .rq files to {args.out_dir} from {args.cq}")


if __name__ == "__main__":
    main()
