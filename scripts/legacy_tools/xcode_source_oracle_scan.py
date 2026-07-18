#!/usr/bin/env python3
"""Compile sampled Xcode-bundled .xcassets with Apple actool and summarize outputs.

This scans publicly shipped source catalogs embedded in Xcode bundles and asks
Apple actool to compile them, then inspects any produced Assets.car with the
local clean-room parser. It is intended to locate real public inputs that cause
packed atlas output or other uncommon layout patterns.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

from actool_linux.bom import BOMStore
from actool_linux.car import CARFile


def infer_platform(path: Path) -> tuple[str, str]:
    text = str(path)
    if 'AppleTVOS.platform' in text or '/tvOS/' in text:
        return 'appletvos', '15.0'
    if 'WatchOS.platform' in text or '/watchOS/' in text:
        return 'watchos', '8.0'
    if 'XROS.platform' in text or '/visionOS/' in text or '/xros/' in text:
        return 'xros', '1.0'
    if 'MacOSX.platform' in text or '/macOS/' in text:
        return 'macosx', '13.0'
    if 'iPhoneOS.platform' in text or 'CocoaTouch' in text or '/iOS/' in text:
        return 'iphoneos', '15.0'
    return 'macosx', '13.0'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', action='append', default=[])
    ap.add_argument('--developer-dir')
    ap.add_argument('--limit', type=int, default=80)
    ns = ap.parse_args()
    roots = [Path(p) for p in ns.root] or [Path('/Applications/Xcode.app')]
    catalogs: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob('*.xcassets'):
            catalogs.append(path)
            if len(catalogs) >= ns.limit:
                break
        if len(catalogs) >= ns.limit:
            break
    env = os.environ.copy()
    if ns.developer_dir:
        env['DEVELOPER_DIR'] = ns.developer_dir
    rows = []
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        for idx, catalog in enumerate(catalogs):
            platform, target = infer_platform(catalog)
            out = base / f'out-{idx}'
            out.mkdir()
            proc = subprocess.run([
                'xcrun', 'actool', '--compile', str(out),
                '--platform', platform, '--minimum-deployment-target', target,
                str(catalog),
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            row = {
                'catalog': str(catalog),
                'platform': platform,
                'target': target,
                'rc': proc.returncode,
                'stdout_len': len(proc.stdout),
                'stderr_len': len(proc.stderr),
            }
            car_path = out / 'Assets.car'
            if car_path.exists():
                try:
                    car = CARFile(BOMStore.from_path(str(car_path)))
                    layouts = {}
                    for rendition in car.renditions:
                        layouts[str(rendition.csi.layout)] = layouts.get(str(rendition.csi.layout), 0) + 1
                    row['car'] = {
                        'renditions': len(car.renditions),
                        'facets': len(car.facets),
                        'layouts': layouts,
                    }
                except Exception as exc:
                    row['car_parse_error'] = str(exc)
            rows.append(row)
    packed = [r for r in rows if 'car' in r and '1004' in r['car']['layouts']]
    layerstack = [r for r in rows if 'car' in r and '1002' in r['car']['layouts']]
    print(json.dumps({
        'roots': [str(r) for r in roots],
        'developer_dir': ns.developer_dir,
        'sampled': len(catalogs),
        'rows': rows,
        'packed_hits': packed,
        'layerstack_hits': layerstack,
    }, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
