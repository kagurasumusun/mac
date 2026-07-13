#!/usr/bin/env python3
"""Search Xcode/template resource text files for aggregate-related terms."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from collections import Counter

TERMS = [
    'top-shelf-image',
    'top-shelf-image-wide',
    'primary-app-icon',
    'brandassets',
    'imagestack',
    'complicationset',
    'graphicCircular',
    'notificationCenter',
    'companionSettings',
    'appLauncher',
    'quickLook',
    'longLook',
    'parallax',
    'stackData',
    'renderingProperties',
]
TEXT_SUFFIXES = {'.json','.plist','.strings','.template','.txt','.md','.swift','.m','.h','.pbxproj'}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', action='append', default=[])
    ap.add_argument('--limit', type=int, default=200)
    ns = ap.parse_args()
    roots = [Path(p) for p in ns.root] or list(Path('/Applications').glob('Xcode*.app'))
    rows = []
    counts = Counter()
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob('*'):
            if len(rows) >= ns.limit:
                break
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            try:
                text = path.read_text(errors='ignore')
            except Exception:
                continue
            hits = [term for term in TERMS if term in text]
            if hits:
                rows.append({'path': str(path), 'hits': hits})
                for hit in hits:
                    counts[hit] += 1
    print(json.dumps({'roots': [str(p) for p in roots], 'counts': dict(counts), 'rows': rows}, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
