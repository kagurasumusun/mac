#!/usr/bin/env python3
"""Probe indexed-PNG output across legacy reference Xcode installs.

This stays on the clean-room side: it feeds synthetic indexed PNGs into Apple
actool and records the observable CAR compression selected by each Xcode.
"""
from __future__ import annotations

import binascii
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import zlib

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


def chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', binascii.crc32(kind + payload) & 0xffffffff)


def indexed_png(size: int, alpha: bool, bit_depth: int) -> bytes:
    if bit_depth not in (1, 2, 4, 8):
        raise ValueError(bit_depth)
    palette = bytes.fromhex('ff000000ff000000ffffff00')
    transparency = bytes([255, 128, 255, 64]) if alpha else b''
    rows = []
    per_byte = 8 // bit_depth
    mask = (1 << bit_depth) - 1
    for y in range(size):
        idx = [(x + y) % 4 for x in range(size)]
        packed = bytearray()
        for x in range(0, size, per_byte):
            value = 0
            for j in range(per_byte):
                sample = idx[x + j] if x + j < size else 0
                shift = 8 - bit_depth * (j + 1)
                value |= (sample & mask) << shift
            packed.append(value)
        rows.append(b'\0' + packed)
    result = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, bit_depth, 3, 0, 0, 0)) + chunk(b'PLTE', palette)
    if transparency:
        result += chunk(b'tRNS', transparency)
    return result + chunk(b'IDAT', zlib.compress(b''.join(rows))) + chunk(b'IEND', b'')


def short_name(app: str) -> str:
    return Path(app).stem


def main() -> int:
    rows = []
    root = Path('/tmp/palette-legacy-matrix')
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir()
    for app in XCODE_APPS:
        if not Path(app).exists():
            rows.append({'xcode': short_name(app), 'present': False})
            continue
        env = os.environ.copy()
        env['DEVELOPER_DIR'] = app + '/Contents/Developer'
        for size in (2, 16, 64, 256):
            for alpha in (False, True):
                for bit_depth in (1, 2, 4, 8):
                    base = root / f'{short_name(app)}-{size}-{alpha}-{bit_depth}'
                    catalog = base / 'A.xcassets'
                    item = catalog / 'P.imageset'
                    out = base / 'out'
                    item.mkdir(parents=True)
                    out.mkdir()
                    (item / 'p.png').write_bytes(indexed_png(size, alpha, bit_depth))
                    (item / 'Contents.json').write_text(json.dumps({
                        'images': [{'filename': 'p.png', 'idiom': 'universal', 'scale': '1x'}],
                        'info': {'author': 'xcode', 'version': 1},
                    }))
                    build = subprocess.run([
                        'xcrun', 'actool', '--compile', str(out), '--platform', 'macosx',
                        '--minimum-deployment-target', '13.0', str(catalog),
                    ], env=env, capture_output=True, text=True)
                    row = {'xcode': short_name(app), 'size': size, 'alpha': alpha, 'bit_depth': bit_depth, 'present': True, 'build_rc': build.returncode}
                    if build.returncode:
                        rows.append(row | {'status': 'build-failed', 'stderr_tail': build.stderr[-300:]})
                        continue
                    info = subprocess.run(['xcrun', 'assetutil', '--info', str(out / 'Assets.car')], env=env, capture_output=True, text=True)
                    try:
                        asset = json.loads(info.stdout)[1]
                        rows.append(row | {'compression': asset.get('Compression'), 'encoding': asset.get('Encoding'), 'disk': asset.get('SizeOnDisk')})
                    except Exception:
                        rows.append(row | {'status': 'info-failed', 'stdout_head': info.stdout[:300]})
    print(json.dumps(rows, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
