#!/usr/bin/env python3
"""Structural diff of two CAR files using the local clean-room parser.

Semantic comparison robust against Apple-vs-ours identifier hashing:
renditions are keyed by (facet name resolved through each file's FACETKEYS,
part, scale, idiom, appearance, subtype, localization, element) rather than
by raw identifier values. Remaining identifier *values* are compared only via
the facet table and cross-reference consistency.

Usage: diff_cars.py APPLE.car OURS.car [--json out.json] [--strict-identifiers]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from actool_linux.carinfo import inspect  # noqa: E402

SEMANTIC_KEY_FIELDS = (
    "kCRThemePartName", "kCRThemeScaleName", "kCRThemeIdiomName",
    "kCRThemeAppearanceName", "kCRThemeSubtypeName", "kCRThemeLocalizationName",
    "kCRThemeElementName", "kCRThemeLayerName", "kCRThemeDimension1Name",
    "kCRThemeDimension2Name", "kCRThemeSizeName", "kCRThemeDirectionName",
)


def _facet_names(info: dict) -> dict[int, str]:
    out = {}
    for f in info["facets"]:
        attrs = f["attributes"]
        ident = attrs.get("kCRThemeIdentifierName")
        if ident is not None:
            out[ident] = f["name"]
    return out


def semantic_view(info: dict) -> dict:
    names_by_id = _facet_names(info)
    rends = {}
    for r in info["renditions"]:
        ident = r["key"].get("kCRThemeIdentifierName", 0)
        facet_name = names_by_id.get(ident)
        if facet_name is None:
            # Anonymous/internal rendition (packed assets, aggregates that
            # override identifiers): fall back to the rendition's own name.
            facet_name = r["name"]
        sem_key = (facet_name,) + tuple(r["key"].get(f, 0) for f in SEMANTIC_KEY_FIELDS)
        tlvs = [(t["tag"], t.get("length", t.get("len"))) for t in r["tlvs"]]
        payload = r.get("decoded_payload") or {}
        entry = {
            "facet_name": facet_name,
            "identifier": ident,
            "name": r["name"],
            "size": (r["width"], r["height"]),
            "scale": r["scale"],
            "pixel_format": r["pixel_format"],
            "layout": r["layout"],
            "flags": r["flags"],
            "tlvs": tlvs,
            "payload_length": r["payload_length"],
            "payload_codec": payload.get("compression_type"),
            "payload_version": payload.get("wrapper_version"),
        }
        if sem_key in rends:
            rends[sem_key] = {"DUPLICATE": [rends[sem_key], entry]}
        else:
            rends[sem_key] = entry
    return {
        "header": {
            "core_ui_version": info["car_header"]["core_ui_version"],
            "storage_version": info["car_header"]["storage_version"],
            "schema_version": info["car_header"]["schema_version"],
            "rendition_count": info["car_header"]["rendition_count"],
        },
        "key_format": info["key_format"],
        "facets": {f["name"]: f["attributes"] for f in info["facets"]},
        "renditions": rends,
        "extended_metadata": info.get("extended_metadata") or {},
    }


def diff(a, b, path="", *, strict_identifiers=False) -> list[str]:
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k == "identifier" and not strict_identifiers:
                continue
            if k == "authoring_tool":
                continue
            if k not in a:
                out.append(f"{path}/{k}: only in ours ({str(b[k])[:160]!r})")
            elif k not in b:
                out.append(f"{path}/{k}: only in apple ({str(a[k])[:160]!r})")
            else:
                out.extend(diff(a[k], b[k], f"{path}/{k}", strict_identifiers=strict_identifiers))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{path}: list length apple={len(a)} ours={len(b)}")
        for i, (x, y) in enumerate(zip(a, b)):
            out.extend(diff(x, y, f"{path}[{i}]", strict_identifiers=strict_identifiers))
    else:
        if a != b:
            out.append(f"{path}: apple={str(a)[:120]!r} ours={str(b)[:120]!r}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("apple", type=Path)
    ap.add_argument("ours", type=Path)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--strict-identifiers", action="store_true")
    ap.add_argument("--ignore-identifiers", action="store_true",
                    help="deprecated alias; identifiers are structural-matched by default")
    ns = ap.parse_args()

    apple = semantic_view(inspect(ns.apple))
    ours = semantic_view(inspect(ns.ours))
    problems = diff(apple, ours, strict_identifiers=ns.strict_identifiers)

    report = {
        "apple": str(ns.apple),
        "ours": str(ns.ours),
        "mismatch_count": len(problems),
        "mismatches": problems,
    }
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if ns.json:
        ns.json.write_text(text + "\n")
    print(text)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
