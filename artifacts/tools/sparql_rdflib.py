#!/usr/bin/env python3
"""Pure-Python engine behind artifacts/tools/sparql.

Executes one SPARQL query file against one Turtle data file with
rdflib (pinned in requirements.lock) and prints results in the format
the KG scripts expect: N-triples for CONSTRUCT/DESCRIBE, TSV (header
line + one line per row) for SELECT/ASK. Slower than oxigraph but
dependency-free beyond the repo's build venv.
"""

import argparse
import sys

try:
    import rdflib
    from rdflib import Graph
except ImportError:
    sys.exit(
        "sparql_rdflib.py: rdflib not importable -- run `make venv` first "
        "(or install oxigraph_server for the fast path)."
    )

# Keep literal lexical forms exactly as written in the source Turtle
# ("520"^^xsd:double must not become "520.0"): the round-trip checker
# compares canonicalised bytes, and oxigraph preserves lexical forms.
rdflib.NORMALIZE_LITERALS = False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help="SPARQL query file (.rq)")
    ap.add_argument("--graph", required=True, help="Turtle data file")
    ap.add_argument("--format", choices=["nt", "tsv"], required=True)
    args = ap.parse_args()

    g = Graph()
    g.parse(args.graph, format="turtle")
    with open(args.query, encoding="utf-8") as fh:
        query = fh.read()
    result = g.query(query)

    if args.format == "nt":
        out = Graph()
        for triple in result:
            out.add(triple)
        sys.stdout.write(out.serialize(format="nt"))
    elif result.type == "ASK":
        print("ask")
        print("true" if result.askAnswer else "false")
    else:
        variables = result.vars or []
        print("\t".join("?%s" % v for v in variables))
        for row in result:
            print(
                "\t".join(
                    term.n3() if term is not None else "" for term in row
                )
            )


if __name__ == "__main__":
    main()
