#!/usr/bin/env python3
"""Synthesize a public tvOS .brandassets catalog and report Apple actool behavior.

This is intended for clean-room contract discovery, not for claiming private
aggregate equivalence. It records only observable output files and assetutil
summaries.
"""
from __future__ import annotations

import argparse
import binascii
import hashlib
import json
import plistlib
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


def info() -> dict[str, object]:
    return {'info': {'author': 'xcode', 'version': 1}}


def write_json(path: Path, obj: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))


def make_stack(root: Path, name: str, size: tuple[int, int], colors: tuple[tuple[int, int, int], tuple[int, int, int]]) -> None:
    stack = root / name
    write_json(stack / 'Contents.json', {'layers': [{'filename': 'Front.imagestacklayer'}, {'filename': 'Back.imagestacklayer'}], **info()})
    width, height = size
    for layer_name, color in (('Front.imagestacklayer', colors[0]), ('Back.imagestacklayer', colors[1])):
        image = stack / layer_name / 'Content.imageset'
        image.mkdir(parents=True, exist_ok=True)
        (image / 'content.png').write_bytes(png(width, height, color))
        write_json(image / 'Contents.json', {'images': [{'idiom': 'tv', 'scale': '1x', 'filename': 'content.png'}], **info()})
        write_json((stack / layer_name / 'Contents.json'), info())


def make_imageset(root: Path, name: str, size: tuple[int, int], color: tuple[int, int, int]) -> None:
    image = root / name
    image.mkdir(parents=True, exist_ok=True)
    (image / 'image.png').write_bytes(png(size[0], size[1], color))
    write_json(image / 'Contents.json', {'images': [{'idiom': 'tv', 'scale': '1x', 'filename': 'image.png'}], **info()})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, default=Path('/tmp/brandassets-probe'))
    ap.add_argument('--output', type=Path, default=Path('brandassets-probe.json'))
    ap.add_argument('--app-icon-name', default='tvOS App Icon & Top Shelf Image')
    ap.add_argument('--platform', default='appletvos')
    ap.add_argument('--target', default='15.0')
    ap.add_argument('--product-type', default='')
    ns = ap.parse_args()

    shutil.rmtree(ns.root, ignore_errors=True)
    catalog = ns.root / 'Assets.xcassets'
    brand = catalog / f'{ns.app_icon_name}.brandassets'
    write_json(brand / 'Contents.json', {
        'assets': [
            {'size': '1280x768', 'idiom': 'tv', 'filename': 'App Icon - Large.imagestack', 'role': 'primary-app-icon'},
            {'size': '400x240', 'idiom': 'tv', 'filename': 'App Icon - Small.imagestack', 'role': 'primary-app-icon'},
            {'size': '1920x720', 'idiom': 'tv', 'filename': 'Top Shelf Image.imageset', 'role': 'top-shelf-image'},
            {'size': '2320x720', 'idiom': 'tv', 'filename': 'Top Shelf Image Wide.imageset', 'role': 'top-shelf-image-wide'},
        ],
        **info(),
    })
    make_stack(brand, 'App Icon - Large.imagestack', (1280, 768), ((220, 80, 80), (60, 60, 240)))
    make_stack(brand, 'App Icon - Small.imagestack', (400, 240), ((220, 120, 60), (60, 160, 240)))
    make_imageset(brand, 'Top Shelf Image.imageset', (1920, 720), (40, 160, 80))
    make_imageset(brand, 'Top Shelf Image Wide.imageset', (2320, 720), (80, 100, 200))

    out = ns.root / 'out'
    out.mkdir(parents=True, exist_ok=True)
    partial = ns.root / 'partial.plist'
    cmd = [
        'xcrun', 'actool', '--compile', str(out), '--platform', ns.platform,
        '--minimum-deployment-target', ns.target, '--app-icon', ns.app_icon_name,
        '--output-partial-info-plist', str(partial),
    ]
    if ns.product_type:
        cmd += ['--product-type', ns.product_type]
    cmd.append(str(catalog))
    actool = subprocess.run(cmd, capture_output=True)
    report: dict[str, object] = {
        'command': cmd,
        'exit_code': actool.returncode,
        'stdout': actool.stdout.decode('utf-8', 'replace'),
        'stderr': actool.stderr.decode('utf-8', 'replace'),
        'car_exists': (out / 'Assets.car').exists(),
        'partial_exists': partial.exists(),
        'output_files': sorted(str(path.relative_to(ns.root)) for path in ns.root.rglob('*') if path.is_file()),
    }
    try:
        report['parsed_stdout'] = plistlib.loads(actool.stdout)
    except Exception:
        pass
    car = out / 'Assets.car'
    if car.exists():
        report['car_sha256'] = hashlib.sha256(car.read_bytes()).hexdigest()
        util = subprocess.run(['xcrun', '--sdk', ns.platform, 'assetutil', '--info', str(car)], capture_output=True, text=True)
        report['assetutil_exit'] = util.returncode
        if util.returncode == 0:
            rows = json.loads(util.stdout)
            report['assetutil_rows'] = [
                {k: row.get(k) for k in ('Name', 'AssetType', 'Idiom', 'Role', 'Scale', 'PixelWidth', 'PixelHeight', 'Layer')}
                for row in rows[:20]
            ]
        else:
            report['assetutil_stdout'] = util.stdout
            report['assetutil_stderr'] = util.stderr
    ns.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'exit_code': actool.returncode, 'car_exists': report['car_exists'], 'partial_exists': report['partial_exists'], 'output': str(ns.output)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
