#!/usr/bin/env python3
"""Run assetutil consumer checks for a generated palette-img CAR across older Xcodes.

The CAR path is fixed to /tmp/paletteimg.car because this probe is intended for
use on the legacy reference host after copying a generated CAR there.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

XCODE_APPS = [
    '/Applications/Xcode_15.0.app',
    '/Applications/Xcode_15.0.1.app',
    '/Applications/Xcode_15.1.app',
    '/Applications/Xcode_15.1.0.app',
    '/Applications/Xcode_15.2.app',
    '/Applications/Xcode_15.2.0.app',
    '/Applications/Xcode_15.3.app',
    '/Applications/Xcode_15.3.0.app',
    '/Applications/Xcode_15.4.app',
    '/Applications/Xcode_15.4.0.app',
    '/Applications/Xcode_16.1.app',
    '/Applications/Xcode_16.1.0.app',
    '/Applications/Xcode_16.2.app',
    '/Applications/Xcode_16.2.0.app',
]
CAR = Path('/tmp/paletteimg.car')


def short(app: str) -> str:
    return Path(app).stem


def main() -> int:
    rows = []
    for app in XCODE_APPS:
        if not Path(app).exists():
            rows.append({'xcode': short(app), 'present': False})
            continue
        env = os.environ.copy()
        env['DEVELOPER_DIR'] = app + '/Contents/Developer'
        proc = subprocess.run(['xcrun', 'assetutil', '--info', str(CAR)], env=env, capture_output=True, text=True)
        row = {'xcode': short(app), 'present': True, 'rc': proc.returncode, 'stderr_len': len(proc.stderr)}
        try:
            info = json.loads(proc.stdout)
            asset = info[1]
            row.update({'compression': asset.get('Compression'), 'encoding': asset.get('Encoding'), 'width': asset.get('PixelWidth'), 'height': asset.get('PixelHeight')})
        except Exception:
            row.update({'status': 'parse-failed', 'stdout_head': proc.stdout[:300]})
        rows.append(row)
    print(json.dumps(rows, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
