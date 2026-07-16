#!/usr/bin/env python3
"""Probe suite #4: dmp2 v3-mini grammar collection.

registry-free catalogs (no appearances/localizations) so every rendition
stays a layout-12 deepmap. Sweep uniform-image sizes to pin the v3/v4/v2
grammar boundary and gather v3-mini samples for decoding.

- probe4a.xcassets -> iphoneos
- probe4b.xcassets -> macosx (does the platform alter the grammar choice?)
"""
from __future__ import annotations

import argparse
import binascii
import json
import struct
import zlib
from pathlib import Path

INFO = {"info": {"author": "xcode", "version": 1}}


def chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", binascii.crc32(kind + payload) & 0xFFFFFFFF)


def png_rgba(w: int, h: int, rgba) -> bytes:
    raw = (b"\x00" + bytes(rgba) * w) * h
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def png_rgb(w: int, h: int, rgb) -> bytes:
    raw = (b"\x00" + bytes(rgb) * w) * h
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def png_ga(w: int, h: int, gray: int, alpha: int) -> bytes:
    raw = (b"\x00" + bytes((gray, alpha)) * w) * h
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 4, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def png_gray(w: int, h: int, v: int) -> bytes:
    raw = (b"\x00" + bytes((v,)) * w) * h
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def write_imageset(cat: Path, name: str, data: bytes, filename: str = "s.png") -> None:
    d = cat / f"{name}.imageset"
    d.mkdir(parents=True, exist_ok=True)
    (d / filename).write_bytes(data)
    (d / "Contents.json").write_text(json.dumps(
        {"images": [{"idiom": "universal", "scale": "1x", "filename": filename}], **INFO}, indent=2))


def fill(cat: Path) -> None:
    # opaque uniform RGBA square sweep (odd sizes catch even-width rules)
    for size in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 16, 17, 18, 20, 22, 24, 28, 32, 40, 64):
        write_imageset(cat, f"Ru{size:02d}", png_rgba(size, size, (17, size * 3 % 251, 90, 255)))
    # translucent uniform RGBA (mode 0 expectation)
    for size in (4, 8, 16, 32):
        write_imageset(cat, f"Rt{size:02d}", png_rgba(size, size, (200, 10, 40, 128)))
    # opaque uniform RGB (color type 2)
    for size in (8, 16, 32):
        write_imageset(cat, f"Rg{size:02d}", png_rgb(size, size, (11, 99, 200)))
    # gray+alpha uniform opaque / translucent
    for size in (8, 16, 32, 64, 128):
        write_imageset(cat, f"Ga{size:03d}", png_ga(size, size, 77, 255))
    for size in (8, 16, 32):
        write_imageset(cat, f"Gt{size:02d}", png_ga(size, size, 160, 100))
    # plain gray (type 0)
    for size in (8, 16, 32):
        write_imageset(cat, f"Gr{size:02d}", png_gray(size, size, 55))
    # non-square uniform RGBA: boundary metric (area vs max dim)
    for w, h in ((8, 16), (16, 8), (4, 64), (64, 4), (2, 128), (128, 2), (12, 12)):
        write_imageset(cat, f"Rw{w:03d}x{h:03d}", png_rgba(w, h, (w % 256, h % 256, 77, 255)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ns = ap.parse_args()
    for case, platform in (("probe4a", "iphoneos"), ("probe4b", "macosx")):
        cat = ns.out / f"{case}.xcassets"
        cat.mkdir(parents=True, exist_ok=True)
        (cat / "Contents.json").write_text(json.dumps(INFO, indent=2))
        fill(cat)
    cases = {
        "probe4a": {"args": ["--platform", "iphoneos", "--minimum-deployment-target", "15.0"]},
        "probe4b": {"args": ["--platform", "macosx", "--minimum-deployment-target", "13.0"]},
    }
    (ns.out / "cases.json").write_text(json.dumps(cases, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
