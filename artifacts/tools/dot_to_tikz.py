#!/usr/bin/env python3
"""Convert Graphviz DOT files to TikZ via Graphviz JSON layout.

Pipeline:  DOT  →  dot -Tjson  →  parse positions  →  emit TikZ

The TikZ output uses coordinates computed by Graphviz, so the initial
placement is good.  The output is a standalone .tex file that can be
\\input{} from the paper or edited with TikZiT or similar tools.

Usage:
    python dot_to_tikz.py [--indir DIR] [--outdir DIR]

Defaults:
    --indir   ../figures/   (reads *.dot)
    --outdir  ../figures/   (writes *.tex)
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


# ── Graphviz JSON → parsed structures ────────────────────────────────────────

def dot_to_json(dot_path):
    """Run dot -Tjson on a DOT file and return parsed JSON."""
    result = subprocess.run(
        ["dot", "-Tjson", str(dot_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"dot failed on {dot_path}: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


# ── Coordinate helpers ───────────────────────────────────────────────────────

# Graphviz uses points (1/72 inch); we convert to cm for TikZ.
PT_TO_CM = 2.54 / 72.0


def gv_pos(pos_str):
    """Parse a Graphviz position string 'x,y' → (x_cm, y_cm)."""
    x, y = pos_str.split(",")
    return float(x) * PT_TO_CM, float(y) * PT_TO_CM


def gv_bb(bb_str):
    """Parse bounding box 'x0,y0,x1,y1' → (x0,y0,x1,y1) in cm."""
    parts = bb_str.split(",")
    return tuple(float(p) * PT_TO_CM for p in parts)


def escape_tex(s):
    """Escape special LaTeX characters in a string."""
    s = s.replace("\\", r"\textbackslash{}")
    s = s.replace("_", r"\_")
    s = s.replace("&", r"\&")
    s = s.replace("%", r"\%")
    s = s.replace("#", r"\#")
    s = s.replace("{", r"\{")
    s = s.replace("}", r"\}")
    s = s.replace("~", r"\textasciitilde{}")
    s = s.replace("^", r"\textasciicircum{}")
    # Undo double-escaping of \textbackslash
    s = s.replace(r"\_ontology", r"\_ontology")
    return s


def clean_label(label, node_name=""):
    """Clean a Graphviz label: handle \\n, \\N, guillemets, escape for TeX."""
    if not label:
        return escape_tex(node_name) if node_name else ""
    # \N is Graphviz placeholder for node name
    label = label.replace("\\N", node_name)
    # Graphviz uses literal \n for line breaks
    parts = label.split("\\n")
    cleaned = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        cleaned.append(escape_tex(p))
    return r" \\ ".join(cleaned)


# ── Module / cluster color mapping ───────────────────────────────────────────

CLUSTER_FILL = {
    "cluster_algorithm": "algofill",
    "cluster_training": "trainfill",
    "cluster_benchmark": "benchfill",
    "cluster_top_row": None,  # invisible wrapper
}

CLUSTER_LABEL = {
    "cluster_algorithm": "Algorithm Module",
    "cluster_training": "Training Data Module",
    "cluster_benchmark": "Benchmark Module",
}


# ── Style detection ──────────────────────────────────────────────────────────

def node_style(obj):
    """Return a TikZ style name based on Graphviz node attributes."""
    fill = obj.get("fillcolor", "")
    shape = obj.get("shape", "box")
    style_str = obj.get("style", "")
    if "dashed" in style_str:
        return "extclass"
    if fill == "#fff4cc":
        return "instance"
    if fill == "#ddeeff":
        return "class"
    if shape == "plaintext":
        return "literal"
    return "class"


def edge_style(obj):
    """Return a TikZ style string based on Graphviz edge attributes."""
    style_str = obj.get("style", "")
    if "invis" in style_str:
        return None  # skip invisible edges
    if "dashed" in style_str:
        return "crossedge"
    return "edge"


# ── TikZ generation ─────────────────────────────────────────────────────────

def generate_tikz(gv_json, figure_name="figure"):
    """Convert parsed Graphviz JSON to a TikZ string."""

    lines = []
    lines.append(r"% Auto-generated from Graphviz layout — edit freely")
    lines.append(r"% Regenerate initial layout: python dot_to_tikz.py")
    lines.append(r"\begin{tikzpicture}[")
    lines.append(r"    x=1cm, y=1cm,")
    lines.append(r"    every node/.style={font=\small},")
    lines.append(r"    class/.style={draw, rounded corners=2pt, fill=classfill,")
    lines.append(r"        font=\small, inner sep=3pt, align=center},")
    lines.append(r"    instance/.style={draw, fill=instancefill,")
    lines.append(r"        font=\small, inner sep=3pt, align=center},")
    lines.append(r"    literal/.style={font=\small\color{gray}, inner sep=2pt, align=center},")
    lines.append(r"    extclass/.style={draw, dashed, rounded corners=2pt, fill=extfill,")
    lines.append(r"        font=\small, inner sep=3pt, align=center},")
    lines.append(r"    edge/.style={->, >=stealth, thick},")
    lines.append(r"    crossedge/.style={->, >=stealth, thick, dashed},")
    lines.append(r"    edgelabel/.style={font=\scriptsize, fill=white, inner sep=1pt},")
    lines.append(r"]")
    lines.append("")

    # Color definitions (will be in the preamble)
    lines.append(r"% Color definitions (copy to preamble if not already defined):")
    lines.append(r"% \definecolor{classfill}{HTML}{DDEEFF}")
    lines.append(r"% \definecolor{instancefill}{HTML}{FFF4CC}")
    lines.append(r"% \definecolor{extfill}{HTML}{E8E8E8}")
    lines.append(r"% \definecolor{algofill}{HTML}{C6DBEF}")
    lines.append(r"% \definecolor{trainfill}{HTML}{C7E9C0}")
    lines.append(r"% \definecolor{benchfill}{HTML}{FDD0A2}")
    lines.append("")

    # Compute global Y offset: Graphviz Y increases upward, TikZ too,
    # but we want top of figure at y=0 going down for readability.
    # Find max Y from bounding box.
    bb = gv_json.get("bb", "0,0,100,100")
    bb_x0, bb_y0, bb_x1, bb_y1 = gv_bb(bb)
    max_y = bb_y1

    def flip_y(y_cm):
        return max_y - y_cm

    # ── Clusters (as background rectangles) ──
    subgraphs = gv_json.get("objects", [])
    # Collect subgraph info for background rectangles
    for sg in subgraphs:
        sg_name = sg.get("name", "")
        if not sg_name.startswith("cluster_"):
            continue
        sg_bb = sg.get("bb")
        if not sg_bb:
            continue
        fill = CLUSTER_FILL.get(sg_name)
        if fill is None:
            continue
        label = CLUSTER_LABEL.get(sg_name, "")
        x0, y0, x1, y1 = gv_bb(sg_bb)
        # flip Y
        ty0 = flip_y(y1)  # top-left y
        ty1 = flip_y(y0)  # bottom-right y
        lines.append(f"  % {sg_name}")
        lines.append(
            f"  \\fill[{fill}, rounded corners=4pt] "
            f"({x0:.2f},{ty0:.2f}) rectangle ({x1:.2f},{ty1:.2f});"
        )
        if label:
            lines.append(
                f"  \\node[anchor=north west, font=\\small\\bfseries] "
                f"at ({x0 + 0.1:.2f},{ty0 + 0.0:.2f}) {{{label}}};"
            )
        lines.append("")

    # ── Nodes ──
    lines.append("  % Nodes")
    node_ids = {}  # gv_id or name → tikz_id

    # Build lookup: _gvid → object for all top-level objects
    obj_by_id = {}
    for obj in subgraphs:
        gvid = obj.get("_gvid")
        if gvid is not None:
            obj_by_id[gvid] = obj

    # Collect node IDs from subgraphs (they reference _gvid integers)
    node_gvids = set()

    def collect_node_ids(obj_list):
        for obj in obj_list:
            if isinstance(obj, int):
                node_gvids.add(obj)
                continue
            if not isinstance(obj, dict):
                continue
            for nid in obj.get("nodes", []):
                if isinstance(nid, int):
                    node_gvids.add(nid)
            for sg in obj.get("subgraphs", []):
                if isinstance(sg, int) and sg in obj_by_id:
                    collect_node_ids([obj_by_id[sg]])
                elif isinstance(sg, dict):
                    collect_node_ids([sg])

    collect_node_ids(subgraphs)

    # Resolve node objects: nodes are top-level objects with "pos"
    all_nodes = []
    for obj in subgraphs:
        gvid = obj.get("_gvid")
        if gvid is not None and "pos" in obj:
            name = obj.get("name", "")
            if name and not name.startswith("cluster_"):
                all_nodes.append(obj)

    for node in all_nodes:
        name = node.get("name", "")
        if not name or name.startswith("cluster_"):
            continue
        pos = node.get("pos")
        if not pos:
            continue
        x, y = gv_pos(pos)
        ty = flip_y(y)
        label = clean_label(node.get("label", ""), node_name=name)
        style = node_style(node)
        tikz_id = name.replace("-", "_").replace(".", "_")
        node_ids[name] = tikz_id
        # Also map by _gvid for edge lookups
        if "_gvid" in node:
            node_ids[node["_gvid"]] = tikz_id

        lines.append(
            f"  \\node[{style}] ({tikz_id}) at ({x:.2f},{ty:.2f}) {{{label}}};"
        )

    lines.append("")

    # ── Edges ──
    lines.append("  % Edges")
    edges = gv_json.get("edges", [])
    for e in edges:
        tail_id = e.get("tail")
        head_id = e.get("head")
        tail_name = node_ids.get(tail_id, node_ids.get(str(tail_id), f"n{tail_id}"))
        head_name = node_ids.get(head_id, node_ids.get(str(head_id), f"n{head_id}"))

        estyle = edge_style(e)
        if estyle is None:
            continue  # skip invisible

        label = clean_label(e.get("label", ""))
        label_str = ""
        if label:
            label_str = f" node[edgelabel, pos=0.5] {{{label}}}"

        lines.append(
            f"  \\draw[{estyle}] ({tail_name}) --{label_str} ({head_name});"
        )

    lines.append("")
    lines.append(r"\end{tikzpicture}")
    return "\n".join(lines)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Convert Graphviz DOT files to TikZ via JSON layout."
    )
    parser.add_argument(
        "--indir",
        default=str(Path(__file__).parent / ".." / "figures"),
        help="Directory containing .dot files",
    )
    parser.add_argument(
        "--outdir",
        default=str(Path(__file__).parent / ".." / "figures"),
        help="Output directory for .tex files",
    )
    args = parser.parse_args()

    indir = Path(args.indir)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    dot_files = sorted(indir.glob("*.dot"))
    if not dot_files:
        print(f"No .dot files found in {indir}", file=sys.stderr)
        sys.exit(1)

    for dot_path in dot_files:
        print(f"Processing {dot_path.name}...")
        gv_json = dot_to_json(dot_path)
        tikz = generate_tikz(gv_json, dot_path.stem)
        out_path = outdir / (dot_path.stem + ".tex")
        out_path.write_text(tikz)
        print(f"  -> {out_path.name}")

    print(f"Done. TikZ files in: {outdir}")


if __name__ == "__main__":
    main()
