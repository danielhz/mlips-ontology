#!/usr/bin/env python3
"""Generate codemeta.json at the repo root from CITATION.cff.

CITATION.cff is the single hand-maintained metadata source;
codemeta.json is derived (cffconvert) and must be regenerated whenever
CITATION.cff changes (`make codemeta`, also a dependency of
`make darus`). The conversion is augmented with the related-identifier
placeholders for the arXiv id and the Software Heritage SWHID, matching
the identifiers the DaRUS deposit's generated CITATION.cff carries
(package_for_darus.py); Daniel replaces the placeholders in the DaRUS
metadata once the identifiers are minted.

Output is deterministic (sorted keys, fixed indentation) so the file
only changes when the metadata does.
"""

import json
import sys
from pathlib import Path

try:
    from cffconvert import Citation
except ImportError:
    sys.exit("gen_codemeta.py: cffconvert not importable -- run `make venv` first.")

REPO = Path(__file__).resolve().parents[2]

# Keep in sync with package_for_darus.py.
ARXIV_PLACEHOLDER = "arXiv:XXXX.XXXXX"
SWHID_PLACEHOLDER = "swh:1:rev:0000000000000000000000000000000000000000"


def main():
    cff = (REPO / "CITATION.cff").read_text(encoding="utf-8")
    codemeta = json.loads(Citation(cff).as_codemeta())

    codemeta["identifier"] = [
        {
            "@type": "PropertyValue",
            "propertyID": "arXiv",
            "value": ARXIV_PLACEHOLDER,
            "description": (
                "PLACEHOLDER -- arXiv identifier of the accompanying"
                " extended paper; fill in once minted."
            ),
        },
        {
            "@type": "PropertyValue",
            "propertyID": "swhid",
            "value": SWHID_PLACEHOLDER,
            "description": (
                "PLACEHOLDER -- Software Heritage SWHID of the release"
                " revision; fill in after Save Code Now."
            ),
        },
    ]

    out = REPO / "codemeta.json"
    out.write_text(
        json.dumps(codemeta, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("Wrote %s (version %s)" % (out, codemeta.get("version")))


if __name__ == "__main__":
    main()
