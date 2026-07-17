#!/usr/bin/env python3
"""Generate a large packed-atlas geometry sweep suite (xcassets + cases.json).

Each case packs 4..12 same-class images of mixed pixel sizes so Apple actool
emits one packed atlas page; comparing LINK geometry against our packer
validates the probed rules on shapes outside the m/n/probe5 corpus.

Usage: make_atlas_sweep.py OUTDIR
"""
from __future__ import annotations

import json
import struct
import sys
import zlib
from pathlib import Path

SIZES = [8, 12, 16, 17, 24, 32, 48, 64]

# (case, [(w, h), ...]) — deterministic mixes chosen to stress shelves,
# holes, columns and threshold boundaries.
CASES = [
    ("s5_mix_a", [(32, 32), (24, 24), (16, 16), (16, 16), (8, 8)]),
    ("s5_mix_b", [(48, 48), (32, 32), (17, 17), (16, 16), (12, 12)]),
    ("s6_mix_a", [(64, 64), (32, 32), (24, 24), (17, 17), (16, 16), (8, 8)]),
    ("s6_mix_b", [(48, 48), (48, 48), (24, 24), (24, 24), (16, 16), (8, 8)]),
    ("s8_mix_a", [(64, 64), (48, 48), (32, 32), (24, 24), (17, 17), (16, 16), (8, 8), (8, 8)]),
    ("s8_mix_b", [(32, 32), (32, 32), (32, 32), (24, 24), (24, 24), (16, 16), (16, 16), (8, 8)]),
    ("s10_mix", [(64, 64), (48, 48), (32, 32), (32, 32), (24, 24), (24, 24), (16, 16), (16, 16), (8, 8), (8, 8)]),
    ("s12_p3a_like", [(64, 64), (48, 48), (32, 32), (32, 32), (32, 32), (24, 24), (24, 24), (17, 17), (16, 16), (16, 16), (8, 8), (8, 8)]),
    ("s5_tall", [(16, 64), (16, 32), (8, 24), (8, 16), (8, 8)]),
    ("s5_wide", [(64, 16), (32, 16), (24, 8), (16, 8), (8, 8)]),
    ("s6_tallmix", [(32, 64), (16, 48), (24, 17), (16, 16), (24, 8), (8, 8)]),
    ("s7_stairs", [(64, 64), (48, 48), (32, 32), (24, 24), (16, 16), (12, 12), (8, 8)]),
    ("s4_deep_hole", [(64, 64), (48, 16), (16, 16), (16, 16)]),
    ("s5_deep_hole", [(64, 64), (48, 16), (16, 16), (16, 16), (8, 8)]),
    ("s6_deep_hole", [(64, 64), (48, 24), (24, 24), (16, 16), (16, 16), (8, 8)]),
    ("s8_uniform24", [(24, 24)] * 8),
    ("s9_uniform16", [(16, 16)] * 9),
    ("s5_uniform32", [(32, 32)] * 5),
    ("s7_uniform17", [(17, 17)] * 7),
    ("s6_columnish", [(64, 64), (24, 24), (24, 24), (17, 17), (16, 16), (8, 8)]),
    ("s7_columnish", [(64, 64), (48, 48), (24, 24), (24, 24), (17, 17), (16, 16), (8, 8)]),
    ("s8_columnish", [(64, 64), (48, 48), (24, 24), (24, 24), (17, 17), (16, 16), (8, 8), (8, 8)]),
    ("s5_oddmix", [(33, 21), (21, 33), (15, 9), (9, 15), (7, 7)]),
    ("s6_oddmix", [(31, 31), (29, 13), (13, 29), (17, 17), (9, 9), (5, 5)]),
    ("s4_ratio", [(64, 64), (48, 24), (24, 12), (12, 6)]),
    ("s5_ratio", [(64, 64), (48, 24), (24, 12), (12, 6), (6, 3)]),
    ("s8_two_tiers", [(48, 48), (48, 48), (16, 16), (16, 16), (16, 16), (16, 16), (8, 8), (8, 8)]),
    ("s8_three_tiers", [(64, 64), (32, 32), (32, 32), (16, 16), (16, 16), (16, 16), (8, 8), (8, 8)]),
    ("s10_small_tail", [(64, 64), (48, 48), (8, 8), (8, 8), (8, 8), (8, 8), (8, 8), (8, 8), (8, 8), (8, 8)]),
    ("s10_units", [(8, 8)] * 10),
    ("s12_units", [(8, 8)] * 12),
    ("s16_units", [(8, 8)] * 16),
    ("s5_dimix", [(48, 32), (32, 48), (24, 16), (16, 24), (12, 12)]),
    ("s6_dimix", [(48, 32), (32, 48), (17, 24), (24, 17), (16, 16), (8, 8)]),
    ("s4_justcol", [(64, 64), (24, 24), (16, 16), (8, 8)]),
    ("s5_justcol", [(64, 64), (24, 24), (24, 24), (16, 16), (8, 8)]),
    ("s6_wrap", [(48, 48), (48, 48), (48, 48), (24, 24), (24, 24), (24, 24)]),
]


def _png(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    def chunk(t: bytes, d: bytes) -> bytes:
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    row = b"\x00" + bytes(rgb + (255,)) * width
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(row * height, 9)) + chunk(b"IEND", b"")


def main() -> int:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    cases = {}
    for case, rects in CASES:
        assets = out / f"{case}.xcassets"
        for i, (w, h) in enumerate(rects):
            rgb = ((37 * i + 90) % 256, (91 * i + 40) % 256, (53 * i + 17) % 256)
            imageset = assets / f"img{i:02d}.imageset"
            imageset.mkdir(parents=True, exist_ok=True)
            (imageset / "s.png").write_bytes(_png(w, h, rgb))
            (imageset / "Contents.json").write_text(json.dumps({
                "images": [{"filename": "s.png", "idiom": "universal", "scale": "1x"}],
                "info": {"author": "xcode", "version": 1},
            }))
        (assets / "Contents.json").write_text(json.dumps({"info": {"author": "xcode", "version": 1}}))
        cases[case] = {"args": ["--platform", "macosx", "--target-device", "mac"]}
    (out / "cases.json").write_text(json.dumps(cases, indent=2))
    print(f"{len(cases)} cases -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
