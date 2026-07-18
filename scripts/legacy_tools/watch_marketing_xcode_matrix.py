#!/usr/bin/env python3
"""Probe watch-marketing AppIcon compiler behavior across installed Xcode 26 apps.

This stays on the observable side of the clean-room boundary: it builds a tiny
catalog, invokes Apple actool, and records whether a CAR/sidecars materialize.
"""
from __future__ import annotations

import json
import os
import plistlib
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import zlib

XCODE_APPS = [
    "/Applications/Xcode_26.0.1.app",
    "/Applications/Xcode_26.1.1.app",
    "/Applications/Xcode_26.2.0.app",
    "/Applications/Xcode_26.3.0.app",
    "/Applications/Xcode_26.4.1.app",
    "/Applications/Xcode_26.5.0.app",
    "/Applications/Xcode_26.6.0.app",
]


def solid_rgba_png(width: int, height: int, rgba: tuple[int, int, int, int]) -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    row = bytes(rgba) * width
    scanlines = b"".join(b"\0" + row for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(scanlines, 9))
        + chunk(b"IEND", b"")
    )


def short_version(app: str) -> str:
    match = re.search(r"Xcode_(.+)\.app$", app)
    return match.group(1) if match else Path(app).name


def main() -> int:
    rows = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "Assets.xcassets"
        item = root / "AppIcon.appiconset"
        item.mkdir(parents=True)
        (item / "watch.png").write_bytes(solid_rgba_png(1024, 1024, (255, 0, 0, 255)))
        (item / "Contents.json").write_text(json.dumps({
            "images": [
                {
                    "filename": "watch.png",
                    "platform": "watchos",
                    "idiom": "watch-marketing",
                    "role": "notificationCenter",
                    "size": "1024x1024",
                }
            ],
            "info": {"author": "xcode", "version": 1},
        }))
        for app in XCODE_APPS:
            version = short_version(app)
            if not Path(app).exists():
                rows.append({"xcode": version, "present": False})
                continue
            env = dict(os.environ, DEVELOPER_DIR=f"{app}/Contents/Developer")
            outdir = Path(td) / f"out-{version}"
            outdir.mkdir()
            partial = Path(td) / f"{version}.plist"
            proc = subprocess.run([
                "xcrun", "actool", "--compile", str(outdir),
                "--platform", "watchos", "--minimum-deployment-target", "11.0",
                "--app-icon", "AppIcon", "--output-partial-info-plist", str(partial),
                str(root),
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            rows.append({
                "xcode": version,
                "present": True,
                "rc": proc.returncode,
                "outputs": sorted(p.name for p in outdir.glob("*") if p.is_file()),
                "partial": plistlib.loads(partial.read_bytes()) if partial.exists() else None,
                "stdout_len": len(proc.stdout),
                "stderr_len": len(proc.stderr),
            })
    print(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
