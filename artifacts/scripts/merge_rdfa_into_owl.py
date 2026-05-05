#!/usr/bin/env python3
"""Merge the RDFa annotations from the ontology XHTML source into
the OWL/TTL files that Saxon's extract-owl.xsl produced.

The XSLT only pulls the embedded <pre class="owl-xml"> CDATA blocks
(per-term axioms), so the ontology-header metadata that lives as RDFa
(dcterms:title, dcterms:license, owl:versionIRI, vann:preferredNamespace*,
owl:imports, dcterms:creator/contributor, dcterms:publisher, etc.) is
otherwise lost from the OWL/TTL serialisation.

This script:
  1. Parses mlips.owl (Saxon output) into an rdflib Graph.
  2. Parses mlips.source.xhtml with pyRdfa, extracts the RDFa triples.
  3. Filters the RDFa triples to the "ontology header CBD" -- the
     ontology subject's triples plus blank-node and external-IRI
     subjects reachable from it (publisher chain, schema:Person
     nodes for editors/contributors).
  4. Adds those triples to the Saxon graph.
  5. Re-serialises as both .ttl and .owl.

Usage:
    python3 artifacts/scripts/merge_rdfa_into_owl.py
        [--xhtml artifacts/ontology/mlips.source.xhtml]
        [--owl   artifacts/ontology/mlips.owl]
        [--ttl   artifacts/ontology/mlips.ttl]
"""
import argparse
import sys
from pathlib import Path

import rdflib
from rdflib import URIRef, BNode

try:
    from pyRdfa import pyRdfa
except ImportError:
    print("ERROR: pyRdfa3 is not installed. Run: pip install pyRdfa3", file=sys.stderr)
    sys.exit(2)


ONTOLOGY_IRI = URIRef("https://w3id.org/mlips")


def cbd(graph: rdflib.Graph, subject) -> rdflib.Graph:
    """Bounded description of `subject` over `graph`: subject's
    triples, plus the recursive closure over both blank-node and
    URIRef objects that themselves have triples in `graph`.

    The recursion is bounded by what is explicitly declared in the
    source graph. Since the source is the XHTML's RDFa (which contains
    only the metadata we hand-wrote), there is no risk of pulling in
    unrelated triples from a larger graph; we just follow every
    outgoing edge that is locally declared.

    This pulls in: editor / contributor schema:name + schema:Person
    type triples (linked by ORCID URIRef); the publisher chain
    (Wikidata IRI for the Institute, schema:parentOrganization to the
    University of Stuttgart Wikidata IRI, with both schema:name
    triples); and anything else we declare reachable from the
    ontology subject in future.
    """
    out = rdflib.Graph()
    seen = set()
    queue = [subject]
    while queue:
        s = queue.pop()
        if s in seen:
            continue
        seen.add(s)
        # Take every outgoing triple of `s`.
        out_triples = list(graph.predicate_objects(s))
        if not out_triples:
            continue
        for p, o in out_triples:
            out.add((s, p, o))
            # Recurse into any object that itself has triples in the
            # source graph -- bnodes (always) and URIRefs (only the
            # ones we declared, since that's all the RDFa source
            # contains).
            if isinstance(o, (BNode, URIRef)):
                queue.append(o)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    base = Path(__file__).resolve().parent.parent / "ontology"
    parser.add_argument("--xhtml", type=Path, default=base / "mlips.source.xhtml")
    parser.add_argument("--owl",   type=Path, default=base / "mlips.owl")
    parser.add_argument("--ttl",   type=Path, default=base / "mlips.ttl")
    args = parser.parse_args()

    # 1. Saxon's OWL output (term axioms).
    g = rdflib.Graph()
    g.parse(str(args.owl), format="xml")
    n_axioms = len(g)

    # 2. pyRdfa extraction from the XHTML.
    rdfa_graph = pyRdfa().graph_from_source(str(args.xhtml))

    # 3. CBD over the ontology subject.
    header = cbd(rdfa_graph, ONTOLOGY_IRI)

    # 4. Merge.
    g += header
    n_total = len(g)

    # 5. Bind common prefixes for nicer Turtle output.
    g.bind("mlips",    "https://w3id.org/mlips#")
    g.bind("dcterms",  "http://purl.org/dc/terms/")
    g.bind("vann",     "http://purl.org/vocab/vann/")
    g.bind("schema",   "https://schema.org/")
    g.bind("prov",     "http://www.w3.org/ns/prov#")
    g.bind("mls",      "http://www.w3.org/ns/mls#")
    g.bind("qudt",     "http://qudt.org/schema/qudt/")
    g.bind("mdo",      "https://w3id.org/mdo/core/")
    g.bind("mdo-calc", "https://w3id.org/mdo/calculation/")

    g.serialize(destination=str(args.ttl), format="turtle")
    g.serialize(destination=str(args.owl), format="xml")

    print(f"  Saxon axioms:      {n_axioms} triples")
    print(f"  RDFa header CBD:   {len(header)} triples")
    print(f"  Merged total:      {n_total} triples")
    print(f"  Wrote {args.ttl}")
    print(f"  Wrote {args.owl}")


if __name__ == "__main__":
    main()
