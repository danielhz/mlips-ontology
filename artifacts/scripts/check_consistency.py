#!/usr/bin/env python3
"""Consistency gate for schema + vocabulary + knowledge graph (issue #1).

Loads the ontology (artifacts/ontology/mlips.ttl), the vocabulary, the
Wikidata typing, the shared KG files and every paper file, together with
the vendored PROV-O and ML-Schema (artifacts/ontology/imports/). It then
computes the RDFS type closure (rdfs:subClassOf, rdfs:subPropertyOf,
rdfs:domain, rdfs:range) and reports:

  1. individuals typed with two classes declared disjoint (owl:disjointWith
     or owl:AllDisjointClasses, from mlips or the imports, inherited by
     subclasses);
  2. literals outside the declared XSD range of a datatype property
     (OWL treats xsd:integer, xsd:decimal and xsd:double as disjoint
     value spaces, so "2600" as an integer violates a double range);
  3. the overlap counts of mlips:BenchmarkResult with mlips:BenchmarkStudy
     and mlips:TrainedModel (the bug of issue #1), printed even when zero.

Exit status 1 when any violation is found. This is a sound but partial
check (RDFS-level inference only); `make reason-kg` runs HermiT over the
same graph when ROBOT is installed.

Usage: check_consistency.py [--write-merged PATH]
"""
import argparse
import collections
import glob
import os
import sys

import rdflib
from rdflib.namespace import OWL, RDF, RDFS, XSD

MLIPS = rdflib.Namespace("https://w3id.org/mlips#")
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def sources():
    kg = os.path.join(REPO, "artifacts", "kg")
    files = [
        os.path.join(REPO, "artifacts", "ontology", "mlips.ttl"),
        os.path.join(kg, "mlips-vocab.ttl"),
        os.path.join(kg, "wikidata-types.ttl"),
    ]
    files += sorted(glob.glob(os.path.join(kg, "shared", "*.ttl")))
    files += sorted(glob.glob(os.path.join(kg, "papers", "*.ttl")))
    return files


def imports():
    d = os.path.join(REPO, "artifacts", "ontology", "imports")
    return [os.path.join(d, "prov-o.ttl"), os.path.join(d, "mls.ttl")]


def short(g, x):
    try:
        return g.namespace_manager.normalizeUri(x)
    except Exception:
        return str(x)


def rdf_list(g, head):
    out = []
    while head and head != RDF.nil:
        out.append(g.value(head, RDF.first))
        head = g.value(head, RDF.rest)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write-merged", help="also write the merged graph (without imports) as RDF/XML to this path")
    args = ap.parse_args()

    data = rdflib.Graph()
    for f in sources():
        data.parse(f)
    if args.write_merged:
        data.serialize(args.write_merged, format="xml")
    tbox = rdflib.Graph()
    for f in imports():
        tbox.parse(f)
    g = data + tbox
    g.namespace_manager.bind("mlips", MLIPS)
    g.namespace_manager.bind("entity", rdflib.Namespace("https://w3id.org/mlips/entity/"))
    g.namespace_manager.bind("prov", rdflib.Namespace("http://www.w3.org/ns/prov#"), replace=True)
    g.namespace_manager.bind("mls", rdflib.Namespace("http://www.w3.org/ns/mls#"), replace=True)

    # class and property hierarchies (reflexive-transitive)
    def closure(pred):
        up = collections.defaultdict(set)
        for s, o in g.subject_objects(pred):
            if isinstance(s, rdflib.URIRef) and isinstance(o, rdflib.URIRef):
                up[s].add(o)
        memo = {}

        def sup(x):
            if x not in memo:
                memo[x] = {x}
                for y in up.get(x, ()):
                    memo[x] |= sup(y)
            return memo[x]
        return sup

    supc = closure(RDFS.subClassOf)
    supp = closure(RDFS.subPropertyOf)
    dom = collections.defaultdict(set)
    rng = collections.defaultdict(set)
    for p, c in g.subject_objects(RDFS.domain):
        dom[p].add(c)
    for p, c in g.subject_objects(RDFS.range):
        rng[p].add(c)

    # RDFS type closure over the data graph
    types = collections.defaultdict(set)
    for s, c in data.subject_objects(RDF.type):
        types[s] |= supc(c)
    for s, p, o in data:
        if p == RDF.type:
            continue
        for q in supp(p):
            for c in dom.get(q, ()):
                types[s] |= supc(c)
            if not isinstance(o, rdflib.Literal):
                for c in rng.get(q, ()):
                    types[o] |= supc(c)

    # disjoint pairs, from owl:disjointWith and owl:AllDisjointClasses
    disjoint = set()
    for a, b in g.subject_objects(OWL.disjointWith):
        disjoint.add(frozenset((a, b)))
    for ax in g.subjects(RDF.type, OWL.AllDisjointClasses):
        members = rdf_list(g, g.value(ax, OWL.members))
        for i, a in enumerate(members):
            for b in members[i + 1:]:
                disjoint.add(frozenset((a, b)))

    violations = collections.defaultdict(list)
    for ind, ts in types.items():
        for pair in disjoint:
            a, b = tuple(pair)
            if a in ts and b in ts:
                violations[(short(g, a), short(g, b))].append(short(g, ind))

    # literal ranges of datatype properties
    xsd_ranges = {p: cs for p, cs in rng.items()
                  if any(str(c).startswith(str(XSD)) for c in cs)}
    dt_errors = collections.defaultdict(list)
    for s, p, o in data:
        if not isinstance(o, rdflib.Literal):
            continue
        for q in supp(p):
            for c in xsd_ranges.get(q, ()):
                dt = o.datatype or (RDF.langString if o.language else XSD.string)
                if dt != c:
                    dt_errors[(short(g, q), short(g, c), short(g, dt))].append(f'{short(g, s)} "{o}"'[:120])

    br = MLIPS.BenchmarkResult
    print("Consistency check: %d data triples, %d typed individuals, %d disjoint class pairs"
          % (len(data), len(types), len(disjoint)))
    for other in (MLIPS.BenchmarkStudy, MLIPS.TrainedModel):
        n = sum(1 for ts in types.values() if br in ts and other in ts)
        print(f"  overlap mlips:BenchmarkResult / {short(g, other)}: {n}")
    status = 0
    for (a, b), inds in sorted(violations.items()):
        status = 1
        print(f"  DISJOINTNESS {a} / {b}: {len(inds)} individual(s): {', '.join(sorted(inds)[:10])}"
              + (" ..." if len(inds) > 10 else ""))
    for (p, c, dt), ex in sorted(dt_errors.items()):
        status = 1
        print(f"  DATATYPE {p} range {c} given {dt}: {len(ex)} literal(s): {'; '.join(ex[:3])}")
    print("  result:", "FAIL" if status else "consistent at RDFS level (no disjointness or datatype violation)")
    return status


if __name__ == "__main__":
    sys.exit(main())
