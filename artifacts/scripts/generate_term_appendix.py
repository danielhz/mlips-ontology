#!/usr/bin/env python3
"""Generate LaTeX appendices for ontology terms from mlips.ttl.

Reads the ontology file and produces three .tex files:
  sections/appendix-classes.tex
  sections/appendix-object-properties.tex
  sections/appendix-data-properties.tex

Examples are included via \\InputIfFileExists from artifacts/examples/.
Skeleton example files are generated for missing terms.
"""

import sys
from pathlib import Path
from rdflib import Graph, Namespace, RDF, RDFS, OWL, XSD

MLIPS = Namespace("https://kg.ki.uni-stuttgart.de/_ontology/mlips#")
PROV = Namespace("http://www.w3.org/ns/prov#")
MLS = Namespace("http://www.w3.org/ns/mls#")
SCHEMA = Namespace("https://schema.org/")

# Axiom mapping: (subject_local, property_local_or_type, kind) -> axiom tag
# kind: 'some' for existential, 'exact' for cardinality, 'domain' for domain GCI,
#       'chain' for property chain, 'inv-some' for inverse existential
AXIOM_MAP = {
    # Algorithm Module
    ("MLIPAlgorithm", "hasHyperparameter", "some"): "A1",
    ("MLIPAlgorithm", "supportsSimulation", "some"): "A2",
    ("Implementation", "implementedIn", "some"): "A3",
    ("TrainingRun", "executes", "exact"): "A4",
    ("TrainingRun", "runsOn", "exact"): "A5",
    ("TrainingRun", "produces", "exact"): "A6",
    ("TrainedModel", "produces", "inv-some"): "A7",
    ("Hyperparameter", "hasHyperparameter", "inv-some"): "A8",
    ("Implementation", "hasImplementation", "inv-some"): "A9",
    ("trainedWith", None, "chain"): "A10",
    ("trainedOn", None, "chain"): "A11",
    ("hasHyperparameter", None, "domain"): "A12",
    ("hasImplementation", None, "domain"): "A13",
    ("supportsSimulation", None, "domain"): "A14",
    # Training Data Module
    ("TrainingDataset", "coversMaterial", "some"): "A15",
    ("TrainingDataset", "coversProperty", "some"): "A16",
    ("TrainingDataset", "datasetProvenance", "some"): "A17",
    ("TrainingDataset", "hasConfiguration", "some"): "A18",
    ("DFTCalculation", "hasDFTSettings", "some"): "A19",
    # Benchmark Module
    ("BenchmarkStudy", "hasResult", "some"): "A20",
    ("BenchmarkResult", "evaluatesModel", "exact"): "A21",
    ("BenchmarkResult", "targetMaterial", "some"): "A22",
    ("BenchmarkResult", "hasAccuracyMetric", "some"): "A23",
    ("AccuracyMetric", "metricType", "exact"): "A24",
    ("AccuracyMetric", "metricProperty", "exact"): "A25",
    ("BenchmarkResult", "hasResult", "inv-some"): "A26",
    ("AccuracyMetric", "hasAccuracyMetric", "inv-some"): "A27",
}


def local_name(uri):
    """Extract local name from URI."""
    s = str(uri)
    return s.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def tex_escape(s):
    """Minimal TeX escaping."""
    return s.replace("_", "\\_").replace("#", "\\#").replace("&", "\\&")


def macro_name_concept(local):
    """Generate the LaTeX macro name for a concept."""
    return f"\\dlConcept{{{local}}}"


def macro_name_role(local):
    """Generate the LaTeX macro name for a role."""
    return f"\\dlRole{{{local}}}"


def get_axioms_for_class(cls_local, outgoing, incoming):
    """Find axiom tags relevant to a class."""
    tags = []
    # Check existential/cardinality axioms where this class is the subject
    for key, tag in AXIOM_MAP.items():
        subj, prop, kind = key
        if subj == cls_local and kind in ("some", "exact", "inv-some"):
            tags.append(tag)
    # Check domain axioms where this class is the domain
    for key, tag in AXIOM_MAP.items():
        subj, prop, kind = key
        if kind == "domain":
            # domain axiom: subj is the property name, class is MLIPAlgorithm
            pass  # handled below
    return sorted(set(tags), key=lambda t: int(t[1:]))


def get_axioms_for_property(prop_local):
    """Find axiom tags relevant to a property."""
    tags = []
    for key, tag in AXIOM_MAP.items():
        subj, prop, kind = key
        if prop == prop_local:
            tags.append(tag)
        if subj == prop_local and kind in ("chain", "domain"):
            tags.append(tag)
    return sorted(set(tags), key=lambda t: int(t[1:]))


def format_domain_range(g, prop_uri):
    """Get domain and range as local names."""
    domains = [local_name(d) for d in g.objects(prop_uri, RDFS.domain)]
    ranges = [local_name(r) for r in g.objects(prop_uri, RDFS.range)]
    return domains, ranges


def generate_class_section(g, cls_uri, all_obj_props, all_dt_props):
    """Generate LaTeX for one class subsection."""
    local = local_name(cls_uri)
    label = str(next(g.objects(cls_uri, RDFS.label), local))
    comment = str(next(g.objects(cls_uri, RDFS.comment), ""))

    # Superclasses
    supers = []
    for sc in g.objects(cls_uri, RDFS.subClassOf):
        if isinstance(sc, type(cls_uri)):  # URIRef, not BNode
            sl = local_name(sc)
            if sl != local:
                supers.append(sl)

    # Outgoing properties (this class is domain)
    outgoing = []
    for prop_uri in all_obj_props + all_dt_props:
        for d in g.objects(prop_uri, RDFS.domain):
            if d == cls_uri:
                outgoing.append(local_name(prop_uri))

    # Incoming properties (this class is range)
    incoming = []
    for prop_uri in all_obj_props:
        for r in g.objects(prop_uri, RDFS.range):
            if r == cls_uri:
                incoming.append(local_name(prop_uri))

    axioms = get_axioms_for_class(local, outgoing, incoming)

    lines = []
    lines.append(f"\\subsection{{{macro_name_concept(local)}}}")
    lines.append(f"\\label{{sec:term-{local}}}")
    lines.append("")
    lines.append(f"\\textbf{{Label:}} {tex_escape(label)}.")
    if comment:
        lines.append(f"{tex_escape(comment.strip())}")
    lines.append("")

    if supers:
        super_strs = [f"${macro_name_concept(s)}$" for s in supers]
        lines.append(f"\\paragraph{{Superclasses.}} {', '.join(super_strs)}.")
        lines.append("")

    if outgoing:
        out_strs = [f"${macro_name_role(p)}$" for p in outgoing]
        lines.append(f"\\paragraph{{Outgoing properties.}} {', '.join(out_strs)}.")
        lines.append("")

    if incoming:
        in_strs = [f"${macro_name_role(p)}$" for p in incoming]
        lines.append(f"\\paragraph{{Incoming properties.}} {', '.join(in_strs)}.")
        lines.append("")

    # Example
    example_path = f"artifacts/examples/classes/{local}.tex"
    lines.append("\\paragraph{Example.}")
    lines.append(f"\\InputIfFileExists{{{example_path}}}{{}}{{\\textit{{TODO: add example.}}}}")
    lines.append("")

    if axioms:
        refs = ", ".join(f"({t})" for t in axioms)
        lines.append(f"\\paragraph{{Related axioms.}} {refs}.")
        lines.append("")

    return "\n".join(lines)


def generate_property_section(g, prop_uri, prop_type="object"):
    """Generate LaTeX for one property subsection."""
    local = local_name(prop_uri)
    label = str(next(g.objects(prop_uri, RDFS.label), local))
    comment = str(next(g.objects(prop_uri, RDFS.comment), ""))

    domains, ranges = format_domain_range(g, prop_uri)

    axioms = get_axioms_for_property(local)

    lines = []
    lines.append(f"\\subsection{{{macro_name_role(local)}}}")
    lines.append(f"\\label{{sec:term-{local}}}")
    lines.append("")
    lines.append(f"\\textbf{{Label:}} {tex_escape(label)}.")
    if comment:
        lines.append(f"{tex_escape(comment.strip())}")
    lines.append("")

    if domains:
        dom_strs = [f"${macro_name_concept(d)}$" for d in domains]
        lines.append(f"\\textbf{{Domain:}} {', '.join(dom_strs)}.")
    if ranges:
        rng_strs = []
        for r in ranges:
            if r.startswith("xsd:") or r in ("double", "integer", "string", "Literal"):
                rng_strs.append(f"\\texttt{{{r}}}")
            else:
                rng_strs.append(f"${macro_name_concept(r)}$")
        lines.append(f"\\textbf{{Range:}} {', '.join(rng_strs)}.")
    lines.append("")

    # Example
    subdir = "object-properties" if prop_type == "object" else "data-properties"
    example_path = f"artifacts/examples/{subdir}/{local}.tex"
    lines.append("\\paragraph{Example.}")
    lines.append(f"\\InputIfFileExists{{{example_path}}}{{}}{{\\textit{{TODO: add example.}}}}")
    lines.append("")

    if axioms:
        refs = ", ".join(f"({t})" for t in axioms)
        lines.append(f"\\paragraph{{Related axioms.}} {refs}.")
        lines.append("")

    return "\n".join(lines)


def main():
    base_dir = Path(__file__).resolve().parent.parent.parent
    onto_path = base_dir / "artifacts" / "ontology" / "mlips.ttl"
    sections_dir = base_dir / "sections"
    examples_dir = base_dir / "artifacts" / "examples"

    g = Graph()
    g.parse(str(onto_path), format="turtle")

    # Collect terms
    classes = sorted(
        [c for c in g.subjects(RDF.type, OWL.Class) if str(c).startswith(str(MLIPS))],
        key=lambda c: local_name(c),
    )
    obj_props = sorted(
        [p for p in g.subjects(RDF.type, OWL.ObjectProperty) if str(p).startswith(str(MLIPS))],
        key=lambda p: local_name(p),
    )
    dt_props = sorted(
        [p for p in g.subjects(RDF.type, OWL.DatatypeProperty) if str(p).startswith(str(MLIPS))],
        key=lambda p: local_name(p),
    )

    print(f"Found {len(classes)} classes, {len(obj_props)} object properties, {len(dt_props)} datatype properties")

    # Generate classes appendix
    cls_lines = [
        "\\section{Class Reference}",
        "\\label{sec:class-reference}",
        "",
        f"This appendix describes all {len(classes)} classes defined in the \\MLIPsOntology{{}}.",
        "",
    ]
    for cls_uri in classes:
        cls_lines.append(generate_class_section(g, cls_uri, obj_props, dt_props))

    with open(sections_dir / "appendix-classes.tex", "w") as f:
        f.write("\n".join(cls_lines))

    # Generate object properties appendix
    op_lines = [
        "\\section{Object Property Reference}",
        "\\label{sec:object-property-reference}",
        "",
        f"This appendix describes all {len(obj_props)} object properties defined in the \\MLIPsOntology{{}}.",
        "",
    ]
    for prop_uri in obj_props:
        op_lines.append(generate_property_section(g, prop_uri, "object"))

    with open(sections_dir / "appendix-object-properties.tex", "w") as f:
        f.write("\n".join(op_lines))

    # Generate datatype properties appendix
    dp_lines = [
        "\\section{Datatype Property Reference}",
        "\\label{sec:datatype-property-reference}",
        "",
        f"This appendix describes all {len(dt_props)} datatype properties defined in the \\MLIPsOntology{{}}.",
        "",
    ]
    for prop_uri in dt_props:
        dp_lines.append(generate_property_section(g, prop_uri, "data"))

    with open(sections_dir / "appendix-data-properties.tex", "w") as f:
        f.write("\n".join(dp_lines))

    # Generate skeleton example files for missing ones
    created = 0
    for cls_uri in classes:
        local = local_name(cls_uri)
        path = examples_dir / "classes" / f"{local}.tex"
        if not path.exists():
            label = str(next(g.objects(cls_uri, RDFS.label), local))
            path.write_text(
                f"% Example for {local}\n"
                f"\\begin{{lstlisting}}[language=turtle]\n"
                f"ex:{local.lower()}01 a mlips:{local} ;\n"
                f'    rdfs:label "{label} example" .\n'
                f"\\end{{lstlisting}}\n"
            )
            created += 1

    for prop_uri in obj_props:
        local = local_name(prop_uri)
        path = examples_dir / "object-properties" / f"{local}.tex"
        if not path.exists():
            domains, ranges = format_domain_range(g, prop_uri)
            dom = domains[0].lower() if domains else "subject"
            rng = ranges[0].lower() if ranges else "object"
            path.write_text(
                f"% Example for {local}\n"
                f"\\begin{{lstlisting}}[language=turtle]\n"
                f"ex:{dom}01 mlips:{local} ex:{rng}01 .\n"
                f"\\end{{lstlisting}}\n"
            )
            created += 1

    for prop_uri in dt_props:
        local = local_name(prop_uri)
        path = examples_dir / "data-properties" / f"{local}.tex"
        if not path.exists():
            domains, ranges = format_domain_range(g, prop_uri)
            dom = domains[0].lower() if domains else "subject"
            rng_local = ranges[0] if ranges else "string"
            if rng_local == "double":
                val = "1.0"
            elif rng_local == "integer":
                val = "1"
            else:
                val = '"value"'
            path.write_text(
                f"% Example for {local}\n"
                f"\\begin{{lstlisting}}[language=turtle]\n"
                f"ex:{dom}01 mlips:{local} {val} .\n"
                f"\\end{{lstlisting}}\n"
            )
            created += 1

    print(f"Created {created} skeleton example files")


if __name__ == "__main__":
    main()
