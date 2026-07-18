#!/usr/bin/env python3
"""Probe suite #5: packed trigger (per-class threshold) + v3 grammar sweep.

Registry-free catalogs. Group C (class/threshold):

- c01_single:    one opaque-color uniform image        -> expect NO packing
- c02_two_col:   two opaque-color uniforms             -> 2 in class -> pack?
- c03_classes:   4 classes with 3/2/1/1 members        -> which classes pack?
- c04_basicmix:  exact basic-suite mirror (4 classes x1) -> expect NO packing
- c05_thresh:    3 opaque-color uniforms               -> threshold probe

Group S (v3/v4 boundary): one singleton image per catalog (never packs)
- u{04..64}:     opaque RGBA uniform squares
- t08,t16:       translucent RGBA uniform
- r08,r16:       opaque RGB (type 2) uniform
- g{08..128}:    opaque GA uniform squares
- h08,h16:       translucent GA uniform
- w0{08,16,32}:  plain gray (type 0) uniform
- n04x64,n08x16: non-square opaque RGBA uniform

Every case is duplicated for iphoneos (a) and macosx (b).
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


def png_rgba(w: int, h: int, px) -> bytes:
    raw = (b"\x00" + bytes(px) * w) * h
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def png_rgb(w: int, h: int, px) -> bytes:
    raw = (b"\x00" + bytes(px) * w) * h
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def png_ga(w: int, h: int, g: int, a: int) -> bytes:
    raw = (b"\x00" + bytes((g, a)) * w) * h
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 4, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def png_gray(w: int, h: int, v: int) -> bytes:
    raw = (b"\x00" + bytes((v,)) * w) * h
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def imageset(cat: Path, name: str, data: bytes, filename: str = "s.png") -> None:
    d = cat / f"{name}.imageset"
    d.mkdir(parents=True, exist_ok=True)
    (d / filename).write_bytes(data)
    (d / "Contents.json").write_text(json.dumps(
        {"images": [{"idiom": "universal", "scale": "1x", "filename": filename}], **INFO}, indent=2))


def catalog(root: Path, case: str) -> Path:
    cat = root / f"{case}.xcassets"
    cat.mkdir(parents=True, exist_ok=True)
    (cat / "Contents.json").write_text(json.dumps(INFO, indent=2))
    return cat


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ns = ap.parse_args()
    cases: dict[str, dict] = {}

    # ---- group C: trigger rules (per platform) ----
    for plat in ("a", "b"):
        c = catalog(ns.out, f"p5{plat}_c01_single")
        imageset(c, "Ru16", png_rgba(16, 16, (10, 200, 90, 255)))

        c = catalog(ns.out, f"p5{plat}_c02_two_col")
        imageset(c, "Ru08", png_rgba(8, 8, (200, 30, 60, 255)))
        imageset(c, "Ru16", png_rgba(16, 16, (10, 200, 90, 255)))

        c = catalog(ns.out, f"p5{plat}_c03_classes")
        imageset(c, "Ru08", png_rgba(8, 8, (200, 30, 60, 255)))
        imageset(c, "Ru16", png_rgba(16, 16, (10, 200, 90, 255)))
        imageset(c, "Rg16", png_rgb(16, 16, (11, 99, 200)))
        imageset(c, "Rt08", png_rgba(8, 8, (200, 10, 40, 128)))
        imageset(c, "Ga08", png_ga(8, 8, 77, 255))
        imageset(c, "Ga16", png_ga(16, 16, 99, 255))
        imageset(c, "Gt08", png_ga(8, 8, 160, 100))

        c = catalog(ns.out, f"p5{plat}_c04_basicmix")
        imageset(c, "AlphaRamp32", png_rgba(32, 32, (9, 9, 9, 128)))
        imageset(c, "Solid64", png_rgba(64, 64, (3, 200, 30, 255)))
        imageset(c, "GA16", png_ga(16, 16, 40, 140))
        imageset(c, "Gray8", png_gray(8, 8, 85))

        c = catalog(ns.out, f"p5{plat}_c05_thresh3")
        for n, size in ((8, 8), (16, 16), (32, 32)):
            imageset(c, f"Ru{size:02d}", png_rgba(size, size, (size, 255 - size, 30, 255)))

    # ---- group S: v3/v4 boundary singles ----
    singles: dict[str, bytes] = {}
    for size in (4, 8, 12, 16, 17, 20, 24, 28, 32, 48, 64):
        singles[f"u{size:02d}"] = png_rgba(size, size, (17, size % 251, 90, 255))
    for size in (8, 16):
        singles[f"t{size:02d}"] = png_rgba(size, size, (200, 10, 40, 128))
        singles[f"h{size:02d}"] = png_ga(size, size, 160, 100)
    singles["r08"] = png_rgb(8, 8, (11, 99, 200))
    singles["r16"] = png_rgb(16, 16, (11, 99, 200))
    for size in (8, 16, 32, 64, 128):
        singles[f"g{size:03d}"] = png_ga(size, size, 77, 255)
    for size in (8, 16, 32):
        singles[f"w{size:02d}"] = png_gray(size, size, 55)
    singles["n04x64"] = png_rgba(4, 64, (9, 9, 200, 255))
    singles["n08x16"] = png_rgba(8, 16, (200, 9, 9, 255))

    for plat in ("a", "b"):
        for key, data in singles.items():
            c = catalog(ns.out, f"p5{plat}_s_{key}")
            imageset(c, f"Img{key}", data)

    for case in ns.out.glob("*.xcassets"):
        platform = "iphoneos" if case.stem.startswith("p5a") else "macosx"
        target = "15.0" if platform == "iphoneos" else "13.0"
        cases[case.stem] = {"args": ["--platform", platform, "--minimum-deployment-target", target]}
    (ns.out / "cases.json").write_text(json.dumps(cases, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
