#!/usr/bin/env python3
"""Transform the MLIPs ontology (Turtle) into Graphviz DOT format.

Produces four DOT files:
  - mlips-overview.dot      : High-level overview of all three modules
  - mlips-algorithm.dot     : Algorithm module with instance examples
  - mlips-training-data.dot : Training Data module with instance examples
  - mlips-benchmark.dot     : Benchmark module with instance examples

Usage:
    python ontology_to_dot.py [--ontology PATH] [--outdir PATH]

Defaults:
    --ontology ../ontology/mlips.ttl
    --outdir   ../figures/
"""

import argparse
import sys
from pathlib import Path

try:
    from rdflib import Graph, RDF, RDFS, OWL, Namespace
except ImportError:
    print("rdflib is required: pip install rdflib", file=sys.stderr)
    sys.exit(1)


MLIPS = Namespace("https://kg.degu.cl/ontology/mlips#")

# ── Styling ──────────────────────────────────────────────────────────────────

GRAPH_ATTRS = (
    'rankdir=LR;\n'
    'fontname="Helvetica";\n'
    'fontsize=10;\n'
    'node [fontname="Helvetica", fontsize=9];\n'
    'edge [fontname="Helvetica", fontsize=8];\n'
)

CLASS_STYLE = 'shape=box, style="rounded,filled", fillcolor="#ddeeff"'
INSTANCE_STYLE = 'shape=box, style="filled", fillcolor="#fff4cc"'
LITERAL_STYLE = 'shape=plaintext, fontcolor="#666666"'
EXTERNAL_STYLE = 'shape=box, style="rounded,dashed,filled", fillcolor="#e8e8e8"'
MODULE_COLORS = {
    "algorithm": "#c6dbef",
    "training": "#c7e9c0",
    "benchmark": "#fdd0a2",
}


def local_name(uri):
    """Extract local name from a URI."""
    s = str(uri)
    for sep in ("#", "/"):
        if sep in s:
            s = s.rsplit(sep, 1)[-1]
    return s


def read_ontology(path):
    """Parse the ontology and return an rdflib Graph."""
    g = Graph()
    g.parse(path, format="turtle")
    return g


def get_classes(g):
    """Return all mlips: classes as local names."""
    classes = set()
    for s in g.subjects(RDF.type, OWL.Class):
        if str(s).startswith(str(MLIPS)):
            classes.add(local_name(s))
    return classes


def get_object_properties(g):
    """Return (property_local_name, domain_local, range_local) triples."""
    props = []
    for s in g.subjects(RDF.type, OWL.ObjectProperty):
        if not str(s).startswith(str(MLIPS)):
            continue
        name = local_name(s)
        domain = None
        range_ = None
        for o in g.objects(s, RDFS.domain):
            domain = local_name(o)
        for o in g.objects(s, RDFS.range):
            range_ = local_name(o)
        if domain and range_:
            props.append((name, domain, range_))
    return props


def get_subclass_of(g):
    """Return (child_local, parent_local) pairs for external parents."""
    pairs = []
    for s, _, o in g.triples((None, RDFS.subClassOf, None)):
        if str(s).startswith(str(MLIPS)) and not str(o).startswith(str(MLIPS)):
            pairs.append((local_name(s), local_name(o)))
    return pairs


# ── DOT generation ───────────────────────────────────────────────────────────

def generate_overview_dot(g):
    """High-level overview: modules as clusters, classes as nodes."""
    algorithm_classes = [
        "MLIPAlgorithm", "Hyperparameter", "HyperparameterSetting",
        "Implementation", "Library", "SimulationType",
    ]
    training_classes = [
        "TrainingDataset", "DFTCalculation", "DFTSettings",
        "MaterialSystem", "AtomicConfiguration",
        "DatasetProvenance", "CoveredProperty",
    ]
    benchmark_classes = [
        "BenchmarkStudy", "BenchmarkResult", "AccuracyMetric",
        "MetricType", "MetricProperty",
    ]

    props = get_object_properties(g)
    subclasses = get_subclass_of(g)

    lines = [f"digraph mlips_overview {{\n{GRAPH_ATTRS}"]

    # Algorithm cluster
    lines.append(f'  subgraph cluster_algorithm {{')
    lines.append(f'    label="Algorithm Module";')
    lines.append(f'    style=filled; color="{MODULE_COLORS["algorithm"]}";')
    for c in algorithm_classes:
        lines.append(f'    {c} [{CLASS_STYLE}];')
    lines.append('  }')

    # Training Data cluster
    lines.append(f'  subgraph cluster_training {{')
    lines.append(f'    label="Training Data Module";')
    lines.append(f'    style=filled; color="{MODULE_COLORS["training"]}";')
    for c in training_classes:
        lines.append(f'    {c} [{CLASS_STYLE}];')
    lines.append('  }')

    # Benchmark cluster
    lines.append(f'  subgraph cluster_benchmark {{')
    lines.append(f'    label="Benchmark Module";')
    lines.append(f'    style=filled; color="{MODULE_COLORS["benchmark"]}";')
    for c in benchmark_classes:
        lines.append(f'    {c} [{CLASS_STYLE}];')
    lines.append('  }')

    # External classes
    external = set()
    for child, parent in subclasses:
        external.add(parent)
    for ext in sorted(external):
        lines.append(f'  {ext} [{EXTERNAL_STYLE}];')

    # Subclass edges
    for child, parent in subclasses:
        lines.append(
            f'  {child} -> {parent} '
            f'[label="rdfs:subClassOf", style=dashed, arrowhead=empty];'
        )

    # Object property edges
    for name, domain, range_ in props:
        lines.append(f'  {domain} -> {range_} [label="{name}"];')

    lines.append("}")
    return "\n".join(lines)


def _instance_node(node_id, label, style=INSTANCE_STYLE):
    return f'  {node_id} [label="{label}", {style}];'


def _literal_node(node_id, label):
    escaped = label.replace('"', '\\"')
    return f'  {node_id} [label="{escaped}", {LITERAL_STYLE}];'


def _edge(src, dst, label=""):
    if label:
        return f'  {src} -> {dst} [label="{label}"];'
    return f'  {src} -> {dst};'


def generate_algorithm_instance_dot():
    """Algorithm module with MACE example instances."""
    lines = [f"digraph mlips_algorithm_example {{\n{GRAPH_ATTRS}"]
    lines.append('  label="Algorithm Module — Example: MACE";')
    lines.append('  labelloc=t; fontsize=12;')

    # Instances
    lines.append(_instance_node("mace", "mlips:mace-algorithm\\n(MLIPAlgorithm)\\n«MACE»"))
    lines.append(_instance_node("hp_cutoff", "mlips:mace-cutoff-radius\\n(Hyperparameter)"))
    lines.append(_instance_node("hp_layers", "mlips:mace-num-layers\\n(Hyperparameter)"))
    lines.append(_instance_node("hp_lr", "mlips:mace-learning-rate\\n(Hyperparameter)"))
    lines.append(_instance_node("impl", "mlips:mace-impl-v03\\n(Implementation)\\n«MACE v0.3»"))
    lines.append(_instance_node("lib", "mlips:lib-mace-python\\n(Library)"))
    lines.append(_instance_node("sim_md", "mlips:sim-md\\n(SimulationType)\\n«Molecular dynamics»"))
    lines.append(_instance_node("sim_opt", "mlips:sim-geometry-opt\\n(SimulationType)\\n«Geometry opt.»"))

    # Literals
    lines.append(_literal_node("l_name", '"cutoff_radius"'))
    lines.append(_literal_node("l_default", '"5.0"^^xsd:double'))
    lines.append(_literal_node("l_min", '"2.0"^^xsd:double'))
    lines.append(_literal_node("l_max", '"10.0"^^xsd:double'))
    lines.append(_literal_node("l_version", '"0.3.0"'))

    # Edges
    lines.append(_edge("mace", "hp_cutoff", "hasHyperparameter"))
    lines.append(_edge("mace", "hp_layers", "hasHyperparameter"))
    lines.append(_edge("mace", "hp_lr", "hasHyperparameter"))
    lines.append(_edge("mace", "impl", "hasImplementation"))
    lines.append(_edge("mace", "sim_md", "supportsSimulation"))
    lines.append(_edge("mace", "sim_opt", "supportsSimulation"))
    lines.append(_edge("impl", "lib", "implementedIn"))
    lines.append(_edge("hp_cutoff", "l_name", "hyperparameterName"))
    lines.append(_edge("hp_cutoff", "l_default", "defaultValue"))
    lines.append(_edge("hp_cutoff", "l_min", "minValue"))
    lines.append(_edge("hp_cutoff", "l_max", "maxValue"))
    lines.append(_edge("impl", "l_version", "version"))

    lines.append("}")
    return "\n".join(lines)


def generate_training_data_instance_dot():
    """Training Data module with Ti-Al dataset example."""
    lines = [f"digraph mlips_training_example {{\n{GRAPH_ATTRS}"]
    lines.append('  label="Training Data Module — Example: Ti-Al Dataset";')
    lines.append('  labelloc=t; fontsize=12;')

    lines.append(_instance_node("ds", "mlips:tial-dataset-2024\\n(TrainingDataset)\\n«Ti-Al DFT dataset»"))
    lines.append(_instance_node("mat", "mlips:mat-tial\\n(MaterialSystem)\\n«Ti-Al»"))
    lines.append(_instance_node("calc", "mlips:tial-dft-calc\\n(DFTCalculation)"))
    lines.append(_instance_node("settings", "mlips:tial-dft-settings\\n(DFTSettings)"))
    lines.append(_instance_node("vasp", "mlips:lib-vasp\\n(Library)\\n«VASP»"))
    lines.append(_instance_node("prov", "mlips:InHouse\\n(DatasetProvenance)"))
    lines.append(_instance_node("prop_e", "mlips:Energy\\n(CoveredProperty)"))
    lines.append(_instance_node("prop_f", "mlips:Forces\\n(CoveredProperty)"))
    lines.append(_instance_node("prop_s", "mlips:Stresses\\n(CoveredProperty)"))

    lines.append(_literal_node("l_nconf", '"15000"^^xsd:integer'))
    lines.append(_literal_node("l_xc", '"PBE"'))
    lines.append(_literal_node("l_kpt", '"4x4x4"'))
    lines.append(_literal_node("l_ecut", '"500.0"^^xsd:double'))
    lines.append(_literal_node("l_pp", '"PAW"'))
    lines.append(_literal_node("l_formula", '"TiAl"'))
    lines.append(_literal_node("l_class", '"binary alloy"'))

    lines.append(_edge("ds", "mat", "coversMaterial"))
    lines.append(_edge("ds", "calc", "hasDFTCalculation"))
    lines.append(_edge("ds", "prov", "datasetProvenance"))
    lines.append(_edge("ds", "prop_e", "coversProperty"))
    lines.append(_edge("ds", "prop_f", "coversProperty"))
    lines.append(_edge("ds", "prop_s", "coversProperty"))
    lines.append(_edge("ds", "l_nconf", "numConfigurations"))
    lines.append(_edge("calc", "settings", "hasDFTSettings"))
    lines.append(_edge("settings", "vasp", "usedDFTCode"))
    lines.append(_edge("settings", "l_xc", "xcFunctional"))
    lines.append(_edge("settings", "l_kpt", "kPointMesh"))
    lines.append(_edge("settings", "l_ecut", "energyCutoff"))
    lines.append(_edge("settings", "l_pp", "pseudopotentialType"))
    lines.append(_edge("mat", "l_formula", "chemicalFormula"))
    lines.append(_edge("mat", "l_class", "materialClass"))

    lines.append("}")
    return "\n".join(lines)


def generate_benchmark_instance_dot():
    """Benchmark module with MACE on Ti-Al example."""
    lines = [f"digraph mlips_benchmark_example {{\n{GRAPH_ATTRS}"]
    lines.append('  label="Benchmark Module — Example: MACE on Ti-Al";')
    lines.append('  labelloc=t; fontsize=12;')

    lines.append(_instance_node("study", "mlips:study-smith2025\\n(BenchmarkStudy)\\n«Smith et al. (2025)»"))
    lines.append(_instance_node("result", "mlips:result-mace-tial\\n(BenchmarkResult)"))
    lines.append(_instance_node("algo", "mlips:mace-algorithm\\n(MLIPAlgorithm)\\n«MACE»"))
    lines.append(_instance_node("ds", "mlips:tial-dataset-2024\\n(TrainingDataset)"))
    lines.append(_instance_node("mat", "mlips:mat-tial\\n(MaterialSystem)\\n«Ti-Al»"))
    lines.append(_instance_node("metric_e", "mlips:metric-energy-rmse\\n(AccuracyMetric)"))
    lines.append(_instance_node("metric_f", "mlips:metric-force-mae\\n(AccuracyMetric)"))
    lines.append(_instance_node("mt_rmse", "mlips:RMSE\\n(MetricType)"))
    lines.append(_instance_node("mt_mae", "mlips:MAE\\n(MetricType)"))
    lines.append(_instance_node("mp_energy", "mlips:EnergyProperty\\n(MetricProperty)"))
    lines.append(_instance_node("mp_force", "mlips:ForceProperty\\n(MetricProperty)"))
    lines.append(_instance_node("article", "mlips:article-smith2025\\n(ScholarlyArticle)"))
    lines.append(_instance_node("setting_c", "mlips:setting-cutoff\\n(HyperparameterSetting)"))

    lines.append(_literal_node("l_val_e", '"1.2"^^xsd:double'))
    lines.append(_literal_node("l_val_f", '"42.0"^^xsd:double'))
    lines.append(_literal_node("l_cutoff", '"5.0"^^xsd:double'))

    lines.append(_edge("study", "result", "hasResult"))
    lines.append(_edge("result", "algo", "usesAlgorithm"))
    lines.append(_edge("result", "ds", "usesTrainingData"))
    lines.append(_edge("result", "mat", "targetMaterial"))
    lines.append(_edge("result", "metric_e", "hasAccuracyMetric"))
    lines.append(_edge("result", "metric_f", "hasAccuracyMetric"))
    lines.append(_edge("result", "setting_c", "hasHyperparameterSetting"))
    lines.append(_edge("result", "article", "reportedIn"))
    lines.append(_edge("metric_e", "mt_rmse", "metricType"))
    lines.append(_edge("metric_e", "mp_energy", "metricProperty"))
    lines.append(_edge("metric_e", "l_val_e", "metricValue"))
    lines.append(_edge("metric_f", "mt_mae", "metricType"))
    lines.append(_edge("metric_f", "mp_force", "metricProperty"))
    lines.append(_edge("metric_f", "l_val_f", "metricValue"))
    lines.append(_edge("setting_c", "l_cutoff", "cutoffRadius"))

    lines.append("}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Convert MLIPs ontology to Graphviz DOT files."
    )
    parser.add_argument(
        "--ontology",
        default=str(Path(__file__).parent / ".." / "ontology" / "mlips.ttl"),
        help="Path to the ontology Turtle file",
    )
    parser.add_argument(
        "--outdir",
        default=str(Path(__file__).parent / ".." / "figures"),
        help="Output directory for DOT files",
    )
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Overview from ontology
    g = read_ontology(args.ontology)
    overview_dot = generate_overview_dot(g)
    (outdir / "mlips-overview.dot").write_text(overview_dot)
    print(f"Wrote {outdir / 'mlips-overview.dot'}")

    # Instance examples (hand-crafted from paper examples)
    algo_dot = generate_algorithm_instance_dot()
    (outdir / "mlips-algorithm-example.dot").write_text(algo_dot)
    print(f"Wrote {outdir / 'mlips-algorithm-example.dot'}")

    td_dot = generate_training_data_instance_dot()
    (outdir / "mlips-training-data-example.dot").write_text(td_dot)
    print(f"Wrote {outdir / 'mlips-training-data-example.dot'}")

    bm_dot = generate_benchmark_instance_dot()
    (outdir / "mlips-benchmark-example.dot").write_text(bm_dot)
    print(f"Wrote {outdir / 'mlips-benchmark-example.dot'}")


if __name__ == "__main__":
    main()
