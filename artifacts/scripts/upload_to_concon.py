#!/usr/bin/env python3
"""Incrementally upload the built MLIPs artifacts to a concon server.

This is the D1 loader: it PUTs the dataset's named graphs and the curated
document to a concon instance via the blessed ingest contract
(Graph Store Protocol-style `_graph` PUT + `_doc` PUT), sending only the
units whose bytes changed since the last successful upload TO THAT SERVER.
It uploads already-built artifacts; run `make ontology` (and optionally
`make compute`) first.

CONVENTION-BASED — minimal typing:
  On the concon server itself:
      CONCON_PASSWORD=... ./artifacts/scripts/upload_to_concon.py
  From a laptop, targeting a remote host:
      CONCON_URL=https://kg.informatik.uni-stuttgart.de \\
      CONCON_PASSWORD=... ./artifacts/scripts/upload_to_concon.py

Configuration (only CONCON_PASSWORD is required):
  CONCON_PASSWORD   (required) HTTP Basic password. Never printed.
  CONCON_USER       Basic user. Default "admin".
  CONCON_INGEST_TOKEN  Optional. If CONCON_PASSWORD is unset, used as a
                    write-only Bearer token instead (Basic is the norm).
  CONCON_URL        Optional host/origin, e.g.
                    "https://kg.informatik.uni-stuttgart.de".
                    Default "http://127.0.0.1:3000" (localhost on the
                    server -- no TLS needed there). The dataset path is
                    appended by the script.
  CONCON_DATASET_PATH  Dataset path appended to the origin.
                    Default "/mlips/_ds/mlips" (team mlips, dataset mlips).

Flags: --dry-run (show what would be sent, no PUTs), --force/--all
(ignore the manifest, re-send everything), --dataset-path PATH.

Incremental state: a gitignored manifest at
.concon-upload-state/<host-key>.json maps each unit -> the sha256 last
successfully uploaded to that base URL. A unit's entry is updated only
after its PUT returns 2xx, so a failed upload retries next run.
"""
import argparse
import base64
import glob
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent  # the code/ repo root
GRAPH_NS = "https://w3id.org/mlips/graph/"
DEFAULT_ORIGIN = "http://127.0.0.1:3000"
DEFAULT_DATASET_PATH = "/mlips/_ds/mlips"


def assemble(paths):
    """Concatenate the given (sorted) files into one Turtle body. Repeated
    @prefix lines across documents are valid Turtle, so this is a legal
    single graph body."""
    parts = []
    for p in paths:
        parts.append(Path(p).read_bytes())
    return b"\n".join(parts)


def units():
    """The ordered upload set: (name, kind, graph-or-None, content-bytes,
    content-type). kind is 'graph' or 'doc'. Units whose sources are
    absent are skipped (content is None)."""
    onto = REPO / "artifacts" / "ontology"
    kg = REPO / "artifacts" / "kg"
    papers = sorted(glob.glob(str(kg / "papers" / "*.ttl")))
    labels = sorted(glob.glob(str(REPO / "dist" / "artifacts" / "kg" / "papers" / "*-labels.ttl")))

    def file_bytes(p):
        return Path(p).read_bytes() if Path(p).exists() else None

    TTL = "text/turtle"
    spec = [
        ("schema",   "graph", "schema",   file_bytes(onto / "mlips.ttl"),       TTL),
        ("vocab",    "graph", "vocab",    file_bytes(kg / "mlips-vocab.ttl"),   TTL),
        ("kg",       "graph", "kg",       assemble(papers) if papers else None, TTL),
        # concon >= v0.2.0 owns the `computed` graph (it derives the
        # axiom-expressible triples itself), so the *-computed.ttl
        # materialisations are no longer PUT. The templated labels --
        # not axiom-expressible -- go to the consumer-owned `labels`
        # graph instead (from dist/, `make compute` first).
        ("labels",   "graph", "labels",   assemble(labels) if labels else None, TTL),
        ("cq",       "graph", "cq",       file_bytes(kg / "cq.ttl"),            TTL),
        ("doc",      "doc",   None,       file_bytes(onto / "mlips.source.xhtml"),
         "application/xhtml+xml"),
    ]
    return spec


def host_key(base):
    return "".join(c if c.isalnum() else "_" for c in base).strip("_")


def put(base, kind, graph, body, content_type, auth_header, dry_run):
    if kind == "graph":
        url = f"{base}/_graph?graph={urllib.parse.quote(GRAPH_NS + graph, safe='')}"
    else:
        url = f"{base}/_doc"
    if dry_run:
        return None
    req = urllib.request.Request(url, data=body, method="PUT",
                                 headers={"Content-Type": content_type,
                                          "Authorization": auth_header})
    with urllib.request.urlopen(req) as resp:
        return resp.status


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="show what would be uploaded; make no PUTs")
    ap.add_argument("--force", "--all", dest="force", action="store_true",
                    help="ignore the manifest and re-send every unit")
    ap.add_argument("--dataset-path", default=os.environ.get("CONCON_DATASET_PATH", DEFAULT_DATASET_PATH),
                    help=f"dataset path appended to the origin (default {DEFAULT_DATASET_PATH})")
    args = ap.parse_args()

    # --- Auth (only the password is required) ---
    password = os.environ.get("CONCON_PASSWORD")
    token = os.environ.get("CONCON_INGEST_TOKEN")
    user = os.environ.get("CONCON_USER", "admin")
    if password:
        auth_header = "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()
    elif token:
        auth_header = "Bearer " + token
        print("auth: using CONCON_INGEST_TOKEN (Bearer)")
    else:
        sys.exit("ERROR: set CONCON_PASSWORD (HTTP Basic) — or CONCON_INGEST_TOKEN. "
                 "Neither is set.")

    # --- Target base URL (origin + dataset path) ---
    origin = os.environ.get("CONCON_URL", DEFAULT_ORIGIN).rstrip("/")
    base = origin + "/" + args.dataset_path.strip("/")
    host = urllib.parse.urlparse(origin).hostname or ""
    if not origin.startswith("https://") and host not in ("127.0.0.1", "localhost", "::1"):
        print(f"WARNING: {origin} is not https — Basic credentials would be sent in cleartext.",
              file=sys.stderr)

    # --- Manifest (per base URL) ---
    state_dir = REPO / ".concon-upload-state"
    state_file = state_dir / f"{host_key(base)}.json"
    manifest = {}
    if state_file.exists() and not args.force:
        manifest = json.loads(state_file.read_text()).get("units", {})

    print(f"Target: {base}" + ("   [DRY RUN]" if args.dry_run else ""))
    sent = skipped = 0
    for name, kind, graph, body, ctype in units():
        target = f"graph/{graph}" if kind == "graph" else "_doc"
        if body is None:
            print(f"  - {name:9} skip (no source artifact)")
            continue
        digest = hashlib.sha256(body).hexdigest()
        if not args.force and manifest.get(name) == digest:
            print(f"  = {name:9} unchanged ({target})")
            skipped += 1
            continue
        if args.dry_run:
            print(f"  ~ {name:9} WOULD PUT -> {target} ({len(body)} bytes, sha256 {digest[:12]})")
            sent += 1
            continue
        try:
            status = put(base, kind, graph, body, ctype, auth_header, dry_run=False)
        except urllib.error.HTTPError as e:
            sys.exit(f"  ! {name}: PUT {target} failed — HTTP {e.code} {e.reason}")
        except urllib.error.URLError as e:
            sys.exit(f"  ! {name}: PUT {target} failed — {e.reason}")
        if not (200 <= (status or 0) < 300):
            sys.exit(f"  ! {name}: PUT {target} returned HTTP {status}")
        print(f"  + {name:9} PUT -> {target} (HTTP {status}, {len(body)} bytes)")
        manifest[name] = digest          # update only on 2xx
        sent += 1

    if not args.dry_run:
        state_dir.mkdir(exist_ok=True)
        state_file.write_text(json.dumps({"base": base, "units": manifest}, indent=2) + "\n")

    print(f"Done: {sent} {'would be ' if args.dry_run else ''}sent, {skipped} unchanged."
          + ("" if args.dry_run else f"  Manifest: {state_file.relative_to(REPO)}"))


if __name__ == "__main__":
    main()
