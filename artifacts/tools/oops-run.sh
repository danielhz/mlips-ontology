#!/usr/bin/env bash
#
# Run OOPS! (OntOlogy Pitfall Scanner) locally on artifacts/ontology/mlips.owl.
#
# On first run, this script downloads Apache Maven and clones the OOPS!
# source into ~/.cache/mlips-oops/, builds the JAR, and runs it. No
# sudo required; everything lives in the user's cache directory.
#
# The OOPS! 0.3.0-SNAPSHOT CLI from github.com/oeg-upm/OOPS implements
# a subset of the published pitfall catalogue (currently P02-P08, plus
# a handful of others). The full ~40-pitfall catalogue is only
# available via the public web UI at https://oops.linkeddata.es/.
# This script captures whatever the open-source CLI emits.
#
# Output: /tmp/oops-report.txt (full log) and dist/oops-summary.tsv
# (one TSV row per pitfall: pitfall_id, count).
#
# Usage:
#   ./artifacts/tools/oops-run.sh [path-to-ontology-file]

set -Eeuo pipefail

CACHE_DIR="$HOME/.cache/mlips-oops"
MVN_VERSION="3.9.15"
MVN_HOME="$CACHE_DIR/apache-maven-$MVN_VERSION"
MVN_URL="https://dlcdn.apache.org/maven/maven-3/$MVN_VERSION/binaries/apache-maven-$MVN_VERSION-bin.tar.gz"
OOPS_SRC="$CACHE_DIR/oops"
OOPS_REPO="https://github.com/oeg-upm/OOPS.git"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATASET_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ONTOLOGY="${1:-$DATASET_ROOT/artifacts/ontology/mlips.owl}"
DIST_DIR="$DATASET_ROOT/dist"
SUMMARY_TSV="$DIST_DIR/oops-summary.tsv"
REPORT_LOG="$DIST_DIR/oops-report.txt"

mkdir -p "$CACHE_DIR" "$DIST_DIR"

# 1. Bootstrap Maven if not already present.
if [ ! -x "$MVN_HOME/bin/mvn" ]; then
  echo "==> Downloading Apache Maven $MVN_VERSION to $CACHE_DIR ..."
  curl -fsL "$MVN_URL" -o "$CACHE_DIR/maven.tar.gz"
  tar -xzf "$CACHE_DIR/maven.tar.gz" -C "$CACHE_DIR"
  rm -f "$CACHE_DIR/maven.tar.gz"
fi

# 2. Clone OOPS! source if not already present.
if [ ! -d "$OOPS_SRC/.git" ]; then
  echo "==> Cloning OOPS! source into $OOPS_SRC ..."
  git clone --depth=1 "$OOPS_REPO" "$OOPS_SRC"
fi

# 3. Build (only if target/ doesn't exist).
if [ ! -d "$OOPS_SRC/target/classes" ]; then
  echo "==> Building OOPS! (skipping tests) ..."
  ( cd "$OOPS_SRC" && "$MVN_HOME/bin/mvn" -q -DskipTests package )
fi

# 4. Run.
echo "==> Running OOPS! on $ONTOLOGY ..."
( cd "$OOPS_SRC" && \
    "$MVN_HOME/bin/mvn" -q exec:java \
      -Dexec.args="--input-file $ONTOLOGY" \
  ) > "$REPORT_LOG" 2>&1 || true   # non-zero on internal OOPS! bugs

# 5. Summarise. Each "Checking CXX ..." line is followed (eventually)
#    by a "Pitfall Ids triggered: N" line; if the checker errored,
#    "ERROR Linter" appears between them.
echo -e "pitfall\tcount\tstatus" > "$SUMMARY_TSV"
awk '
  /Checking [CP][0-9]+ \.\.\./ {
    match($0, /[CP][0-9]+/);
    current = substr($0, RSTART, RLENGTH);
    errored = 0;
    next
  }
  /ERROR Linter/                         { errored = 1 }
  /Pitfall Ids triggered:/ {
    n = $NF;
    status = (errored ? "errored-then-counted" : "ok");
    printf "%s\t%s\t%s\n", current, n, status;
    current = ""; errored = 0
  }
  /Checking [CP][0-9]+ done/ && current != "" {
    if (errored) { printf "%s\t-\terrored\n", current; current = "" }
  }
' "$REPORT_LOG" >> "$SUMMARY_TSV"

echo
echo "==> Summary (also at $SUMMARY_TSV):"
column -t -s $'\t' "$SUMMARY_TSV"
echo
echo "==> Full log at $REPORT_LOG"
