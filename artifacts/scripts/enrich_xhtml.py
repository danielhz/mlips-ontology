#!/usr/bin/env python3
"""Enrich the source XHTML ontology document with deterministic
extras for human readers:

  1. A table of contents derived from the existing <h2>/<h3>/<h4>
     section ids. Inserted after the <section id="ontology-metadata">
     block as <nav id="toc">.

  2. For every <section class="term class">, an "Outgoing properties"
     paragraph listing the object/datatype properties whose
     rdfs:domain is that class, and an "Incoming properties"
     paragraph listing the object properties whose rdfs:range is
     that class. Both lists are derived by parsing the embedded
     <pre class="owl-xml"> CDATA blocks of the property sections.

The script reads a source XHTML and writes an enriched copy. The
RDFa attributes and the OWL/XML CDATA blocks are preserved verbatim
so downstream tools (Saxon, pyRdfa, browsers) see the same triples
in either file.

Usage:
    python3 artifacts/scripts/enrich_xhtml.py
        [--source artifacts/ontology/mlips.source.xhtml]
        [--output artifacts/ontology/mlips.xhtml]
"""
import argparse
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

XHTML = "http://www.w3.org/1999/xhtml"
OWL = "http://www.w3.org/2002/07/owl#"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
ET.register_namespace("", XHTML)

MLIPS_NS = "https://w3id.org/mlips#"


def local_name(uri: str) -> str:
    """Return the local name of an IRI, e.g.,
    https://w3id.org/mlips#Hyperparameter -> Hyperparameter."""
    if uri.startswith(MLIPS_NS):
        return uri[len(MLIPS_NS):]
    if "#" in uri:
        return uri.rsplit("#", 1)[-1]
    return uri.rsplit("/", 1)[-1]


def is_mlips(uri: str) -> bool:
    return uri.startswith(MLIPS_NS)


# ---------------------------------------------------------------------------
# Step 1: extract domain/range relationships from the OWL/XML CDATA blocks.

def extract_domain_range(xhtml_text: str):
    """Walk every <pre class="owl-xml"> ... </pre> block and parse
    the OWL/XML inside. Returns two dicts:

        outgoing[class_local_name] -> sorted list of property local names
                                       (where this class is rdfs:domain)
        incoming[class_local_name] -> sorted list of object-property local names
                                       (where this class is rdfs:range)

    Restrictions and blank-node domain/range are ignored; only IRI
    domain/range targets are recorded.
    """
    outgoing: dict[str, set[str]] = {}
    incoming: dict[str, set[str]] = {}

    cdata_re = re.compile(
        r'<pre class="owl-xml"><code><!\[CDATA\[(.*?)\]\]></code></pre>',
        re.DOTALL,
    )
    for m in cdata_re.finditer(xhtml_text):
        snippet = m.group(1).strip()
        # Wrap each snippet in an rdf:RDF root with the prefixes the
        # source XHTML declares, so ElementTree can parse the QName
        # attribute values like rdf:about="...".
        wrapper = (
            f'<rdf:RDF xmlns:rdf="{RDF}" '
            f'xmlns:rdfs="{RDFS}" '
            f'xmlns:owl="{OWL}" '
            f'xmlns:xsd="http://www.w3.org/2001/XMLSchema#">'
            f'{snippet}'
            f'</rdf:RDF>'
        )
        try:
            root = ET.fromstring(wrapper)
        except ET.ParseError:
            continue

        # We are interested only in property declarations:
        # <owl:ObjectProperty rdf:about="..."> ... </owl:ObjectProperty>
        # <owl:DatatypeProperty rdf:about="..."> ... </owl:DatatypeProperty>
        for prop_el in root:
            if prop_el.tag not in (f"{{{OWL}}}ObjectProperty",
                                   f"{{{OWL}}}DatatypeProperty"):
                continue
            prop_iri = prop_el.attrib.get(f"{{{RDF}}}about", "")
            if not is_mlips(prop_iri):
                continue
            prop_local = local_name(prop_iri)

            for child in prop_el:
                if child.tag == f"{{{RDFS}}}domain":
                    target_iri = child.attrib.get(f"{{{RDF}}}resource", "")
                    if is_mlips(target_iri):
                        outgoing.setdefault(local_name(target_iri),
                                            set()).add(prop_local)
                elif (child.tag == f"{{{RDFS}}}range"
                      and prop_el.tag == f"{{{OWL}}}ObjectProperty"):
                    target_iri = child.attrib.get(f"{{{RDF}}}resource", "")
                    if is_mlips(target_iri):
                        incoming.setdefault(local_name(target_iri),
                                            set()).add(prop_local)

    return ({k: sorted(v) for k, v in outgoing.items()},
            {k: sorted(v) for k, v in incoming.items()})


# ---------------------------------------------------------------------------
# Step 2: walk the source XHTML and emit an enriched copy.

# Source uses ad-hoc HTML rather than strict XML in some places
# (e.g., self-closing <meta /> with attributes that ElementTree mangles),
# so we rewrite via regex on the raw text rather than DOM manipulation.
# This keeps the CDATA sections, comments, and attribute order intact.


HEADER_RE = re.compile(
    r'(<section id="([^"]+)"[^>]*>\s*<h(\d)[^>]*>(.*?)</h\3>)',
    re.DOTALL,
)
TERM_CLASS_RE = re.compile(
    r'(<section id="(?P<id>[^"]+)" class="term class"[^>]*>.*?<pre class="owl-xml">)',
    re.DOTALL,
)
ONTOLOGY_METADATA_END_RE = re.compile(
    r'(</section>)\s*\n\s*(<section id="algorithm-module">)',
    re.DOTALL,
)


def build_toc(xhtml_text: str) -> str:
    """Build a simple inline table of contents from <section id=...>
    elements with header tags h1-h4. The TOC is a nested <ul> reflecting
    the heading hierarchy."""
    # Iterate sections that have an id and a heading at the top.
    entries = []
    for sec_match in re.finditer(
        r'<section id="(?P<sid>[^"]+)"[^>]*>\s*'
        r'<h(?P<lvl>[1-4])[^>]*>(?P<text>.*?)</h(?P=lvl)>',
        xhtml_text, re.DOTALL,
    ):
        sid = sec_match.group("sid")
        lvl = int(sec_match.group("lvl"))
        # Strip inner tags from the heading text.
        text = re.sub(r"<[^>]+>", "", sec_match.group("text")).strip()
        if sid == "ontology-metadata":
            continue  # the TOC sits below this section; skip self-link
        entries.append((lvl, sid, text))

    # Build nested HTML based on level transitions. The stack tracks
    # the heading levels of currently open <ul> elements. Sibling
    # entries at the same level reuse the open <ul>; deeper entries
    # open a new <ul>; shallower entries close one or more <ul>s.
    out = ['<nav id="toc" aria-label="Table of contents">',
           '  <h2 class="toc-heading">Table of Contents</h2>']
    stack: list[int] = []
    for lvl, sid, text in entries:
        # Close lists that are deeper than the current entry's level.
        while stack and stack[-1] > lvl:
            stack.pop()
            out.append('  ' * (len(stack) + 1) + '</ul>')
        # Open a new list if we're going deeper.
        if not stack or stack[-1] < lvl:
            out.append('  ' * (len(stack) + 1) + '<ul>')
            stack.append(lvl)
        # Emit the <li> at the current depth.
        out.append('  ' * (len(stack) + 1)
                   + f'<li><a href="#{sid}">{text}</a></li>')
    # Close any still-open lists.
    while stack:
        stack.pop()
        out.append('  ' * (len(stack) + 1) + '</ul>')
    out.append('</nav>')
    return "\n".join(out) + "\n"


def render_property_block(class_local: str,
                          outgoing: dict[str, list[str]],
                          incoming: dict[str, list[str]]) -> str:
    """Render two paragraphs (or omit if empty) listing outgoing and
    incoming properties for a class."""
    out_props = outgoing.get(class_local, [])
    in_props = incoming.get(class_local, [])
    if not out_props and not in_props:
        return ""

    def fmt(props: list[str]) -> str:
        return ", ".join(
            f'<a href="#{p}"><code>mlips:{p}</code></a>' for p in props
        )

    lines = ['      <div class="term-properties">']
    if out_props:
        lines.append(
            f'        <p><strong>Outgoing properties:</strong> {fmt(out_props)}</p>'
        )
    if in_props:
        lines.append(
            f'        <p><strong>Incoming properties:</strong> {fmt(in_props)}</p>'
        )
    lines.append('      </div>')
    return "\n".join(lines) + "\n"


def enrich(source_text: str) -> str:
    """Apply both enrichments: TOC after the metadata section, and
    property blocks before the OWL/XML CDATA inside each class
    section."""
    outgoing, incoming = extract_domain_range(source_text)

    # 1. Inject TOC right after the </section> that closes the
    #    ontology-metadata block. We detect that boundary by the
    #    transition from </section> to the first <section
    #    id="...-module"> in the body.
    toc = build_toc(source_text)
    enriched = ONTOLOGY_METADATA_END_RE.sub(
        lambda m: f"{m.group(1)}\n\n{toc}\n{m.group(2)}",
        source_text, count=1,
    )

    # 2. For each class section, inject the property block right
    #    before the <pre class="owl-xml"> opener.
    def inject_props(m: re.Match) -> str:
        cls_local = m.group("id")
        block = render_property_block(cls_local, outgoing, incoming)
        if not block:
            return m.group(0)
        return m.group(0).replace(
            '<pre class="owl-xml">',
            f'{block.rstrip()}\n      <pre class="owl-xml">',
        )

    enriched = TERM_CLASS_RE.sub(inject_props, enriched)
    return enriched


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    base = Path(__file__).resolve().parent.parent / "ontology"
    parser.add_argument("--source", type=Path, default=base / "mlips.source.xhtml")
    parser.add_argument("--output", type=Path, default=base / "mlips.xhtml")
    args = parser.parse_args()

    source = args.source.read_text(encoding="utf-8")
    enriched = enrich(source)
    args.output.write_text(enriched, encoding="utf-8")

    out_count = source.count("<section ") - enriched.count("<section ")
    classes_with_props = sum(
        1 for m in re.finditer(r'<section id="[^"]+" class="term class"',
                               enriched)
    )
    toc_entries = enriched.count('<li><a href="#')

    print(f"  Source:   {args.source}")
    print(f"  Output:   {args.output}")
    print(f"  TOC entries: {toc_entries}")
    print(f"  Class sections processed: {classes_with_props}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
