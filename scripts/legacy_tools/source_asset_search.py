#!/usr/bin/env python3
"""Search Xcode installations for source asset-catalog directories.

This is used to find publicly observable source fixtures such as .brandassets,
.complicationset, .imagestack, and ordinary .xcassets directories that may help
reproduce Apple aggregate output.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from collections import Counter

SUFFIXES = (
    '.xcassets',
    '.brandassets',
    '.complicationset',
    '.imagestack',
    '.imagestacklayer',
    '.solidimagestack',
    '.solidimagestacklayer',
    '.appiconset',
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', action='append', default=[])
    ap.add_argument('--limit', type=int, default=300)
    ns = ap.parse_args()
    roots = [Path(p) for p in ns.root] or list(Path('/Applications').glob('Xcode*.app'))
    rows = []
    counts = Counter()
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob('*'):
            if not path.is_dir():
                continue
            suffix = path.suffix.lower()
            if suffix not in SUFFIXES:
                continue
            counts[suffix] += 1
            if len(rows) < ns.limit:
                rows.append({'path': str(path), 'suffix': suffix})
    print(json.dumps({'roots': [str(p) for p in roots], 'counts': dict(counts), 'sample': rows}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
