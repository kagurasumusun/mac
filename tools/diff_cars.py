#!/usr/bin/env python3
"""Structural diff of two CAR files using the local clean-room parser.

Focus: semantic parity with Apple's actool output.
- facets (name -> attributes)
- renditions (key tuple -> name, layout, pixel format, size, scale, flags,
  TLV tag+length list, payload codec/length)
- header/storage metadata that matters to consumers

Volatile fields (version strings, timestamps, identifiers inside header) are
reported separately and not treated as semantic mismatches unless
--strict-header is given.

Usage: diff_cars.py APPLE.car OURS.car [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from actool_linux.carinfo import inspect  # noqa: E402


def semantic_view(info: dict) -> dict:
    facets = {}
    for f in info["facets"]:
        attrs = dict(f["attributes"])
        facets[f["name"]] = attrs
    rends = []
    for r in info["renditions"]:
        key = tuple(sorted(r["key"].items()))
        tlvs = [(t["tag"], t.get("length", t.get("len"))) for t in r["tlvs"]]
        payload = r.get("decoded_payload") or {}
        rends.append({
            "key": key,
            "name": r["name"],
            "size": (r["width"], r["height"]),
            "scale": r["scale"],
            "pixel_format": r["pixel_format"],
            "layout": r["layout"],
            "flags": r["flags"],
            "tlvs": tlvs,
            "payload_length": r["payload_length"],
            "payload_codec": payload.get("compression_type"),
        })
    return {
        "header": {
            "core_ui_version": info["car_header"]["core_ui_version"],
            "storage_version": info["car_header"]["storage_version"],
            "schema_version": info["car_header"]["schema_version"],
            "rendition_count": info["car_header"]["rendition_count"],
            "color_space_id": info["car_header"]["color_space_id"],
            "key_semantics": info["car_header"]["key_semantics"],
        },
        "extended_metadata": {
            k: v for k, v in (info.get("extended_metadata") or {}).items()
        },
        "key_format": info["key_format"],
        "facets": facets,
        "renditions": sorted(rends, key=lambda r: (r["key"], r["name"])),
    }


def diff(a, b, path="") -> list[str]:
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(f"{path}/{k}: only in ours ({b[k]!r})")
            elif k not in b:
                out.append(f"{path}/{k}: only in apple ({a[k]!r})")
            else:
                out.extend(diff(a[k], b[k], f"{path}/{k}"))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{path}: list length apple={len(a)} ours={len(b)}")
        for i, (x, y) in enumerate(zip(a, b)):
            out.extend(diff(x, y, f"{path}[{i}]"))
    else:
        if a != b:
            out.append(f"{path}: apple={a!r} ours={b!r}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("apple", type=Path)
    ap.add_argument("ours", type=Path)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--ignore-identifiers", action="store_true",
                    help="ignore identifier attribute differences (hash not yet matched)")
    ns = ap.parse_args()

    apple = semantic_view(inspect(ns.apple))
    ours = semantic_view(inspect(ns.ours))
    problems = diff(apple, ours)

    if ns.ignore_identifiers:
        problems = [p for p in problems if "Identifier" not in p]

    volatile = {
        "apple_header_version_string": inspect(ns.apple)["car_header"]["version_string"],
        "ours_header_version_string": inspect(ns.ours)["car_header"]["version_string"],
        "apple_main_version": inspect(ns.apple)["car_header"]["main_version"],
        "ours_main_version": inspect(ns.ours)["car_header"]["main_version"],
        "apple_authoring_tool": (inspect(ns.apple).get("extended_metadata") or {}).get("authoring_tool"),
        "ours_authoring_tool": (inspect(ns.ours).get("extended_metadata") or {}).get("authoring_tool"),
    }
    report = {
        "apple": str(ns.apple),
        "ours": str(ns.ours),
        "mismatch_count": len(problems),
        "mismatches": problems,
        "volatile": volatile,
    }
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if ns.json:
        ns.json.write_text(text + "\n")
    print(text)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
