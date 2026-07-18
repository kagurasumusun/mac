#!/usr/bin/env python3
"""Generate self-authored source catalogs for the public CAR fixtures.

Every input (PNGs, colors, data blobs, Contents.json) is produced here from
scratch; nothing is derived from Apple or third-party artwork. Two modes:

  make_public_fixtures.py OUT_DIR
      Write the fixture *suite* (selfgen-rich.xcassets + selfgen-brand.xcassets
      + cases.json) so tools/run_apple_matrix.py can compile it with the real
      actool on a macOS host.

  make_public_fixtures.py --emit-solidstack-demo OUT.car
      Assemble a self-made layout-1018 SolidImageStack CAR directly with the
      clean-room writer (actool_linux.carwriter), for cross-validation by
      Apple assetutil.
"""
from __future__ import annotations

import argparse
import binascii
import json
import shutil
import struct
import zlib
from pathlib import Path

INFO = {"info": {"author": "xcode", "version": 1}}


# --------------------------------------------------------------------------
# Deterministic self-drawn PNG helpers (stdlib only).

def chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload)) + kind + payload
        + struct.pack(">I", binascii.crc32(kind + payload) & 0xFFFFFFFF)
    )


def _png(width: int, height: int, rows: bytes, color_type: int) -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows, 9))
        + chunk(b"IEND", b"")
    )


def png_rgba_gradient_seed(width: int, height: int, seed: int) -> bytes:
    """Non-uniform RGBA: gradient + seed-dependent solid corner patch."""
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            if (x - width // 4) ** 2 + (y - height // 4) ** 2 < (width // 6 + 1) ** 2:
                rows += bytes(((seed * 37 + 40) % 256, (seed * 91 + 90) % 256,
                               (seed * 53 + 150) % 256, 255))
            else:
                rows += bytes((x * 255 // max(width - 1, 1),
                               y * 255 // max(height - 1, 1),
                               (seed * 17 + (x + y) * 255 // max(width + height - 2, 1)) % 256,
                               192 + 63 * x // max(width - 1, 1)))
    return _png(width, height, bytes(rows), 6)


def png_gray_seed(width: int, height: int, gray: int) -> bytes:
    rows = b"\x00" + bytes((gray,)) * width
    return _png(width, height, rows * height, 0)


def png_gray16_seed(width: int, height: int, base: int) -> bytes:
    """16-bit gray PNG: vertical gradient around a seed base value."""
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        v = (base + y * (4096 // max(height, 1))) % 65536
        rows += struct.pack(">H", v) * width
    return _png16(width, height, bytes(rows), 0)


def png_ga16_seed(width: int, height: int, base: int) -> bytes:
    """16-bit gray+alpha PNG: gray gradient + alpha ramp."""
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            g = (base + (x + y) * 512) % 65536
            a = min(65535, 32768 + (x * 32768 // max(width - 1, 1)))
            rows += struct.pack(">HH", g, a)
    return _png16(width, height, bytes(rows), 4)


def _png16(width: int, height: int, rows: bytes, color_type: int) -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 16, color_type, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows, 9))
        + chunk(b"IEND", b"")
    )


def make_pdf(pt: float, seed: int) -> bytes:
    """Minimal self-authored one-page PDF: filled rect + bezier stroke."""
    def col(v: int) -> str:
        return f"{(v % 256) / 255:.3f}"
    content = (
        f"{col(seed*37)} {col(seed*91)} {col(seed*53)} rg\n"
        f"4 4 {pt-8:.0f} {pt-8:.0f} re f\n"
        f"{col(seed*11)} {col(seed*61)} {col(seed*29)} RG 3 w\n"
        f"8 8 m {pt/2:.0f} {pt-8:.0f} {pt-8:.0f} {pt/2:.0f} {pt-8:.0f} 8 c S\n"
    ).encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {pt:.0f} {pt:.0f}] /Contents 4 0 R >>".encode(),
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"endstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs)+1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n").encode()
    return bytes(out)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2))


# --------------------------------------------------------------------------
# selfgen-rich.xcassets — appearance colors, multi-scale images, data, app icon.

def build_selfgen_rich(root: Path) -> None:
    cat = root / "selfgen-rich.xcassets"

    def colorset(name: str, any_rgb: tuple[str, str, str], dark_rgb: tuple[str, str, str],
                 light_rgb: tuple[str, str, str] | None = None, space: str = "srgb") -> None:
        d = cat / name
        d.mkdir(parents=True, exist_ok=True)
        entries = [{
            "idiom": "universal",
            "color": {"color-space": space, "components": {
                "red": any_rgb[0], "green": any_rgb[1], "blue": any_rgb[2], "alpha": "1.0"}},
        }]
        if light_rgb:
            entries.append({
                "idiom": "universal",
                "appearances": [{"appearance": "luminosity", "value": "light"}],
                "color": {"color-space": space, "components": {
                    "red": light_rgb[0], "green": light_rgb[1], "blue": light_rgb[2], "alpha": "1.0"}},
            })
        entries.append({
            "idiom": "universal",
            "appearances": [{"appearance": "luminosity", "value": "dark"}],
            "color": {"color-space": space, "components": {
                "red": dark_rgb[0], "green": dark_rgb[1], "blue": dark_rgb[2], "alpha": "1.0"}},
        })
        write_json(d / "Contents.json", {"colors": entries, **INFO})

    colorset("SelfAccent.colorset", ("0.847", "0.204", "0.396"), ("0.955", "0.512", "0.626"),
             ("0.700", "0.120", "0.300"))
    colorset("SelfTint.colorset", ("0.150", "0.450", "0.800"), ("0.350", "0.650", "0.950"),
             None, "display-p3")

    d = cat / "SelfLogo.imageset"
    d.mkdir(parents=True, exist_ok=True)
    for scale, px in (("1x", 48), ("2x", 96), ("3x", 144)):
        (d / f"logo{scale}.png").write_bytes(png_rgba_gradient_seed(px, px, {"1x": 3, "2x": 5, "3x": 7}[scale]))
    write_json(d / "Contents.json", {"images": [
        {"idiom": "universal", "scale": s, "filename": f"logo{s}.png"} for s in ("1x", "2x", "3x")
    ], **INFO})

    d = cat / "SelfBanner.imageset"
    d.mkdir(parents=True, exist_ok=True)
    (d / "banner_any.png").write_bytes(png_rgba_gradient_seed(64, 24, 11))
    (d / "banner_dark.png").write_bytes(png_rgba_gradient_seed(64, 24, 23))
    write_json(d / "Contents.json", {"images": [
        {"idiom": "universal", "scale": "1x", "filename": "banner_any.png"},
        {"idiom": "universal", "scale": "1x",
         "appearances": [{"appearance": "luminosity", "value": "dark"}],
         "filename": "banner_dark.png"},
    ], **INFO})

    d = cat / "SelfGlyph.imageset"
    d.mkdir(parents=True, exist_ok=True)
    (d / "glyph.png").write_bytes(png_gray_seed(32, 32, 120))
    write_json(d / "Contents.json", {
        "images": [{"idiom": "universal", "scale": "1x", "filename": "glyph.png"}],
        "properties": {"template-rendering-intent": "template"}, **INFO})

    d = cat / "SelfBlob.dataset"
    d.mkdir(parents=True, exist_ok=True)
    (d / "payload.bin").write_bytes(b"actool-linux self-authored blob\n" * 8)
    (d / "payload_dark.bin").write_bytes(b"actool-linux self-authored dark blob\n" * 8)
    write_json(d / "Contents.json", {"data": [
        {"idiom": "universal", "filename": "payload.bin",
         "universal-type-identifier": "public.data"},
        {"idiom": "universal", "filename": "payload_dark.bin",
         "appearances": [{"appearance": "luminosity", "value": "dark"}],
         "universal-type-identifier": "public.data"},
    ], **INFO})

    d = cat / "SelfAppIcon.appiconset"
    d.mkdir(parents=True, exist_ok=True)
    images = []
    for pt in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            px = pt * scale
            fn = f"icon_{pt}_{scale}x.png"
            (d / fn).write_bytes(png_rgba_gradient_seed(px, px, pt ^ scale))
            images.append({"idiom": "mac", "size": f"{pt}x{pt}",
                           "scale": f"{scale}x", "filename": fn})
    write_json(d / "Contents.json", {"images": images, **INFO})

    write_json(cat / "Contents.json", INFO)


# --------------------------------------------------------------------------
# selfgen-brand.xcassets — tv brandassets with two parallax imagestacks.

def _make_stack(brand: Path, name: str, layers: list[tuple[str, int, int, int]]) -> None:
    stack = brand / name
    write_json(stack / "Contents.json",
               {"layers": [{"filename": f"{ln}.imagestacklayer"} for ln, _, _, _ in layers], **INFO})
    for layer_name, w, h, seed in layers:
        image = stack / f"{layer_name}.imagestacklayer" / "Content.imageset"
        image.mkdir(parents=True, exist_ok=True)
        (image / "content.png").write_bytes(png_rgba_gradient_seed(w, h, seed))
        write_json(image / "Contents.json",
                   {"images": [{"idiom": "tv", "scale": "1x", "filename": "content.png"}], **INFO})
        write_json(stack / f"{layer_name}.imagestacklayer" / "Contents.json", INFO)


def build_selfgen_brand(root: Path) -> None:
    cat = root / "selfgen-brand.xcassets"
    brand = cat / "Icon.brandassets"
    write_json(brand / "Contents.json", {"assets": [
        {"size": "1280x768", "idiom": "tv", "filename": "App Icon - Large.imagestack",
         "role": "primary-app-icon"},
        {"size": "400x240", "idiom": "tv", "filename": "App Icon - Small.imagestack",
         "role": "primary-app-icon"},
        {"size": "1920x720", "idiom": "tv", "filename": "Top Shelf Image.imageset",
         "role": "top-shelf-image"},
    ], **INFO})
    _make_stack(brand, "App Icon - Large.imagestack", [
        ("Back", 1280, 768, 31), ("Middle", 1280, 768, 41), ("Front", 1280, 768, 51)])
    _make_stack(brand, "App Icon - Small.imagestack", [
        ("Back", 400, 240, 61), ("Front", 400, 240, 71)])
    d = brand / "Top Shelf Image.imageset"
    d.mkdir(parents=True, exist_ok=True)
    (d / "shelf.png").write_bytes(png_rgba_gradient_seed(1920, 720, 81))
    write_json(d / "Contents.json",
               {"images": [{"idiom": "tv", "scale": "1x", "filename": "shelf.png"}], **INFO})
    write_json(cat / "Contents.json", INFO)


# --------------------------------------------------------------------------
# selfgen-vec.xcassets — special payloads: PDF vector, 16-bit PNGs, JPEG,
# high-contrast color, extended sRGB, typed datasets.

def build_selfgen_vec(root: Path) -> None:
    cat = root / "selfgen-vec.xcassets"

    d = cat / "SelfVector.imageset"
    d.mkdir(parents=True, exist_ok=True)
    (d / "vector.pdf").write_bytes(make_pdf(64.0, 7))
    write_json(d / "Contents.json", {
        "images": [{"idiom": "universal", "filename": "vector.pdf"}],
        "properties": {"preserves-vector-representation": True}, **INFO})

    d = cat / "SelfGA16.imageset"
    d.mkdir(parents=True, exist_ok=True)
    (d / "ga16.png").write_bytes(png_ga16_seed(24, 24, 5000))
    write_json(d / "Contents.json",
               {"images": [{"idiom": "universal", "scale": "1x", "filename": "ga16.png"}], **INFO})

    d = cat / "SelfGray16.imageset"
    d.mkdir(parents=True, exist_ok=True)
    (d / "gray16.png").write_bytes(png_gray16_seed(24, 24, 40000))
    write_json(d / "Contents.json",
               {"images": [{"idiom": "universal", "scale": "1x", "filename": "gray16.png"}], **INFO})

    jpeg = root / "_jpeg_work"
    try:
        from PIL import Image
        img = Image.new("RGB", (32, 32))
        px = img.load()
        for yy in range(32):
            for xx in range(32):
                px[xx, yy] = (xx * 255 // 31, yy * 255 // 31, (xx + yy) * 255 // 62)
        jpeg.mkdir(parents=True, exist_ok=True)
        img.save(jpeg / "photo.jpg", quality=88)
        d = cat / "SelfPhoto.imageset"
        d.mkdir(parents=True, exist_ok=True)
        (d / "photo.jpg").write_bytes((jpeg / "photo.jpg").read_bytes())
        write_json(d / "Contents.json",
                   {"images": [{"idiom": "universal", "scale": "1x", "filename": "photo.jpg"}], **INFO})
    except ImportError:
        pass  # JPEG case skipped when Pillow is unavailable

    d = cat / "SelfHighContrastColor.colorset"
    d.mkdir(parents=True, exist_ok=True)
    write_json(d / "Contents.json", {"colors": [
        {"idiom": "universal", "color": {"color-space": "srgb", "components": {
            "red": "0.55", "green": "0.42", "blue": "0.80", "alpha": "1.0"}}},
        {"idiom": "universal",
         "appearances": [{"appearance": "contrast", "value": "high"}],
         "color": {"color-space": "srgb", "components": {
             "red": "0.80", "green": "0.70", "blue": "1.00", "alpha": "1.0"}}},
    ], **INFO})

    d = cat / "SelfTranslucentColor.colorset"
    d.mkdir(parents=True, exist_ok=True)
    write_json(d / "Contents.json", {"colors": [
        {"idiom": "universal", "color": {"color-space": "display-p3", "components": {
            "red": "1.0", "green": "0.82", "blue": "0.1", "alpha": "0.5"}}},
    ], **INFO})

    for name, fn, data, uti in (
            ("SelfJsonBlob.dataset", "blob.json", b'{"self": "authored", "n": 42}\n', "public.json"),
            ("SelfTextBlob.dataset", "memo.txt", b"actool-linux self-authored text\n", "public.text")):
        d = cat / name
        d.mkdir(parents=True, exist_ok=True)
        (d / fn).write_bytes(data)
        write_json(d / "Contents.json", {"data": [
            {"idiom": "universal", "filename": fn, "universal-type-identifier": uti}], **INFO})

    write_json(cat / "Contents.json", INFO)


# --------------------------------------------------------------------------
# selfgen-ios.xcassets — iphone/ipad idioms, dark appearances, localization.

def build_selfgen_ios(root: Path) -> None:
    cat = root / "selfgen-ios.xcassets"

    for idiom, scales in (("iphone", ("1x", "2x", "3x")), ("ipad", ("1x", "2x"))):
        d = cat / f"SelfIcon_{idiom}.imageset"
        d.mkdir(parents=True, exist_ok=True)
        images = []
        for scale in scales:
            px = {"1x": 20, "2x": 40, "3x": 60}[scale]
            fn = f"icon_{idiom}{scale}.png"
            (d / fn).write_bytes(png_rgba_gradient_seed(px, px, px ^ len(idiom)))
            images.append({"idiom": idiom, "scale": scale, "filename": fn})
        write_json(d / "Contents.json", {"images": images, **INFO})

    d = cat / "SelfMode.imageset"
    d.mkdir(parents=True, exist_ok=True)
    (d / "any.png").write_bytes(png_rgba_gradient_seed(24, 24, 13))
    (d / "dark.png").write_bytes(png_rgba_gradient_seed(24, 24, 29))
    write_json(d / "Contents.json", {"images": [
        {"idiom": "universal", "scale": "1x", "filename": "any.png"},
        {"idiom": "universal", "scale": "1x",
         "appearances": [{"appearance": "luminosity", "value": "dark"}], "filename": "dark.png"},
    ], **INFO})

    d = cat / "SelfHello.imageset"
    d.mkdir(parents=True, exist_ok=True)
    (d / "base.png").write_bytes(png_rgba_gradient_seed(24, 24, 37))
    (d / "ja.png").write_bytes(png_rgba_gradient_seed(24, 24, 43))
    write_json(d / "Contents.json", {"images": [
        {"idiom": "universal", "scale": "1x", "filename": "base.png"},
        {"idiom": "universal", "scale": "1x", "locale": "ja", "filename": "ja.png"},
    ], **INFO})

    d = cat / "SelfP3Color.colorset"
    d.mkdir(parents=True, exist_ok=True)
    write_json(d / "Contents.json", {"colors": [
        {"idiom": "universal", "color": {"color-space": "display-p3", "components": {
            "red": "1.0", "green": "0.25", "blue": "0.35", "alpha": "1.0"}}},
        {"idiom": "universal",
         "appearances": [{"appearance": "luminosity", "value": "dark"}],
         "color": {"color-space": "display-p3", "components": {
             "red": "1.0", "green": "0.55", "blue": "0.60", "alpha": "1.0"}}},
    ], **INFO})

    write_json(cat / "Contents.json", INFO)


CASES = {
    "selfgen-rich": build_selfgen_rich,
    "selfgen-brand": build_selfgen_brand,
    "selfgen-vec": build_selfgen_vec,
    "selfgen-ios": build_selfgen_ios,
}

ARGS = {
    "selfgen-rich": {"args": ["--platform", "macosx", "--minimum-deployment-target", "13.0",
                              "--app-icon", "SelfAppIcon"]},
    "selfgen-brand": {"args": ["--platform", "appletvos", "--minimum-deployment-target", "15.0",
                               "--app-icon", "Icon", "--target-device", "tv"]},
    "selfgen-vec": {"args": ["--platform", "macosx", "--minimum-deployment-target", "13.0"]},
    "selfgen-ios": {"args": ["--platform", "iphoneos", "--minimum-deployment-target", "15.0"]},
}


def emit_solidstack_demo(out: Path) -> None:
    """Self-made layout-1018 SolidImageStack CAR via the clean-room writer."""
    from actool_linux.carwriter import build_solid_image_stack_aggregate_car

    layers = [
        ("back", png_rgba_gradient_seed(64, 64, 91)),
        ("middle", png_rgba_gradient_seed(64, 64, 97)),
        ("front", png_rgba_gradient_seed(64, 64, 103)),
    ]
    data = build_solid_image_stack_aggregate_car("SelfSolidStack", layers)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    print(json.dumps({"out": str(out), "bytes": len(data)}))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path, nargs="?")
    ap.add_argument("--emit-solidstack-demo", type=Path)
    ns = ap.parse_args()
    if ns.emit_solidstack_demo:
        emit_solidstack_demo(ns.emit_solidstack_demo)
        return 0
    if ns.out is None:
        ap.error("OUT_DIR is required in suite mode")
    shutil.rmtree(ns.out, ignore_errors=True)
    ns.out.mkdir(parents=True, exist_ok=True)
    for fn in CASES.values():
        fn(ns.out)
    (ns.out / "cases.json").write_text(json.dumps(ARGS, indent=2) + "\n")
    print(json.dumps({"cases": sorted(CASES), "out": str(ns.out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
