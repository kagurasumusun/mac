#!/usr/bin/env python3
"""Scan CAR files for observable ImageStack / IconImageStack / IconGroup / Named Gradient fixtures."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

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
    ap.add_argument('--limit', type=int, default=1200)
    ap.add_argument('--sample', type=int, default=80)
    ap.add_argument('--output', type=Path, default=Path('iconstack-fixtures.json'))
    ns = ap.parse_args()
    roots = [Path(p) for p in ns.root] or [Path('/Applications'), Path('/System/Library')]
    cars = iter_cars(roots, ns.limit)
    layout_counts: Counter[int] = Counter()
    rows: list[dict[str, object]] = []
    for path in cars:
        try:
            car = CARFile(BOMStore.from_path(str(path)))
        except Exception:
            continue
        hits = [
            {
                'layout': rendition.csi.layout,
                'name': rendition.csi.name,
                'pixel_format': rendition.csi.pixel_format,
                'key': {k: v for k, v in rendition.key.items() if v},
            }
            for rendition in car.renditions
            if rendition.csi.layout in (1002, 1019, 1020, 1021)
        ]
        if not hits:
            continue
        layout_counts.update(hit['layout'] for hit in hits)
        rows.append({
            'path': str(path),
            'counts': dict(Counter(hit['layout'] for hit in hits)),
            'sample': hits[:ns.sample],
        })
    payload = {
        'schema': 1,
        'sampled_cars': len(cars),
        'cars_with_hits': len(rows),
        'layout_counts': dict(layout_counts),
        'rows': rows,
    }
    ns.output.write_text(json.dumps(payload, indent=2) + '\n')
    print(json.dumps({'sampled_cars': len(cars), 'cars_with_hits': len(rows), 'layout_counts': dict(layout_counts)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
