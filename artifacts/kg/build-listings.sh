#!/usr/bin/env bash
#
# Build per-question Turtle listings from a paper's canonical .ttl by
# running the CONSTRUCT queries and pretty-printing each output as
# Turtle (using the same prefix declarations as the source file).
#
# Usage:
#   artifacts/kg/build-listings.sh [--computed] <paper-id>
#
# Modes:
#   default (canonical):
#     Source = artifacts/kg/papers/<paper-id>.ttl. Runs Q1-Q11.
#     Output = artifacts/kg/listings/<paper-id>/qNN-*.ttl.
#   --computed:
#     Source = dist/artifacts/kg/papers/<paper-id>-computed.ttl
#     (run `make compute` first). Runs Q1-Q13.
#     Output = artifacts/kg/listings-computed/<paper-id>/qNN-*.ttl.
#     The Q1-Q11 outputs in this mode include computed rdfs:label and
#     inverse-role triples wherever they apply (e.g. Q8's HS triples
#     gain a label, Q9's TrainedModel gains isProducedBy/isEvaluatedIn).

set -euo pipefail

# Make oxigraph and other cargo-installed binaries available even when
# the script is invoked without sourcing ~/.cargo/env.
if [ -d "$HOME/.cargo/bin" ]; then
  case ":$PATH:" in
    *":$HOME/.cargo/bin:"*) ;;
    *) export PATH="$HOME/.cargo/bin:$PATH" ;;
  esac
fi

MODE="canonical"
PAPER_ID=""
while [ $# -gt 0 ]; do
  case "$1" in
    --computed) MODE="computed"; shift ;;
    --*) echo "ERROR: unknown flag: $1" >&2; exit 2 ;;
    *) if [ -z "$PAPER_ID" ]; then PAPER_ID="$1"; fi; shift ;;
  esac
done

if [ -z "$PAPER_ID" ]; then
  echo "Usage: $0 [--computed] <paper-id>" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
QUERY_DIR="$SCRIPT_DIR/queries"

if [ "$MODE" = "computed" ]; then
  PAPER_TTL="$REPO_ROOT/dist/artifacts/kg/papers/${PAPER_ID}-computed.ttl"
  OUT_DIR="$SCRIPT_DIR/listings-computed/${PAPER_ID}"
  QUERY_GLOB="q*.rq"
else
  PAPER_TTL="$SCRIPT_DIR/papers/${PAPER_ID}.ttl"
  OUT_DIR="$SCRIPT_DIR/listings/${PAPER_ID}"
  # Skip Q12/Q13 in canonical mode (they are computed-mode partitions).
  QUERY_GLOB="q0?-*.rq q1[01]-*.rq"
fi

if [ ! -f "$PAPER_TTL" ]; then
  echo "ERROR: not found: $PAPER_TTL" >&2
  if [ "$MODE" = "computed" ]; then
    echo "       (run 'make compute' first)" >&2
  fi
  exit 2
fi

mkdir -p "$OUT_DIR"

# Header lines from the source file: keep @prefix declarations.
PREFIX_BLOCK=$(grep '^@prefix' "$PAPER_TTL" || true)

# Collect query files matching QUERY_GLOB, ordered.
QUERY_FILES=()
for pattern in $QUERY_GLOB; do
  for q in "$QUERY_DIR"/$pattern; do
    [ -f "$q" ] && QUERY_FILES+=("$q")
  done
done

for q in "${QUERY_FILES[@]}"; do
  qname=$(basename "$q" .rq)
  out_ttl="$OUT_DIR/${qname}.ttl"

  # Run the query, strip status lines, get N-triples.
  nt=$(sparql "$q" --graph "$PAPER_TTL" 2>/dev/null \
        | grep -E '^[[:space:]]*(<|_:|").*\.[[:space:]]*$' || true)

  if [ -z "$nt" ]; then
    # No triples for this question: write a single-comment file so the
    # subsection's CONSTRUCT placeholder still has something to include.
    {
      echo "# Q${qname#q}: no triples (paper does not report this)."
    } > "$out_ttl"
    continue
  fi

  # Convert N-triples back to abbreviated Turtle. Trick: feed rapper a
  # Turtle document that combines the source's @prefix declarations with
  # the N-triples body (Turtle accepts full IRI triples too). Rapper then
  # re-emits using the short prefix forms.
  {
    echo "$PREFIX_BLOCK"
    echo
    echo "$nt"
  } | rapper -q -i turtle -o turtle - 'http://example.org/' 2>/dev/null \
    | sed '/^[[:space:]]*$/d' \
    > "$out_ttl"
done

echo "Wrote $(ls "$OUT_DIR" | wc -l) listing files to $OUT_DIR"
