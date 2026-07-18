#!/usr/bin/env python3
"""Scan installed CARs for potentially useful aggregate/fixture candidates."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from collections import Counter

from actool_linux.bom import BOMStore
from actool_linux.car import CARFile


def iter_cars(roots: list[Path], limit: int) -> list[Path]:
    paths: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob('Assets.car'):
            paths.append(path)
            if len(paths) >= limit:
                return paths
    return paths


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', action='append', default=[])
    ap.add_argument('--limit', type=int, default=250)
    ap.add_argument('--sample', type=int, default=120)
    ns = ap.parse_args()
    roots = [Path(p) for p in ns.root] or [Path('/Applications'), Path('/System/Library')]
    cars = iter_cars(roots, ns.limit)
    summary: dict[str, object] = {
        'sampled': len(cars),
        'layout_counts': Counter(),
        'top_shelf_candidates': [],
        'watch_candidates': [],
        'vision_candidates': [],
        'layout_1002_candidates': [],
        'layout_other_candidates': [],
    }
    interesting_layouts = {1002, 1019, 1020, 1021}
    for car_path in cars:
        try:
            car = CARFile(BOMStore.from_path(str(car_path)))
        except Exception:
            continue
        id_to_name = {}
        for facet in car.facets:
            ident = facet.named_attributes.get('kCRThemeIdentifierName')
            if ident is not None:
                id_to_name[ident] = facet.name
        for rendition in car.renditions:
            layout = rendition.csi.layout
            key = rendition.key
            summary['layout_counts'][str(layout)] += 1
            text_name = ' '.join(filter(None, [id_to_name.get(key.get('kCRThemeIdentifierName')), rendition.csi.name]))
            lowered = text_name.lower()
            row = {
                'path': str(car_path),
                'name': text_name,
                'layout': layout,
                'pixel_format': rendition.csi.pixel_format,
                'key': {k: v for k, v in key.items() if v},
            }
            if ('top shelf' in lowered or 'topshelf' in lowered or '.brandassets' in str(car_path).lower()) and len(summary['top_shelf_candidates']) < ns.sample:
                summary['top_shelf_candidates'].append(row)
            if key.get('kCRThemeIdiomName') == 5 and (key.get('kCRThemeSubtypeName') or key.get('kCRThemeDimension2Name')) and len(summary['watch_candidates']) < ns.sample:
                summary['watch_candidates'].append(row)
            if key.get('kCRThemeIdiomName') == 8 and (key.get('kCRThemeLayerName') or key.get('kCRThemeDimension2Name')) and len(summary['vision_candidates']) < ns.sample:
                summary['vision_candidates'].append(row)
            if layout == 1002 and len(summary['layout_1002_candidates']) < ns.sample:
                summary['layout_1002_candidates'].append(row)
            elif layout in interesting_layouts and len(summary['layout_other_candidates']) < ns.sample:
                summary['layout_other_candidates'].append(row)
    summary['layout_counts'] = dict(summary['layout_counts'].most_common())
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
