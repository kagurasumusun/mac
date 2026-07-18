#!/usr/bin/env python3
"""Dump facet name -> kCRThemeIdentifierName (u16) mapping from CAR files.

Diagnostic for the open facet-identifier question: the u16 identifier CoreUI
assigns per facet is not yet reproduced. This tool prints the mapping so two
compilations can be compared (determinism / sensitivity probes).

Usage: dump_facet_hashes.py CAR [CAR ...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from actool_linux.carinfo import inspect  # noqa: E402


def main() -> int:
    out = {}
    for arg in sys.argv[1:]:
        info = inspect(Path(arg))
        mapping = {}
        for f in info["facets"]:
            ident = f["attributes"].get("kCRThemeIdentifierName")
            if ident is not None:
                mapping[f["name"]] = ident
        out[arg] = mapping
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
