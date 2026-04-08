#!/bin/bash
# Render DOT files to PDF and PNG using Graphviz.
#
# Usage:
#   ./render_figures.sh [--format pdf|png|both] [--outdir DIR]
#
# Prerequisites:
#   - Graphviz (dot command)
#   - Python 3 + rdflib (for ontology_to_dot.py)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FIGURES_DIR="${SCRIPT_DIR}/../figures"
FORMAT="both"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --format) FORMAT="$2"; shift 2 ;;
        --outdir) FIGURES_DIR="$2"; shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

mkdir -p "$FIGURES_DIR"

# Step 1: Generate DOT files from ontology
echo "==> Generating DOT files from ontology..."
python3 "${SCRIPT_DIR}/ontology_to_dot.py" --outdir "$FIGURES_DIR"

# Step 2: Render each DOT file
for dotfile in "$FIGURES_DIR"/*.dot; do
    base="$(basename "$dotfile" .dot)"
    echo "==> Rendering ${base}..."

    if [[ "$FORMAT" == "pdf" || "$FORMAT" == "both" ]]; then
        dot -Tpdf "$dotfile" -o "$FIGURES_DIR/${base}.pdf"
        echo "    -> ${base}.pdf"
    fi

    if [[ "$FORMAT" == "png" || "$FORMAT" == "both" ]]; then
        dot -Tpng -Gdpi=300 "$dotfile" -o "$FIGURES_DIR/${base}.png"
        echo "    -> ${base}.png"
    fi
done

# Step 3: Generate TikZ files from DOT (via Graphviz JSON layout)
echo "==> Generating TikZ files from DOT layouts..."
python3 "${SCRIPT_DIR}/dot_to_tikz.py" --indir "$FIGURES_DIR" --outdir "$FIGURES_DIR"

echo "==> Done. Figures in: $FIGURES_DIR"
