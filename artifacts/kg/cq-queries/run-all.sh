#!/usr/bin/env bash
#
# Execute every CQ query against the merged corpus and print a
# results table (rows + wall-clock time per query). Used to
# regenerate the §8.1 numbers in the paper after a schema or KG
# change.
#
# Output is a small Markdown table on stdout; the run-time of each
# query and its row count are also captured to /tmp/cq-results.tsv
# for downstream consumption.

set -euo pipefail

if [ -d "$HOME/.cargo/bin" ]; then
  case ":$PATH:" in
    *":$HOME/.cargo/bin:"*) ;;
    *) export PATH="$HOME/.cargo/bin:$PATH" ;;
  esac
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATASET_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

ONTOLOGY="$DATASET_ROOT/artifacts/ontology/mlips.ttl"
VOCAB="$DATASET_ROOT/artifacts/kg/mlips-vocab.ttl"
PAPERS=("$DATASET_ROOT"/artifacts/kg/papers/*.ttl)

CORPUS=$(mktemp /tmp/mlips-corpus.XXXXXX.ttl)
trap 'rm -f "$CORPUS" "$CORPUS".nt' EXIT

# Build a deduplicated merged corpus (ontology + vocab + 20 papers).
for f in "$ONTOLOGY" "$VOCAB" "${PAPERS[@]}"; do
  rapper -q -i turtle -o ntriples "$f" 2>/dev/null
done | sort -u > "$CORPUS".nt
rapper -q -i ntriples -o turtle "$CORPUS".nt > "$CORPUS" 2>/dev/null

n_triples=$(wc -l < "$CORPUS".nt)

printf "%-7s %8s %8s\n" "Query"   "Rows"  "Time(ms)"
printf "%-7s %8s %8s\n" "-------" "-----" "--------"

: > /tmp/cq-results.tsv

for q in "$SCRIPT_DIR"/cq*.rq; do
  name=$(basename "$q" .rq)
  start_ns=$(date +%s%N)
  # sparql writes status banners to stderr (suppressed) and a TSV
  # to stdout: a header line (the SELECT variables, tab-separated)
  # followed by one line per result. Skip the first line and
  # count the rest.
  rows=$(sparql "$q" --graph "$CORPUS" 2>/dev/null | tail -n +2 | wc -l)
  end_ns=$(date +%s%N)
  elapsed_ms=$(( (end_ns - start_ns) / 1000000 ))
  printf "%-7s %8d %8d\n" "$name" "$rows" "$elapsed_ms"
  printf "%s\t%d\t%d\n" "$name" "$rows" "$elapsed_ms" >> /tmp/cq-results.tsv
done

echo
echo "Corpus: $n_triples triples (ontology + vocab + ${#PAPERS[@]} papers)."
echo "Per-query results: /tmp/cq-results.tsv"
