#!/usr/bin/env bash
#
# Round-trip check for the worked-examples extraction protocol.
#
# Usage:  artifacts/kg/check-roundtrip.sh <paper-id>
# Example: artifacts/kg/check-roundtrip.sh kumar2025
#
# For a paper-id, this script:
#   1. Runs all 11 CONSTRUCT queries against artifacts/kg/papers/<paper-id>.ttl.
#   2. Concatenates and canonicalises (N-triples, sorted, deduped) the
#      union of the query outputs.
#   3. Canonicalises the source .ttl file the same way.
#   4. Diffs the two. Exit 0 if identical (round-trip pass), 1 otherwise.
#
# The script is paper-agnostic; the queries are too.

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

if [ ! -f "$PAPER_TTL" ]; then
  echo "ERROR: not found: $PAPER_TTL" >&2
  exit 2
fi

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

# --- Step 1: run each query, collect the constructed triples ---------------
UNION_NT="$WORK_DIR/union.nt"
: > "$UNION_NT"

for q in "$QUERY_DIR"/q*.rq; do
  qname=$(basename "$q" .rq)
  out_nt="$WORK_DIR/${qname}.nt"
  # The custom `sparql` CLI emits N-triples directly, but prefixes the
  # output with status lines (Loading.../Loaded.../Running.../Constructed...).
  # We strip those by keeping only lines that look like N-triples (start
  # with `<`, `_:`, or `"` or end with `.`).
  sparql "$q" --graph "$PAPER_TTL" 2>/dev/null \
    | grep -E '^[[:space:]]*(<|_:|").*\.[[:space:]]*$' \
    > "$out_nt" || true
  cat "$out_nt" >> "$UNION_NT"
done

# --- Unicode normalisation -------------------------------------------------
# rapper's N-triples output escapes non-ASCII characters as \uXXXX, while
# oxigraph emits them as raw UTF-8. Both forms are valid N-triples, but a
# byte-level diff sees them as different. Normalise both sides by decoding
# \uXXXX escapes back to UTF-8 before sorting, so cross-corpus literals
# with umlauts or other non-ASCII characters compare equal.
UNESCAPE_PY='import re, sys
for line in sys.stdin:
    sys.stdout.write(re.sub(r"\\u([0-9A-Fa-f]{4})", lambda m: chr(int(m.group(1), 16)), line))'

# --- Step 2: canonicalise the union (N-triples, sorted, deduped) -----------
UNION_CANON="$WORK_DIR/union.canon"
python3 -c "$UNESCAPE_PY" < "$UNION_NT" | sort -u > "$UNION_CANON"

# --- Step 3: canonicalise the source .ttl ---------------------------------
SOURCE_CANON="$WORK_DIR/source.canon"
rapper -i turtle -o ntriples "$PAPER_TTL" 2>/dev/null \
  | python3 -c "$UNESCAPE_PY" \
  | sort -u > "$SOURCE_CANON"

# --- Step 4: diff ----------------------------------------------------------
echo "Round-trip check for $PAPER_ID"
echo "  Source:    $(wc -l < "$SOURCE_CANON") triples in $PAPER_TTL"
echo "  CONSTRUCT: $(wc -l < "$UNION_CANON") triples after the 11 queries"

if diff -u "$SOURCE_CANON" "$UNION_CANON" > "$WORK_DIR/diff.out"; then
  echo "  Result:    PASS -- the 11 queries reproduce the canonical .ttl"
  exit 0
else
  echo "  Result:    FAIL -- drift between source and queries"
  echo
  echo "Triples in source but missing from query union (- lines):"
  echo "Triples in query union but missing from source (+ lines):"
  echo
  cat "$WORK_DIR/diff.out"
  exit 1
fi
