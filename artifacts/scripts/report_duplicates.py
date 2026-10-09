#!/usr/bin/env python3
"""Same-label instance report for the per-paper KG (see artifacts/kg/IDENTITY.md).

Loads every artifacts/kg/papers/*.ttl and, per class, counts the instances
and how many of them share a normalised label (rdfs:label or schema:name)
with another instance of the same class. Exact label matching is a lower
bound on real duplication: the same data set or material under two
different labels is not seen.

Prints a Markdown table; classes with fewer than MIN instances are skipped.
"""
import collections
import glob
import os
import re
import sys

import rdflib
from rdflib.namespace import RDF, RDFS

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
NAMES = [RDFS.label, rdflib.URIRef("https://schema.org/name"),
         rdflib.URIRef("http://schema.org/name")]
MIN = 15


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()


def main():
    g = rdflib.Graph()
    paths = sorted(glob.glob(os.path.join(ROOT, "artifacts", "kg", "papers", "*.ttl")))
    for p in paths:
        g.parse(p)
    rows = []
    for c in set(g.objects(None, RDF.type)):
        inst = set(g.subjects(RDF.type, c))
        if len(inst) < MIN:
            continue
        labels = collections.Counter()
        for i in inst:
            for prop in NAMES:
                lab = g.value(i, prop)
                if lab is not None:
                    labels[norm(lab)] += 1
                    break
        if not labels:
            continue
        shared = sum(v for v in labels.values() if v > 1)
        top = ", ".join(f"{k} ({v})" for k, v in labels.most_common(4) if v > 1)
        rows.append((shared, re.split(r"[#/]", str(c))[-1], len(inst), len(labels), top))
    print(f"{len(paths)} files, {len(g)} triples\n")
    print("| class | instances | distinct labels | sharing a label | most repeated |")
    print("|---|---|---|---|---|")
    for shared, name, n, distinct, top in sorted(rows, reverse=True):
        print(f"| {name} | {n} | {distinct} | {shared} | {top} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
