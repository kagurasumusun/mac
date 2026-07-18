#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from collections import Counter

SUFFIXES = ['.brandassets', '.complicationset', '.imagestack', '.imagestacklayer']


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', action='append', default=[])
    ap.add_argument('--limit', type=int, default=400)
    ns = ap.parse_args()
    roots = [Path(p) for p in ns.root] or [Path('/Applications'), Path('/System/Library'), Path('/Library'), Path('/Users/runner')]
    rows = []
    counts = Counter()
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob('*'):
            if not path.is_dir():
                continue
            suffix = path.suffix.lower()
            if suffix in SUFFIXES:
                counts[suffix] += 1
                if len(rows) < ns.limit:
                    rows.append({'path': str(path), 'suffix': suffix})
    print(json.dumps({'roots':[str(r) for r in roots], 'counts': dict(counts), 'rows': rows}, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
