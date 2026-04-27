#!/usr/bin/env bash
#
# Build per-question Turtle listings from a paper's canonical .ttl by
# running the 11 CONSTRUCT queries and pretty-printing each output as
# Turtle (using the same prefix declarations as the source file).
#
# Usage:  artifacts/kg/build-listings.sh <paper-id>
# Output: writes artifacts/kg/listings/<paper-id>/qNN-*.ttl, one file
#         per query, suitable for inclusion as lstlisting fragments.

set -euo pipefail

# Make oxigraph and other cargo-installed binaries available even when
# the script is invoked without sourcing ~/.cargo/env.
if [ -d "$HOME/.cargo/bin" ]; then
  case ":$PATH:" in
    *":$HOME/.cargo/bin:"*) ;;
    *) export PATH="$HOME/.cargo/bin:$PATH" ;;
  esac
fi

if [ $# -ne 1 ]; then
  echo "Usage: $0 <paper-id>" >&2
  exit 2
fi

PAPER_ID="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PAPER_TTL="$SCRIPT_DIR/papers/${PAPER_ID}.ttl"
QUERY_DIR="$SCRIPT_DIR/queries"
OUT_DIR="$SCRIPT_DIR/listings/${PAPER_ID}"

if [ ! -f "$PAPER_TTL" ]; then
  echo "ERROR: not found: $PAPER_TTL" >&2
  exit 2
fi

mkdir -p "$OUT_DIR"

# Header lines from the canonical file: keep @prefix declarations.
PREFIX_BLOCK=$(grep '^@prefix' "$PAPER_TTL" || true)

for q in "$QUERY_DIR"/q*.rq; do
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
