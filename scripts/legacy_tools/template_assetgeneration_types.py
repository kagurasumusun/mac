#!/usr/bin/env python3
"""Extract public AssetGeneration type/name/platform tuples from TemplateInfo.plist files."""
from __future__ import annotations

import argparse
import json
import plistlib
from pathlib import Path
from collections import Counter


def walk(value, callback):
    if isinstance(value, dict):
        callback(value)
        for child in value.values():
            walk(child, callback)
    elif isinstance(value, list):
        for child in value:
            walk(child, callback)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', action='append', default=[])
    ns = ap.parse_args()
    roots = [Path(p) for p in ns.root] or list(Path('/Applications').glob('Xcode*.app'))
    rows = []
    type_counts = Counter()
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob('TemplateInfo.plist'):
            try:
                data = plistlib.loads(path.read_bytes())
            except Exception:
                continue
            found = []
            def cb(node):
                if isinstance(node, dict) and 'AssetGeneration' in node:
                    found.append(node['AssetGeneration'])
            walk(data, cb)
            normalized = []
            for item in found:
                if isinstance(item, dict):
                    items = [item]
                elif isinstance(item, list):
                    items = [x for x in item if isinstance(x, dict)]
                else:
                    items = []
                for entry in items:
                    row = {
                        'type': entry.get('Type'),
                        'name': entry.get('Name'),
                        'platforms': sorted([k for k, v in (entry.get('Platforms') or {}).items() if v]) if isinstance(entry.get('Platforms'), dict) else None,
                        'raw_keys': sorted(entry.keys()),
                    }
                    normalized.append(row)
                    if row['type']:
                        type_counts[str(row['type'])] += 1
            if normalized:
                rows.append({'path': str(path), 'asset_generation': normalized})
    print(json.dumps({'roots':[str(r) for r in roots], 'type_counts': dict(type_counts), 'rows': rows}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
