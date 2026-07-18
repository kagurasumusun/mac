#!/usr/bin/env python3
"""Probe public tvOS .brandassets materialization across installed Xcode 26 releases."""
from __future__ import annotations

import argparse
import binascii
import json
import os
import shutil
import struct
import subprocess
import zlib
from pathlib import Path


def chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', binascii.crc32(kind + payload) & 0xFFFFFFFF)


def png(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    row = b'\0' + bytes((*rgb, 255)) * width
    raw = row * height
    return (
        b'\x89PNG\r\n\x1a\n'
        + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
        + chunk(b'IDAT', zlib.compress(raw, 9))
        + chunk(b'IEND', b'')
    )


def write_json(path: Path, obj: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))


def info() -> dict[str, object]:
    return {'info': {'author': 'xcode', 'version': 1}}


def make_catalog(root: Path) -> Path:
    catalog = root / 'Assets.xcassets'
    brand = catalog / 'tvOS App Icon & Top Shelf Image.brandassets'
    write_json(brand / 'Contents.json', {
        'assets': [
            {'size': '1280x768', 'idiom': 'tv', 'filename': 'App Icon - Large.imagestack', 'role': 'primary-app-icon'},
            {'size': '400x240', 'idiom': 'tv', 'filename': 'App Icon - Small.imagestack', 'role': 'primary-app-icon'},
            {'size': '1920x720', 'idiom': 'tv', 'filename': 'Top Shelf Image.imageset', 'role': 'top-shelf-image'},
            {'size': '2320x720', 'idiom': 'tv', 'filename': 'Top Shelf Image Wide.imageset', 'role': 'top-shelf-image-wide'},
        ],
        **info(),
    })
    for stack_name, size, c1, c2 in [
        ('App Icon - Large.imagestack', (1280, 768), (220, 80, 80), (60, 60, 240)),
        ('App Icon - Small.imagestack', (400, 240), (220, 120, 60), (60, 160, 240)),
    ]:
        stack = brand / stack_name
        write_json(stack / 'Contents.json', {'layers': [{'filename': 'Front.imagestacklayer'}, {'filename': 'Back.imagestacklayer'}], **info()})
        for layer_name, color in [('Front.imagestacklayer', c1), ('Back.imagestacklayer', c2)]:
            image = stack / layer_name / 'Content.imageset'
            image.mkdir(parents=True, exist_ok=True)
            width, height = size
            (image / 'content.png').write_bytes(png(width, height, color))
            write_json(image / 'Contents.json', {'images': [{'idiom': 'tv', 'scale': '1x', 'filename': 'content.png'}], **info()})
            write_json(stack / layer_name / 'Contents.json', info())
    for name, size, color in [
        ('Top Shelf Image.imageset', (1920, 720), (40, 160, 80)),
        ('Top Shelf Image Wide.imageset', (2320, 720), (80, 100, 200)),
    ]:
        image = brand / name
        image.mkdir(parents=True, exist_ok=True)
        (image / 'image.png').write_bytes(png(size[0], size[1], color))
        write_json(image / 'Contents.json', {'images': [{'idiom': 'tv', 'scale': '1x', 'filename': 'image.png'}], **info()})
    return catalog


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, default=Path('/tmp/brandassets-xcode-matrix'))
    ap.add_argument('--output', type=Path, default=Path('brandassets-xcode26-targettv-matrix.json'))
    ns = ap.parse_args()
    shutil.rmtree(ns.root, ignore_errors=True)
    catalog = make_catalog(ns.root)
    xcodes = [path for path in sorted(Path('/Applications').glob('Xcode_26*.app')) if path.is_dir()]
    cases = [
        ('base', ['--app-icon', 'tvOS App Icon & Top Shelf Image']),
        ('target_tv', ['--app-icon', 'tvOS App Icon & Top Shelf Image', '--target-device', 'tv']),
    ]
    rows = []
    for xcode in xcodes:
        developer_dir = str(xcode / 'Contents/Developer')
        version = subprocess.run(
            ['xcodebuild', '-version'],
            capture_output=True,
            text=True,
            env={**os.environ, 'DEVELOPER_DIR': developer_dir},
        ).stdout.splitlines()[:2]
        for case_name, extra in cases:
            out = ns.root / f'{xcode.stem}-{case_name}'
            shutil.rmtree(out, ignore_errors=True)
            out.mkdir(parents=True, exist_ok=True)
            partial = ns.root / f'{xcode.stem}-{case_name}.plist'
            cmd = [
                'xcrun', 'actool', '--compile', str(out), '--platform', 'appletvos',
                '--minimum-deployment-target', '15.0', '--output-partial-info-plist', str(partial),
                *extra, str(catalog),
            ]
            proc = subprocess.run(cmd, capture_output=True, env={**os.environ, 'DEVELOPER_DIR': developer_dir})
            rows.append({
                'xcode_app': xcode.name,
                'developer_dir': developer_dir,
                'version': version,
                'case': case_name,
                'exit': proc.returncode,
                'car_exists': (out / 'Assets.car').exists(),
                'partial_exists': partial.exists(),
                'stderr': proc.stderr.decode('utf-8', 'replace'),
            })
    ns.output.write_text(json.dumps({'schema': 1, 'rows': rows}, indent=2) + '\n')
    print(json.dumps({'rows': len(rows), 'output': str(ns.output)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
