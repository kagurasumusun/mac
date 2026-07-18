#!/usr/bin/env python3
"""Probe suite #3: packed-asset (ZZZZPackedAsset / LINK) and dmp2 v3/v4 boundary rules.

Two catalogs:
- probe3a.xcassets (iphoneos): size sweeps, appearance/localization variants,
  non-uniform and GA sources -> which default renditions become layout-1003
  LINK renditions into a packed atlas, and which stay layout 12.
- probe3b.xcassets (macosx): does packing happen on the macOS platform?
"""
from __future__ import annotations

import argparse
import binascii
import json
import struct
import zlib
from pathlib import Path

INFO = {"info": {"author": "xcode", "version": 1}}
DARK = [{"appearance": "luminosity", "value": "dark"}]


def chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", binascii.crc32(kind + payload) & 0xFFFFFFFF)


def png_rgba(w: int, h: int, rgba) -> bytes:
    raw = (b"\x00" + bytes(rgba) * w) * h
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def png_rgba_gradient(w: int, h: int) -> bytes:
    rows = []
    for y in range(h):
        row = bytearray(b"\x00")
        for x in range(w):
            row += bytes(((x * 7 + y) % 256, (x + y * 5) % 256, (x * 3 + y * 11) % 256, 255))
        rows.append(bytes(row))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + chunk(b"IEND", b""))


def png_gray(w: int, h: int, v: int) -> bytes:
    raw = (b"\x00" + bytes((v,)) * w) * h
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def write_imageset(cat: Path, name: str, entries: list[dict], files: dict[str, bytes]) -> None:
    d = cat / f"{name}.imageset"
    d.mkdir(parents=True, exist_ok=True)
    for fn, data in files.items():
        (d / fn).write_bytes(data)
    write_json(d / "Contents.json", {"images": entries, **INFO})


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2))


def build_a(root: Path) -> None:
    cat = root / "probe3a.xcassets"
    cat.mkdir(parents=True, exist_ok=True)
    write_json(cat / "Contents.json", INFO)

    # U8: 8x8 uniform, 1x+2x, no appearance -> multi-scale facet
    write_imageset(cat, "U8",
        [{"idiom": "universal", "scale": "1x", "filename": "u1.png"},
         {"idiom": "universal", "scale": "2x", "filename": "u2.png"}],
        {"u1.png": png_rgba(8, 8, (200, 30, 60, 255)), "u2.png": png_rgba(16, 16, (200, 30, 60, 255))})

    # U16single: 16x16 uniform, single rendition
    write_imageset(cat, "U16single",
        [{"idiom": "universal", "scale": "1x", "filename": "s.png"}],
        {"s.png": png_rgba(16, 16, (10, 220, 90, 255))})

    # U24/U32/U64: uniform any+dark (appearance registry present)
    for size, base in ((24, (255, 128, 0)), (32, (0, 128, 255)), (64, (128, 0, 255))):
        write_imageset(cat, f"U{size}",
            [{"idiom": "universal", "scale": "1x", "filename": "any.png"},
             {"idiom": "universal", "scale": "1x", "appearances": DARK, "filename": "dark.png"}],
            {"any.png": png_rgba(size, size, (*base, 255)),
             "dark.png": png_rgba(size, size, (255 - base[0], 255 - base[1], 255 - base[2], 255))})

    # NU32: non-uniform any+dark
    write_imageset(cat, "NU32",
        [{"idiom": "universal", "scale": "1x", "filename": "any.png"},
         {"idiom": "universal", "scale": "1x", "appearances": DARK, "filename": "dark.png"}],
        {"any.png": png_rgba_gradient(32, 32), "dark.png": png_rgba_gradient(32, 32)})

    # GA8set: grayscale uniform any+dark
    write_imageset(cat, "GA8set",
        [{"idiom": "universal", "scale": "1x", "filename": "any.png"},
         {"idiom": "universal", "scale": "1x", "appearances": DARK, "filename": "dark.png"}],
        {"any.png": png_gray(8, 8, 90), "dark.png": png_gray(8, 8, 200)})

    # Loc8: uniform any + ja (localization registry)
    write_imageset(cat, "Loc8",
        [{"idiom": "universal", "scale": "1x", "filename": "any.png"},
         {"idiom": "universal", "scale": "1x", "locale": "de", "filename": "de.png"}],
        {"any.png": png_rgba(8, 8, (77, 88, 99, 255)), "de.png": png_rgba(8, 8, (111, 122, 133, 255))})

    # Size sweep singles (v3/v4 boundary + single-facet packing question)
    for size in (16, 17, 24, 32, 48):
        write_imageset(cat, f"S{size}",
            [{"idiom": "universal", "scale": "1x", "filename": "s.png"}],
            {"s.png": png_rgba(size, size, (size, 200 - size, 30, 255))})


def build_b(root: Path) -> None:
    cat = root / "probe3b.xcassets"
    cat.mkdir(parents=True, exist_ok=True)
    write_json(cat / "Contents.json", INFO)
    # macosx: uniform any+dark 32x32 -> packing on macOS?
    write_imageset(cat, "MU32",
        [{"idiom": "universal", "scale": "1x", "filename": "any.png"},
         {"idiom": "universal", "scale": "1x", "appearances": DARK, "filename": "dark.png"}],
        {"any.png": png_rgba(32, 32, (1, 100, 200, 255)), "dark.png": png_rgba(32, 32, (200, 100, 1, 255))})
    # macosx: multi-scale 8x8 uniform
    write_imageset(cat, "MU8",
        [{"idiom": "universal", "scale": "1x", "filename": "u1.png"},
         {"idiom": "universal", "scale": "2x", "filename": "u2.png"}],
        {"u1.png": png_rgba(8, 8, (9, 8, 7, 255)), "u2.png": png_rgba(16, 16, (9, 8, 7, 255))})


CASE_ARGS = {
    "probe3a": {"args": ["--platform", "iphoneos", "--minimum-deployment-target", "15.0"]},
    "probe3b": {"args": ["--platform", "macosx", "--minimum-deployment-target", "13.0"]},
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ns = ap.parse_args()
    build_a(ns.out)
    build_b(ns.out)
    write_json(ns.out / "cases.json", CASE_ARGS)
    print("probe3 suite written to", ns.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
