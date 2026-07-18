#!/usr/bin/env python3
"""Scan TemplateInfo.plist files for asset-generation and Top Shelf clues."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

TERMS = [
    'solidimagestack',
    'imagestack',
    'com.apple.tv-top-shelf',
    'top shelf',
    'AssetGeneration',
    'brandassets',
    'complication',
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', action='append', default=[])
    ns = ap.parse_args()
    roots = [Path(p) for p in ns.root] or list(Path('/Applications').glob('Xcode*.app'))
    rows = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob('TemplateInfo.plist'):
            try:
                lines = path.read_text(errors='ignore').splitlines()
            except Exception:
                continue
            matches = []
            for idx, line in enumerate(lines, 1):
                if any(term in line for term in TERMS):
                    matches.append({'line': idx, 'text': line.strip()[:300]})
            if matches:
                rows.append({'path': str(path), 'matches': matches[:40]})
    print(json.dumps({'roots': [str(r) for r in roots], 'rows': rows}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
