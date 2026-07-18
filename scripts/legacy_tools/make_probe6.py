#!/usr/bin/env python3
"""Probe suite #6: gray-RGB(A) normalization + GA grammar boundaries.

Open questions this suite answers (single-image catalogs keep every rendition
unpacked, exposing the raw layout-12 grammar Apple picks):

1. Standalone RGB(A) sources with r == g == b everywhere: does Apple store
   them as GA8 (like type-0/type-4 gray) or BGRA? (Our writer re-encodes;
   this is the last unprobed pixel-format behavior — packed cases verified.)
2. GA (gray+alpha) *non-uniform* sources: grammar v1 or v2?
3. GA uniform boundary between v3-mini and v3-LZFSE (known: 32x32=2048 B
   pixel data -> mini, 64x64=8192 B -> LZFSE; sweep 40/48/56 px).
4. Two-color non-uniform color images (small and large): v2 or v4?

- p6a_* -> iphoneos, p6b_* -> macosx (platform grammar cross-check)
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


def png_ga_custom(w: int, h: int, pxfn) -> bytes:
    raw = b"".join(b"\x00" + b"".join(bytes(pxfn(x, y)) for x in range(w)) for y in range(h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 4, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def png_ga(w: int, h: int, g: int, a: int) -> bytes:
    return png_ga_custom(w, h, lambda x, y: (g, a))


def png_checker(w: int, h: int, c0, c1, cell: int = 1) -> bytes:
    def px(x, y):
        return c0 if ((x // cell) + (y // cell)) % 2 == 0 else c1
    raw = b"".join(b"\x00" + b"".join(bytes(px(x, y)) for x in range(w)) for y in range(h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
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
    (cat / "Contents.json").write_text(json.dumps(INFO))
    return cat


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ns = ap.parse_args()
    cases: dict[str, dict] = {}

    for plat in ("a", "b"):
        # 1. standalone gray-representable RGB(A) -> GA8 or BGRA?
        c = catalog(ns.out, f"p6{plat}_solo_gray_rgb")
        imageset(c, "Solo", png_rgb(64, 64, (200, 200, 200)))
        c = catalog(ns.out, f"p6{plat}_solo_gray_rgba_t")
        imageset(c, "Solo", png_rgba(64, 64, (9, 9, 9, 128)))
        c = catalog(ns.out, f"p6{plat}_solo_gray_rgba_o")
        imageset(c, "Solo", png_rgba(64, 64, (77, 77, 77, 255)))
        # 2. GA gradient grammars
        c = catalog(ns.out, f"p6{plat}_ga_vgrad")
        imageset(c, "Solo", png_ga_custom(16, 16, lambda x, y: (x * 16, 255)))
        c = catalog(ns.out, f"p6{plat}_ga_agrad")
        imageset(c, "Solo", png_ga_custom(16, 16, lambda x, y: (90, 16 + x * 8)))
        # 3. GA uniform v3-mini/LZFSE boundary refinement
        for size in (40, 48, 56):
            c = catalog(ns.out, f"p6{plat}_ga{size:03d}")
            imageset(c, "Solo", png_ga(size, size, 77, 255))
        # 4. two-color checkerboards: v4 multi-swatch for ordinary images?
        c = catalog(ns.out, f"p6{plat}_chk04")
        imageset(c, "Solo", png_checker(4, 4, (255, 0, 0, 255), (0, 0, 255, 255)))
        c = catalog(ns.out, f"p6{plat}_chk64")
        imageset(c, "Solo", png_checker(64, 64, (255, 0, 0, 255), (0, 0, 255, 255), cell=8))
        # 5. uniform RGB (type 2) large: grammar + pixel format
        c = catalog(ns.out, f"p6{plat}_rgb64")
        imageset(c, "Solo", png_rgb(64, 64, (11, 99, 200)))
        # 6. pair of gray RGB sources -> do they pack into the gray class?
        c = catalog(ns.out, f"p6{plat}_pair_gray_rgb")
        imageset(c, "W1", png_rgb(40, 40, (200, 200, 200)))
        imageset(c, "W2", png_rgb(24, 24, (128, 128, 128)))

    for case in ns.out.glob("*.xcassets"):
        platform = "iphoneos" if case.stem.startswith("p6a") else "macosx"
        target = "15.0" if platform == "iphoneos" else "13.0"
        cases[case.stem] = {"args": ["--platform", platform, "--minimum-deployment-target", target]}
    (ns.out / "cases.json").write_text(json.dumps(cases, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
