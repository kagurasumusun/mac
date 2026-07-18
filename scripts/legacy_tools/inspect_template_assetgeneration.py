#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, plistlib
from pathlib import Path

TARGET_TYPES = {'tvappicon', 'solidimagestack', 'appicon', 'stickersicon'}


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
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob('TemplateInfo.plist'):
            try:
                data = plistlib.loads(path.read_bytes())
            except Exception:
                continue
            ag_rows = []
            def cb(node):
                if isinstance(node, dict) and 'AssetGeneration' in node:
                    ag = node['AssetGeneration']
                    items = [ag] if isinstance(ag, dict) else [x for x in ag if isinstance(x, dict)] if isinstance(ag, list) else []
                    for entry in items:
                        if entry.get('Type') in TARGET_TYPES:
                            ag_rows.append({
                                'type': entry.get('Type'),
                                'name': entry.get('Name'),
                                'platforms': entry.get('Platforms'),
                                'entry': entry,
                            })
            walk(data, cb)
            if ag_rows:
                rows.append({'path': str(path), 'asset_generation': ag_rows})
    print(json.dumps({'rows': rows}, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
