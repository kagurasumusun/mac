#!/usr/bin/env python3
"""Scan installed Apple CARs for observable atlas/packed-image fixtures.

This is evidence gathering only. It does not claim a full Xcode packing heuristic.
The scan reads a bounded sample of CARs, parses linked-image INLK metadata when
present, and summarizes token/rectangle/page patterns.
"""
from __future__ import annotations

import json
from pathlib import Path
from collections import Counter, defaultdict

from actool_linux.atlas import parse_atlas_link
from actool_linux.bom import BOMStore
from actool_linux.car import CARFile

SEARCH_ROOTS = [
    Path("/System/Library"),
    Path("/Applications"),
]
MAX_CARS = 400


def iter_cars() -> list[Path]:
    cars: list[Path] = []
    for root in SEARCH_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("Assets.car"):
            cars.append(path)
            if len(cars) >= MAX_CARS:
                return cars
    return cars


def main() -> int:
    sampled = iter_cars()
    summary: dict[str, object] = {
        "sampled": len(sampled),
        "cars_with_packedimage": 0,
        "cars_with_inlk": 0,
        "packedimage_count": 0,
        "linked_image_count": 0,
        "token_attributes": Counter(),
        "token_pairs": Counter(),
        "page_dimension1_values": Counter(),
        "page_name_prefixes": Counter(),
        "rect_sizes": Counter(),
        "files": [],
    }
    files: list[dict[str, object]] = []
    for path in sampled:
        try:
            car = CARFile(BOMStore.from_path(str(path)))
        except Exception:
            continue
        packed = []
        linked = []
        for rendition in car.renditions:
            if rendition.csi.layout == 1004:
                packed.append(rendition)
            elif rendition.csi.layout == 1003:
                tlv = next((item for item in rendition.csi.tlvs if item.tag == 1010), None)
                if tlv is not None:
                    try:
                        linked.append((rendition, parse_atlas_link(tlv.value)))
                    except Exception:
                        pass
        if not packed and not linked:
            continue
        if packed:
            summary["cars_with_packedimage"] += 1
            summary["packedimage_count"] += len(packed)
        if linked:
            summary["cars_with_inlk"] += 1
            summary["linked_image_count"] += len(linked)
        row = {
            "path": str(path),
            "packed_count": len(packed),
            "linked_count": len(linked),
            "pages": [],
            "links": [],
        }
        for rendition in packed:
            dim1 = rendition.key.get("kCRThemeDimension1Name", 0)
            summary["page_dimension1_values"][str(dim1)] += 1
            name = rendition.csi.name
            prefix = name.split("-", 1)[0]
            summary["page_name_prefixes"][prefix] += 1
            row["pages"].append({
                "name": name,
                "dimension1": dim1,
                "width": rendition.csi.width,
                "height": rendition.csi.height,
            })
        for rendition, link in linked:
            size_key = f"{link.width}x{link.height}"
            summary["rect_sizes"][size_key] += 1
            token_map = []
            for token in link.tokens:
                summary["token_attributes"][str(token.attribute)] += 1
                summary["token_pairs"][f"{token.attribute}:{token.value}"] += 1
                token_map.append([token.attribute, token.value])
            row["links"].append({
                "name": rendition.csi.name,
                "x": link.x,
                "y": link.y,
                "width": link.width,
                "height": link.height,
                "tokens": token_map,
            })
        files.append(row)
    summary["token_attributes"] = dict(summary["token_attributes"].most_common())
    summary["token_pairs"] = dict(summary["token_pairs"].most_common(50))
    summary["page_dimension1_values"] = dict(summary["page_dimension1_values"].most_common())
    summary["page_name_prefixes"] = dict(summary["page_name_prefixes"].most_common())
    summary["rect_sizes"] = dict(summary["rect_sizes"].most_common(50))
    summary["files"] = files[:80]
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
