#!/usr/bin/env python3
"""Semantic assetutil matrix: compare Apple-oracle CARs vs ours, key-wise.

Runs ON a macOS host with Xcode. For every case directory containing an
Assets.car under APPLE_DIR and OURS_DIR, runs `xcrun assetutil --info`, then
multiset-compares entries keyed by (Name, RenditionName, Scale, Appearance,
Idiom, AssetType) with values from the remaining observable fields. This is
the "Apple consumer as judge" parity check used by the probe3-6 campaigns.

Usage: assetutil_semantic_matrix.py APPLE_DIR OURS_DIR [--json OUT]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

KEYS = ("Name", "RenditionName", "Scale", "Appearance", "Idiom", "AssetType")
VALS = ("AssetType", "BitsPerComponent", "ColorModel", "Colorspace", "Compression",
        "Encoding", "Opaque", "PixelHeight", "PixelWidth", "Template Mode")


def assetutil_entries(car: Path) -> list[tuple]:
    proc = subprocess.run(["xcrun", "assetutil", "--info", str(car)],
                          text=True, capture_output=True)
    if proc.returncode:
        raise RuntimeError(f"assetutil failed for {car}: {proc.stderr[:400]}")
    rows = json.loads(proc.stdout)
    out = []
    for r in rows:
        if not isinstance(r, dict) or "AssetType" not in r:
            continue
        out.append((tuple(r.get(k) for k in KEYS), tuple(r.get(v) for v in VALS)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("apple_dir", type=Path)
    ap.add_argument("ours_dir", type=Path)
    ap.add_argument("--json", type=Path, default=None)
    ns = ap.parse_args()

    results = {}
    for apple_car in sorted(ns.apple_dir.glob("*/Assets.car")):
        case = apple_car.parent.name
        ours_car = ns.ours_dir / case / "Assets.car"
        if not ours_car.exists():
            results[case] = {"status": "ours-car-missing"}
            continue
        a = Counter(assetutil_entries(apple_car))
        o = Counter(assetutil_entries(ours_car))
        only_a = [list(e) for e in (a - o).elements()]
        only_o = [list(e) for e in (o - a).elements()]
        common = sum((a & o).values())
        results[case] = {
            "status": "match" if a == o else "differ",
            "common": common, "apple_total": sum(a.values()), "ours_total": sum(o.values()),
            "only_apple": only_a[:20], "only_ours": only_o[:20],
        }
    full = sum(1 for r in results.values() if r["status"] == "match")
    summary = {"cases": len(results), "full_matches": full, "results": results}
    text = json.dumps(summary, indent=2)
    if ns.json:
        ns.json.write_text(text)
    print(f"semantic matrix: {full}/{len(results)} full matches")
    mismatched = [c for c, r in results.items() if r["status"] != "match"]
    if mismatched:
        print("differing cases:", ", ".join(mismatched))
    return 0


if __name__ == "__main__":
    sys.exit(main())
