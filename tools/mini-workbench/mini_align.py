#!/usr/bin/env python3
"""Align Apple multi-swatch mini token streams with ground-truth RLE runs.

Builds exact unit bitmaps (palette indices for v4 color atlases; raw bytes
for GA v3 atlases) from LINK rect placements, palette order (swatches),
and the source PNG colours. Prints runs vs token stream for eyeballing.
"""
from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, "/home/user/mac-repo/src")
from actool_linux.car import CARFile  # noqa: E402


def read_png_rgba(path: Path):
    """Minimal RGBA/RGB/GA PNG reader for our probe sources."""
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos = 8
    w = h = ctype = None
    idat = bytearray()
    while pos < len(data):
        ln = struct.unpack_from(">I", data, pos)[0]
        tag = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + ln]
        if tag == b"IHDR":
            w, h, _, ctype = struct.unpack_from(">IIBB", chunk, 0)
        elif tag == b"IDAT":
            idat += chunk
        pos += 12 + ln
    raw = zlib.decompress(bytes(idat))
    ch = {6: 4, 2: 3, 4: 2}.get(ctype)
    stride = w * ch + 1
    px = bytearray()
    for y in range(h):
        f = raw[y * stride]
        assert f == 0, "probe sources are filter-0"
        px += raw[y * stride + 1:(y + 1) * stride]
    return w, h, ch, bytes(px)


def load_atlas_case(carpath: str, srcdir: Path | None, ga: bool):
    car = CARFile.from_path(carpath)
    atlas = [r for r in car.renditions if r.csi.name.startswith("ZZZZ")][0]
    d = atlas.csi.rendition_data[32:]
    ver = d[4]
    W, H = struct.unpack_from("<HH", d, 8)
    pal = None
    if ver == 4:
        count, _ = struct.unpack_from("<HH", d, 12)
        pal = [d[16 + 4 * i:20 + 4 * i] for i in range(count)]
        off = 16 + 4 * count
        sl, = struct.unpack_from("<I", d, off)
        stream = d[off + 4:off + 4 + sl]
    else:
        sl, = struct.unpack_from("<I", d, 12)
        stream = d[16:16 + sl]
    rends = []
    for r in car.renditions:
        if r.csi.name.startswith("ZZZZ"):
            continue
        t = [x for x in r.csi.tlvs if x.tag == 1010][0].value
        _, x, y, w, h = struct.unpack_from("<5I", t, 4)
        rends.append(dict(name=r.csi.name, x=x, y=y, w=w, h=h))
    return W, H, pal, ver, stream, rends


def rle(units):
    runs = []
    last, n = units[0], 1
    for u in units[1:]:
        if u == last:
            n += 1
        else:
            runs.append((last, n))
            last, n = u, 1
    runs.append((last, n))
    return runs


def build_units(W, H, rends, values, ga):
    units = [0] * (W * H * (2 if ga else 1))
    for (x, y, w, h, val) in values:
        for dy in range(h):
            for dx in range(w):
                p = (y + dy) * W + (x + dx)
                if ga:
                    units[2 * p] = val[0]
                    units[2 * p + 1] = val[1]
                else:
                    units[p] = val
    return units


def main():
    print("# m-series solved placements & palette assignments")
    m_cases = [
        ("m1", "/home/user/work/atlasprobe-apple-out/m1_pair2x2/Assets.car",
         # rect values by rendition name -> palette index
         {"A.png": 2, "B.png": 1}, False),
        ("m2", "/home/user/work/atlasprobe-apple-out/m2_pair4x2/Assets.car",
         {"A.png": 2, "B.png": 1}, False),
        ("m5", "/home/user/work/atlasprobe-apple-out/m5_trio/Assets.car",
         {"A.png": 3, "C.png": 1, "B.png": 2}, False),
        ("m7", "/home/user/work/atlasprobe-apple-out/m7_row/Assets.car",
         {"A.png": 2, "B.png": 1}, False),
        ("m8", "/home/user/work/atlasprobe-apple-out/m8_big/Assets.car",
         {"A.png": 3, "B.png": 1, "C.png": 2}, False),
        ("m3", "/home/user/work/atlasprobe-apple-out/m3_ga/Assets.car",
         {"B.png": (0x40, 0xFF), "A.png": (0x80, 0xFF)}, True),
        ("m6", "/home/user/work/atlasprobe-apple-out/m6_ga_t/Assets.car",
         {"A.png": (0x66, 0xCC), "B.png": (0x20, 0x80)}, True),
    ]
    for name, carpath, colormap, ga in m_cases:
        W, H, pal, ver, stream, rends = load_atlas_case(carpath, None, ga)
        values = [(r["x"], r["y"], r["w"], r["h"], colormap[r["name"]]) for r in rends]
        units = build_units(W, H, rends, values, ga)
        print(f"== {name} v{ver} {W}x{H} pal={[p.hex() for p in pal] if pal else None}")
        print("   runs:", rle(units))
        print("   toks:", " ".join(f"{b:02x}" for b in stream))


if __name__ == "__main__":
    main()
