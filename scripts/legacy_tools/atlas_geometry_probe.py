#!/usr/bin/env python3
"""Extract packed-atlas geometry (TLV1010 atlas-link records) from .car files.

For every rendition carrying a TLV 1010 atlas link this prints the rect
placement ``(x, y): wxh`` using absolute pixel coordinates that include the
2px top-left content margin, plus the trailing attribute token pairs
(page / appearance etc.).

Layout rules probed on Apple actool (Xcode 26.5, 2026-07) with the m1..m8 /
n1..n8 probe suites:
  * insertion order is the reverse of the RENDITIONS tree order,
  * first-fit left packing, shelf height = height of the first rect in a row,
  * 2px gutter between packed rects, right margin always 2px,
  * the atlas W picking rule and the palette order remain unsolved
    (resistant to hypothesis testing; treated as a private heuristic).

Usage: atlas_geometry_probe.py FILE.car [FILE.car ...]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from actool_linux.carinfo import inspect  # noqa: E402


def probe(path: Path) -> list[tuple[str, str, str, str]]:
    rows = []
    for r in inspect(path)["renditions"]:
        for tlv in r["tlvs"]:
            link = tlv.get("atlas_link")
            if not link:
                continue
            body = f"({link['x']},{link['y']}): {link['width']}x{link['height']}"
            tail = " ".join(f"{t['attribute']}:{t['value']}" for t in link["tokens"])
            rows.append((r["name"], f"x{r['scale']}", body, tail))
    return rows


def main(argv: list[str]) -> int:
    rc = 0
    for arg in argv[1:]:
        path = Path(arg)
        print(f"== {path.name} ==")
        try:
            for name, scale, body, tail in probe(path):
                print(f"  {name:<30} [{scale}] {body}  [{tail}]")
        except Exception as e:  # noqa: BLE001
            print(f"  (error: {e})")
            rc = 1
    return rc


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    sys.exit(main(sys.argv))
