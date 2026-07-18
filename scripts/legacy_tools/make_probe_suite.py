#!/usr/bin/env python3
"""Generate a differential probe catalog suite (clean-room inputs).

Each case directory is an .xcassets with controlled, distinct content so that
Apple's actool output can be compared byte-for-byte against actool-linux.

Usage: make_probe_suite.py OUT_DIR
"""
from __future__ import annotations

import argparse
import binascii
import json
import math
import shutil
import struct
import zlib
from pathlib import Path


def chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload)) + kind + payload
        + struct.pack(">I", binascii.crc32(kind + payload) & 0xFFFFFFFF)
    )


def png_rgb(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    row = b"\x00" + bytes((*rgb,)) * width
    raw = row * height
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def png_rgba(width: int, height: int, rgba: tuple[int, int, int, int]) -> bytes:
    row = b"\x00" + bytes((*rgba,)) * width
    raw = row * height
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def png_rgba_gradient(width: int, height: int) -> bytes:
    """Distinct non-uniform content: horizontal gradient + alpha ramp."""
    rows = []
    for y in range(height):
        row = bytearray(b"\x00")
        for x in range(width):
            row += bytes((x * 255 // max(width - 1, 1),
                          y * 255 // max(height - 1, 1),
                          (x + y) * 255 // max(width + height - 2, 1),
                          64 + 191 * x // max(width - 1, 1)))
        rows.append(bytes(row))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"".join(rows), 9))
        + chunk(b"IEND", b"")
    )


def png_ga(width: int, height: int, gray: int, alpha: int) -> bytes:
    row = b"\x00" + bytes((gray, alpha)) * width
    raw = row * height
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 4, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def png_gray(width: int, height: int, gray: int) -> bytes:
    row = b"\x00" + bytes((gray,)) * width
    raw = row * height
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


INFO = {"info": {"author": "xcode", "version": 1}}


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2))


def make_stack(brand: Path, name: str, size: tuple[int, int],
               layers: list[tuple[str, bytes]]) -> None:
    stack = brand / name
    write_json(stack / "Contents.json",
               {"layers": [{"filename": f"{ln}.imagestacklayer"} for ln, _ in layers], **INFO})
    for layer_name, png_bytes in layers:
        image = stack / f"{layer_name}.imagestacklayer" / "Content.imageset"
        image.mkdir(parents=True, exist_ok=True)
        (image / "content.png").write_bytes(png_bytes)
        write_json(image / "Contents.json",
                   {"images": [{"idiom": "tv", "scale": "1x", "filename": "content.png"}], **INFO})
        write_json(stack / f"{layer_name}.imagestacklayer" / "Contents.json", INFO)


def case_basic(root: Path) -> None:
    cat = root / "basic.xcassets"
    for name, data in (("Solid64", png_rgba(64, 64, (10, 20, 30, 255))),
                       ("AlphaRamp32", png_rgba_gradient(32, 32)),
                       ("GA16", png_ga(16, 16, 200, 128)),
                       ("Gray8", png_gray(8, 8, 90))):
        d = cat / f"{name}.imageset"
        d.mkdir(parents=True, exist_ok=True)
        (d / "img.png").write_bytes(data)
        write_json(d / "Contents.json",
                   {"images": [{"idiom": "universal", "scale": "1x", "filename": "img.png"}], **INFO})
    write_json(cat / "Contents.json", INFO)


def case_scales(root: Path) -> None:
    cat = root / "scales.xcassets"
    d = cat / "Multi.imageset"
    d.mkdir(parents=True, exist_ok=True)
    for scale, px in (("1x", 16), ("2x", 32), ("3x", 48)):
        (d / f"img{scale}.png").write_bytes(png_rgba(px, px, (30, 100, 200, 255)))
    write_json(d / "Contents.json", {"images": [
        {"idiom": "universal", "scale": s, "filename": f"img{s}.png"} for s in ("1x", "2x", "3x")
    ], **INFO})
    # appearance + localization variants
    d2 = cat / "Variant.imageset"
    d2.mkdir(parents=True, exist_ok=True)
    (d2 / "any.png").write_bytes(png_rgba(8, 8, (1, 2, 3, 255)))
    (d2 / "dark.png").write_bytes(png_rgba(8, 8, (4, 5, 6, 255)))
    (d2 / "ja.png").write_bytes(png_rgba(8, 8, (7, 8, 9, 255)))
    write_json(d2 / "Contents.json", {"images": [
        {"idiom": "universal", "scale": "1x", "filename": "any.png"},
        {"idiom": "universal", "scale": "1x", "appearances": [{"appearance": "luminosity", "value": "dark"}], "filename": "dark.png"},
        {"idiom": "universal", "scale": "1x", "locale": "ja", "filename": "ja.png"},
    ], **INFO})
    write_json(cat / "Contents.json", INFO)


def case_color_data(root: Path) -> None:
    cat = root / "colordata.xcassets"
    c1 = cat / "Tint.colorset"
    c1.mkdir(parents=True, exist_ok=True)
    write_json(c1 / "Contents.json", {"colors": [
        {"idiom": "universal", "color": {"color-space": "srgb", "components": {
            "red": "0.25", "green": "0.5", "blue": "0.75", "alpha": "0.875"}}},
        {"idiom": "universal", "appearances": [{"appearance": "luminosity", "value": "dark"}],
         "color": {"color-space": "display-p3", "components": {
             "red": "1.0", "green": "0x80", "blue": "16", "alpha": "1.0"}}},
    ], **INFO})
    d = cat / "Blob.dataset"
    d.mkdir(parents=True, exist_ok=True)
    (d / "blob.bin").write_bytes(bytes(range(256)))
    write_json(d / "Contents.json", {"data": [
        {"idiom": "universal", "filename": "blob.bin", "universal-type-identifier": "public.data"}
    ], **INFO})
    write_json(cat / "Contents.json", INFO)


def case_brandassets(root: Path) -> None:
    cat = root / "brand.xcassets"
    brand = cat / "Icon.brandassets"
    write_json(brand / "Contents.json", {"assets": [
        {"size": "1280x768", "idiom": "tv", "filename": "App Icon - Large.imagestack", "role": "primary-app-icon"},
        {"size": "400x240", "idiom": "tv", "filename": "App Icon - Small.imagestack", "role": "primary-app-icon"},
        {"size": "1920x720", "idiom": "tv", "filename": "Top Shelf Image.imageset", "role": "top-shelf-image"},
        {"size": "2320x720", "idiom": "tv", "filename": "Top Shelf Image Wide.imageset", "role": "top-shelf-image-wide"},
    ], **INFO})
    make_stack(brand, "App Icon - Large.imagestack", (1280, 768), [
        ("Front", png_rgba(1280, 768, (220, 80, 80, 255))),
        ("Back", png_rgba(1280, 768, (60, 60, 240, 255))),
    ])
    make_stack(brand, "App Icon - Small.imagestack", (400, 240), [
        ("Front", png_rgba(400, 240, (220, 120, 60, 255))),
        ("Middle", png_rgba(400, 240, (0, 200, 120, 128))),
        ("Back", png_rgba(400, 240, (60, 160, 240, 255))),
    ])
    for name, size, rgb in (("Top Shelf Image", (1920, 720), (40, 160, 80)),
                            ("Top Shelf Image Wide", (2320, 720), (80, 100, 200))):
        d = brand / f"{name}.imageset"
        d.mkdir(parents=True, exist_ok=True)
        (d / "image.png").write_bytes(png_rgba(size[0], size[1], (*rgb, 255)))
        write_json(d / "Contents.json",
                   {"images": [{"idiom": "tv", "scale": "1x", "filename": "image.png"}], **INFO})
    write_json(cat / "Contents.json", INFO)


def case_imagestack_tv(root: Path) -> None:
    cat = root / "tvstack.xcassets"
    stack = cat / "Poster.imagestack"
    write_json(stack / "Contents.json",
               {"layers": [{"filename": "Front.imagestacklayer"}, {"filename": "Back.imagestacklayer"}], **INFO})
    for layer_name, rgb in (("Front", (250, 10, 10)), ("Back", (10, 10, 250))):
        image = stack / f"{layer_name}.imagestacklayer" / "Content.imageset"
        image.mkdir(parents=True, exist_ok=True)
        (image / "content.png").write_bytes(png_rgba(560, 840, (*rgb, 255)))
        write_json(image / "Contents.json",
                   {"images": [{"idiom": "tv", "scale": "1x", "filename": "content.png"}], **INFO})
        write_json(stack / f"{layer_name}.imagestacklayer" / "Contents.json", INFO)
    write_json(cat / "Contents.json", INFO)


CASES = {
    "basic": case_basic,
    "scales": case_scales,
    "colordata": case_color_data,
    "brand": case_brandassets,
    "tvstack": case_imagestack_tv,
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("--cases", nargs="*", default=sorted(CASES))
    ns = ap.parse_args()
    shutil.rmtree(ns.out, ignore_errors=True)
    ns.out.mkdir(parents=True, exist_ok=True)
    for name in ns.cases:
        CASES[name](ns.out)
    print(json.dumps({"cases": sorted(ns.cases), "out": str(ns.out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
