#!/usr/bin/env python3
"""Scan installed CAR files for observable aggregate/layout fixtures.

This parser-based scan looks for CSI layout values, explicit layer/depth keys,
Top Shelf naming hints, and watch complication-like keyed renditions. It is
intended to locate candidate fixtures for future reverse engineering work.
"""
from __future__ import annotations

import json
from pathlib import Path
from collections import Counter

from actool_linux.bom import BOMStore
from actool_linux.car import CARFile

ROOTS = [Path('/System/Library'), Path('/Applications')]


def iter_cars(limit: int) -> list[Path]:
    paths: list[Path] = []
    for root in ROOTS:
        if not root.exists():
            continue
        for path in root.rglob('Assets.car'):
            paths.append(path)
            if len(paths) >= limit:
                return paths
    return paths


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=120)
    ns = ap.parse_args()
    sampled = iter_cars(ns.limit)
    summary: dict[str, object] = {
        'sampled': len(sampled),
        'layout_counts': Counter(),
        'layout_1002_hits': [],
        'top_shelf_name_hits': [],
        'watch_key_hits': [],
        'vision_layer_hits': [],
    }
    for path in sampled:
        try:
            car = CARFile(BOMStore.from_path(str(path)))
        except Exception:
            continue
        for rendition in car.renditions:
            layout = rendition.csi.layout
            summary['layout_counts'][str(layout)] += 1
            key = rendition.key
            name = rendition.csi.name
            facet_name = None
            try:
                facet_name = next((f.name for f in car.facets if f.named_attributes.get('kCRThemeIdentifierName') == key.get('kCRThemeIdentifierName')), None)
            except Exception:
                facet_name = None
            text_name = ' '.join(x for x in (facet_name, name) if x)
            if layout == 1002:
                summary['layout_1002_hits'].append({
                    'path': str(path),
                    'name': text_name,
                    'pixel_format': rendition.csi.pixel_format,
                    'key': key,
                })
            lowered = text_name.lower()
            if 'top shelf' in lowered or 'topshelf' in lowered:
                summary['top_shelf_name_hits'].append({
                    'path': str(path),
                    'name': text_name,
                    'layout': layout,
                    'key': key,
                })
            if key.get('kCRThemeIdiomName') == 5 and (key.get('kCRThemeSubtypeName') or key.get('kCRThemeDimension2Name')):
                summary['watch_key_hits'].append({
                    'path': str(path),
                    'name': text_name,
                    'layout': layout,
                    'subtype': key.get('kCRThemeSubtypeName'),
                    'dimension2': key.get('kCRThemeDimension2Name'),
                })
            if key.get('kCRThemeIdiomName') == 8 and (key.get('kCRThemeLayerName') or key.get('kCRThemeDimension2Name')):
                summary['vision_layer_hits'].append({
                    'path': str(path),
                    'name': text_name,
                    'layout': layout,
                    'layer': key.get('kCRThemeLayerName'),
                    'dimension2': key.get('kCRThemeDimension2Name'),
                })
    summary['layout_counts'] = dict(summary['layout_counts'].most_common())
    summary['layout_1002_hits'] = summary['layout_1002_hits'][:120]
    summary['top_shelf_name_hits'] = summary['top_shelf_name_hits'][:120]
    summary['watch_key_hits'] = summary['watch_key_hits'][:120]
    summary['vision_layer_hits'] = summary['vision_layer_hits'][:120]
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
