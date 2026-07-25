#!/usr/bin/env python3
"""Package the DaRUS deposit zip for the MLIPs ontology (make darus).

Produces ONE upload zip whose top level contains (DaRUS extracts a
zip into a flat object tree, non-recursively):

  - mlips-onto-v<V>.bundle -- `git bundle` of `main` plus the `v<V>`
    tag: code + data + full history in a single file object. Only
    those two refs are bundled (never `--all`; the orphan
    agent-messages branch stays out of the deposit).
  - README.md, LICENSE -- top-level copies (DaRUS previews text).
  - CITATION.cff -- generated deposit artifact, NOT the committed
    file: it additionally carries the release commit SHA (which
    cannot live inside the bundle it identifies) and placeholder
    related identifiers for the arXiv id and the Software Heritage
    SWHID, which Daniel fills in the DaRUS metadata once minted.

The version is read from the committed CITATION.cff. The release tag
v<V> must exist and point at HEAD (--allow-untagged relaxes this for
dry runs; the bundle then contains `main` only). Output is
reproducible: zip entry timestamps are pinned to the release commit's
own timestamp and the bundle is packed single-threaded, so a clean
checkout of the same commit yields a byte-identical zip.

Usage:  package_for_darus.py [--allow-untagged] [--allow-dirty]
                             [--output-dir DIR]
"""

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# Deposit manifest: repo files copied verbatim to the zip top level.
PLAIN_FILES = ["README.md", "LICENSE"]

ARXIV_PLACEHOLDER = "arXiv:XXXX.XXXXX"
SWHID_PLACEHOLDER = "swh:1:rev:0000000000000000000000000000000000000000"


def run(*args, **kw):
    return subprocess.run(
        args, cwd=REPO, check=True, capture_output=True, text=True, **kw
    ).stdout.strip()


def read_version():
    text = (REPO / "CITATION.cff").read_text(encoding="utf-8")
    m = re.search(r'^version:\s*"?([0-9][^"\s]*)"?\s*$', text, re.M)
    if not m:
        sys.exit("ERROR: no version: field in CITATION.cff")
    return m.group(1)


def deposit_citation_cff(sha):
    """The committed CITATION.cff plus the release commit SHA and
    placeholder related identifiers (arXiv, SWHID)."""
    lines = (REPO / "CITATION.cff").read_text(encoding="utf-8").splitlines(True)
    if any(l.startswith("commit:") for l in lines) or any(
        l.startswith("identifiers:") for l in lines
    ):
        sys.exit("ERROR: committed CITATION.cff already has commit:/identifiers:")
    out = []
    for line in lines:
        out.append(line)
        if line.startswith("version:"):
            out.append('commit: "%s"\n' % sha)
        if line.startswith("repository-code:"):
            out.append("identifiers:\n")
            out.append("  - type: other\n")
            out.append('    value: "%s"\n' % ARXIV_PLACEHOLDER)
            out.append(
                "    description: \"PLACEHOLDER -- arXiv identifier of the"
                " accompanying extended paper; fill in once minted.\"\n"
            )
            out.append("  - type: swh\n")
            out.append('    value: "%s"\n' % SWHID_PLACEHOLDER)
            out.append(
                "    description: \"PLACEHOLDER -- Software Heritage SWHID"
                " of the release revision; fill in after Save Code Now.\"\n"
            )
    return "".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow-untagged", action="store_true")
    ap.add_argument("--allow-dirty", action="store_true")
    ap.add_argument("--output-dir", default=str(REPO / "dist" / "darus"))
    args = ap.parse_args()

    version = read_version()
    tag = "v" + version
    sha = run("git", "rev-parse", "HEAD")

    if run("git", "status", "--porcelain") and not args.allow_dirty:
        sys.exit(
            "ERROR: working tree not clean -- the deposit must be"
            " generated from a committed state (--allow-dirty to override)."
        )

    # HEAD (= main in the throwaway clone) is bundled too so that a
    # plain `git clone <bundle>` finds a default branch to check out.
    refs = ["HEAD", "main"]
    tag_sha = None
    try:
        tag_sha = run("git", "rev-parse", "--verify", "refs/tags/" + tag + "^{commit}")
    except subprocess.CalledProcessError:
        pass
    if tag_sha is None:
        if not args.allow_untagged:
            sys.exit(
                "ERROR: tag %s does not exist -- cut it on the release"
                " commit first (--allow-untagged for a dry run)." % tag
            )
    elif tag_sha != sha:
        sys.exit("ERROR: tag %s points at %s, but HEAD is %s." % (tag, tag_sha, sha))
    else:
        refs.append(tag)

    out_dir = Path(args.output_dir)
    stage = out_dir / "stage"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)

    # 1. The git bundle (main + release tag only; never --all).
    #
    # Bundled from a throwaway single-branch bare clone that is
    # force-repacked single-threaded first: pack bytes otherwise
    # depend on the delta layout of the local object store (an
    # incrementally-grown checkout and a fresh clone would produce
    # different -- though content-identical -- bundles). Repacking
    # with --no-reuse-delta (-f) and pack.threads=1 makes the pack,
    # and hence the bundle, deterministic for a given git version.
    bundle = stage / ("mlips-onto-%s.bundle" % tag)
    bundle_src = out_dir / ".bundle-src.git"
    if bundle_src.exists():
        shutil.rmtree(bundle_src)
    subprocess.run(
        ["git", "clone", "--quiet", "--bare", "--no-local",
         "--branch", "main", "--single-branch", str(REPO), str(bundle_src)],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-c", "pack.threads=1", "repack", "-adfq"],
        cwd=bundle_src, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-c", "pack.threads=1", "bundle", "create", str(bundle), *refs],
        cwd=bundle_src, check=True, capture_output=True,
    )
    shutil.rmtree(bundle_src)

    # 2. Plain top-level copies.
    for name in PLAIN_FILES:
        shutil.copyfile(REPO / name, stage / name)

    # 3. The generated deposit CITATION.cff.
    (stage / "CITATION.cff").write_text(deposit_citation_cff(sha), encoding="utf-8")

    # 4. One reproducible zip: fixed entry order, entry timestamps
    #    pinned to the release commit's timestamp.
    commit_ts = int(run("git", "show", "-s", "--format=%ct", "HEAD"))
    date_time = time.gmtime(commit_ts)[:6]
    zip_path = out_dir / ("mlips-onto-%s-darus.zip" % tag)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(stage.iterdir()):
            info = zipfile.ZipInfo(f.name, date_time=date_time)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, f.read_bytes())

    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    print("DaRUS deposit for %s" % tag)
    print("  commit:  %s%s" % (sha, "" if tag_sha else "  (UNTAGGED dry run)"))
    print("  objects:")
    for f in sorted(stage.iterdir()):
        print("    %-28s %8d bytes" % (f.name, f.stat().st_size))
    print("  zip:     %s (%d bytes)" % (zip_path, zip_path.stat().st_size))
    print("  sha256:  %s" % digest)


if __name__ == "__main__":
    main()
