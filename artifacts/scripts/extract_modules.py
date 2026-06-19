#!/usr/bin/env python3
"""Add machine-readable ontology modules to the generated OWL/TTL.

The ontology's thematic modules exist in the XHTML source only as
top-level `<section id="*-module">` sections; the extracted OWL/TTL has
no module representation, so a tool loading mlips.ttl cannot recover
which module a term belongs to (R1 reviewer: "no real modules"). This
step fixes that WITHOUT physically splitting the ontology:

  1. Each `<section id="<name>-module">` becomes an owl:Ontology
     `https://w3id.org/mlips/module/<name>` with rdfs:label from its <h2>.
  2. Every ontology term (class / object- / datatype- / annotation-
     property / named individual) gets `rdfs:isDefinedBy <its-module>`,
     derived from the module section that contains its owl-xml CDATA
     definition. The mapping is computed from the doc structure, so it
     cannot drift from it.

`rdfs:isDefinedBy` is chosen over a custom `mlips:inModule` because it
is the tool-recognized term for "the resource that defines this term"
(Protégé, Widoco, etc. surface it).

Run after merge_rdfa_into_owl.py: reads the merged mlips.ttl, adds the
module triples, and rewrites both mlips.ttl and mlips.owl.

The companion SHACL shape (shapes/mlips-shapes.ttl) enforces that every
mlips term resolves to exactly one declared module.

Usage:
    python3 artifacts/scripts/extract_modules.py
        [--xhtml artifacts/ontology/mlips.source.xhtml]
        [--owl   artifacts/ontology/mlips.owl]
        [--ttl   artifacts/ontology/mlips.ttl]
"""
import argparse
import re
import sys
from pathlib import Path

import rdflib
from rdflib import URIRef, Literal, RDF, RDFS, OWL
import html5lib

DCTERMS = rdflib.Namespace("http://purl.org/dc/terms/")
MLIPS = "https://w3id.org/mlips#"
MODULE_BASE = "https://w3id.org/mlips/module/"

# owl-xml elements that DEFINE a term (their rdf:about is the term IRI),
# as opposed to references (rdf:resource) inside axioms.
TERM_RE = re.compile(
    r'<owl:(?:Class|ObjectProperty|DatatypeProperty|AnnotationProperty|NamedIndividual)\b'
    r'[^>]*\brdf:about="([^"]+)"'
)
# Term types whose module membership the SHACL shape enforces.
ENFORCED_TYPES = (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty)


def _text(el):
    return "".join(el.itertext())


def module_map(xhtml_path):
    """Return (modules, term2module).

    modules: {name -> label} for every top-level `<section id="*-module">`.
    term2module: {term-IRI -> name} from the owl-xml CDATA in each module.
    """
    doc = html5lib.parse(open(xhtml_path, "rb"),
                         treebuilder="etree", namespaceHTMLElements=False)
    modules, term2module, descriptions, dupes = {}, {}, {}, []

    def walk(el, cur):
        sid = el.get("id")
        if el.tag == "section" and sid and sid.endswith("-module"):
            cur = sid[:-len("-module")]
            h2 = el.find(".//h2")
            modules[cur] = (_text(h2).strip() if h2 is not None else cur)
            desc = el.find(".//p[@class='module-description']")
            if desc is not None:
                descriptions[cur] = " ".join(_text(desc).split())
        cls = el.get("class") or ""
        if el.tag in ("pre", "code") and "owl-xml" in cls and cur:
            for iri in TERM_RE.findall(_text(el)):
                if iri in term2module and term2module[iri] != cur:
                    dupes.append((iri, term2module[iri], cur))
                term2module[iri] = cur
        for child in el:
            walk(child, cur)

    walk(doc, None)
    if dupes:
        raise SystemExit(f"ERROR: terms mapped to >1 module: {dupes}")
    return modules, term2module, descriptions


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    base = Path(__file__).resolve().parent.parent / "ontology"
    ap.add_argument("--xhtml", type=Path, default=base / "mlips.source.xhtml")
    ap.add_argument("--owl", type=Path, default=base / "mlips.owl")
    ap.add_argument("--ttl", type=Path, default=base / "mlips.ttl")
    args = ap.parse_args()

    modules, term2module, descriptions = module_map(args.xhtml)

    g = rdflib.Graph()
    g.parse(str(args.ttl), format="turtle")

    # 1. Declare each module as an owl:Ontology with its heading label and,
    # where the section carries a <p class="module-description"> intro, a
    # queryable dcterms:description (rendered as the section intro too).
    for name, label in modules.items():
        m = URIRef(MODULE_BASE + name)
        g.add((m, RDF.type, OWL.Ontology))
        g.add((m, RDFS.label, Literal(label, lang="en")))
        if name in descriptions:
            g.add((m, DCTERMS.description, Literal(descriptions[name], lang="en")))

    # 2. Annotate every term with rdfs:isDefinedBy <module>.
    for term, name in term2module.items():
        g.add((URIRef(term), RDFS.isDefinedBy, URIRef(MODULE_BASE + name)))

    # 3. Guard: every enforced mlips term must now resolve to exactly one
    # module. Catches a term added to the ontology outside any *-module
    # section (which would otherwise silently fail SHACL downstream).
    missing = []
    for t in ENFORCED_TYPES:
        for s in g.subjects(RDF.type, t):
            if not str(s).startswith(MLIPS):
                continue
            mods = list(g.objects(s, RDFS.isDefinedBy))
            if len(mods) != 1:
                missing.append((str(s), len(mods)))
    if missing:
        print("ERROR: terms not assigned to exactly one module "
              f"(check their *-module section): {missing}", file=sys.stderr)
        sys.exit(1)

    g.bind("mlips", MLIPS)
    g.bind("owl", str(OWL))
    g.bind("rdfs", str(RDFS))
    g.serialize(destination=str(args.ttl), format="turtle")
    g.serialize(destination=str(args.owl), format="xml")

    print(f"  Modules:           {len(modules)} ({', '.join(sorted(modules))})")
    print(f"  Descriptions:      {len(descriptions)} dcterms:description triples")
    print(f"  Terms annotated:   {len(term2module)} rdfs:isDefinedBy triples")
    print(f"  Wrote {args.ttl}")
    print(f"  Wrote {args.owl}")


if __name__ == "__main__":
    main()
