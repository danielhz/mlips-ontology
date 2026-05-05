#!/usr/bin/env python3
"""Pure-Python substitute for Saxon's extract-owl.xsl.

Pulls every <pre class="owl-xml"><code><![CDATA[...]]></code></pre>
block from artifacts/ontology/mlips.source.xhtml, wraps the blocks
in an rdf:RDF root with the schema's namespace prefixes, and writes
the result to artifacts/ontology/mlips.owl.

Used by the Makefile's `ontology` target when Saxon (with the
concon-onto extract-owl.xsl) is not installed; produces the same
RDF/XML output that merge_rdfa_into_owl.py expects to see.

Usage:  python3 artifacts/scripts/extract_owl.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "artifacts/ontology/mlips.source.xhtml"
OUT = ROOT / "artifacts/ontology/mlips.owl"

text = SRC.read_text()

pattern = re.compile(
    r'<pre class="owl-xml"><code><!\[CDATA\[(.*?)\]\]></code></pre>',
    re.DOTALL,
)

blocks = pattern.findall(text)
print(f"Extracted {len(blocks)} owl-xml CDATA blocks", file=sys.stderr)

# rdf:RDF root with the namespace prefixes the CDATA blocks rely on.
# `mlips:` is needed for the metaSort annotation triples (issue 0010);
# the rest match the prefixes already used by the per-term axioms.
header = '''<?xml version="1.0" encoding="utf-8"?>
<rdf:RDF
   xmlns:dcterms="http://purl.org/dc/terms/"
   xmlns:owl="http://www.w3.org/2002/07/owl#"
   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
   xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
   xmlns:schema="https://schema.org/"
   xmlns:vann="http://purl.org/vocab/vann/"
   xmlns:xsd="http://www.w3.org/2001/XMLSchema#"
   xmlns:mls="http://www.w3.org/ns/mls#"
   xmlns:prov="http://www.w3.org/ns/prov#"
   xmlns:mdo="https://w3id.org/mdo/core/"
   xmlns:mdo-calc="https://w3id.org/mdo/calculation/"
   xmlns:qudt="http://qudt.org/schema/qudt/"
   xmlns:mlips="https://w3id.org/mlips#"
>
'''
footer = '</rdf:RDF>\n'

OUT.write_text(header + "\n".join(blocks) + "\n" + footer)
print(f"Wrote {OUT}", file=sys.stderr)
