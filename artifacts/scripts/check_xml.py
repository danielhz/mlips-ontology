#!/usr/bin/env python3
"""Fail if any given file is not well-formed XML.

The ontology source (mlips.source.xhtml) and published doc (mlips.xhtml)
are XHTML and MUST be valid XML: HTML-only named entities (&ldquo;,
&mdash;, &nbsp;, ...) are undefined in XML and make a browser serving the
document as application/xhtml+xml throw "XML Parsing Error: undefined
entity". This check uses the strict stdlib XML parser -- NOT the HTML5
parser the RDFa extraction (merge_rdfa_into_owl.py) uses, which silently
tolerates such entities and would mask the bug.

Usage: check_xml.py <file.xhtml> [<file.xhtml> ...]
"""
import sys
import xml.etree.ElementTree as ET

bad = 0
for path in sys.argv[1:]:
    try:
        ET.parse(path)
        print(f"  XML OK: {path}")
    except ET.ParseError as e:
        print(f"  XML MALFORMED: {path}: {e}", file=sys.stderr)
        bad = 1
sys.exit(bad)
