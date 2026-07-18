#!/usr/bin/env python3
"""Aggregate observable semantics from ImageStack / IconImageStack / IconGroup / Named Gradient fixtures."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from actool_linux.bom import BOMStore
from actool_linux.car import CARFile
from actool_linux.iconstack import (
    parse_iconstack_aux_list,
    parse_iconstack_group_style_reference,
    parse_iconstack_root_style_list,
    parse_named_gradient_payload,
)
from actool_linux.solidstack import parse_solidimagestack_layer_list


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
    ap.add_argument('--limit', type=int, default=2000)
    ap.add_argument('--output', type=Path, default=Path('iconstack-semantics-summary.json'))
    ns = ap.parse_args()
    roots = [Path(p) for p in ns.root] or [Path('/Applications'), Path('/System/Library')]
    paths = iter_cars(roots, ns.limit)

    root_style_kind_by_refpart: Counter[tuple[int, int]] = Counter()
    root_style_values_by_kind: dict[int, Counter[float]] = defaultdict(Counter)
    aux_u32_2_by_refpart: dict[int, Counter[int]] = defaultdict(Counter)
    aux_f32_1_by_refpart: dict[int, Counter[float]] = defaultdict(Counter)
    aux_f32_2_by_refpart: dict[int, Counter[float]] = defaultdict(Counter)
    group_style_kind_counts: Counter[int] = Counter()
    group_style_count_counts: Counter[int] = Counter()
    group_style_name_kind: Counter[str] = Counter()
    gradient_stopcount_mode: Counter[tuple[int, int]] = Counter()
    gradient_scalar_tuples: Counter[tuple[float, float, float, float, float]] = Counter()
    cars_with_hits = 0

    for path in paths:
        try:
            car = CARFile(BOMStore.from_path(str(path)))
        except Exception:
            continue
        hit = False
        for rendition in car.renditions:
            if rendition.csi.layout not in (1002, 1019, 1020, 1021):
                continue
            hit = True
            tlvmap = {tlv.tag: tlv.value for tlv in rendition.csi.tlvs}
            if rendition.csi.layout == 1019 and 1012 in tlvmap and 1020 in tlvmap and 1021 in tlvmap:
                refs = parse_solidimagestack_layer_list(tlvmap[1012]).layers
                styles = parse_iconstack_root_style_list(tlvmap[1020]).entries
                aux_entries = parse_iconstack_aux_list(tlvmap[1021]).entries
                for ref, style, aux in zip(refs, styles, aux_entries):
                    refpart = dict(ref.referenced_key.attribute_value_pairs).get(2, -1)
                    root_style_kind_by_refpart[(refpart, style.kind)] += 1
                    root_style_values_by_kind[style.kind][round(style.value, 3)] += 1
                    aux_u32_2_by_refpart[refpart][aux.u32_2] += 1
                    aux_f32_1_by_refpart[refpart][round(aux.f32_1, 3)] += 1
                    aux_f32_2_by_refpart[refpart][round(aux.f32_2, 3)] += 1
            elif rendition.csi.layout == 1020 and 1020 in tlvmap:
                try:
                    ref = parse_iconstack_group_style_reference(tlvmap[1020])
                except Exception:
                    ref = None
                if ref is not None:
                    group_style_kind_counts[ref.kind] += 1
                    group_style_count_counts[ref.count] += 1
                    if '/Color-' in ref.name:
                        group_style_name_kind['color'] += 1
                    elif '/Gradient-' in ref.name:
                        group_style_name_kind['gradient'] += 1
                    else:
                        group_style_name_kind['other'] += 1
            elif rendition.csi.layout == 1021:
                try:
                    gradient = parse_named_gradient_payload(rendition.csi.rendition_data)
                except Exception:
                    gradient = None
                if gradient is not None:
                    gradient_stopcount_mode[(gradient.stop_count, gradient.mode)] += 1
                    gradient_scalar_tuples[(
                        round(gradient.scalar_1, 3),
                        round(gradient.scalar_2, 3),
                        round(gradient.scalar_3, 3),
                        round(gradient.scalar_4, 3),
                        round(gradient.scalar_5, 3),
                    )] += 1
        if hit:
            cars_with_hits += 1

    payload = {
        'schema': 1,
        'sampled_cars': len(paths),
        'cars_with_hits': cars_with_hits,
        'root_style_kind_by_refpart': {f'{refpart}:{kind}': count for (refpart, kind), count in sorted(root_style_kind_by_refpart.items())},
        'root_style_values_by_kind': {str(kind): dict(counter) for kind, counter in root_style_values_by_kind.items()},
        'aux_u32_2_by_refpart': {str(refpart): dict(counter) for refpart, counter in aux_u32_2_by_refpart.items()},
        'aux_f32_1_by_refpart': {str(refpart): dict(counter) for refpart, counter in aux_f32_1_by_refpart.items()},
        'aux_f32_2_by_refpart': {str(refpart): dict(counter) for refpart, counter in aux_f32_2_by_refpart.items()},
        'group_style_kind_counts': dict(group_style_kind_counts),
        'group_style_count_counts': dict(group_style_count_counts),
        'group_style_name_kind': dict(group_style_name_kind),
        'gradient_stopcount_mode': {f'{stop_count}:{mode}': count for (stop_count, mode), count in gradient_stopcount_mode.items()},
        'gradient_scalar_tuples': {str(key): value for key, value in gradient_scalar_tuples.most_common(50)},
    }
    ns.output.write_text(json.dumps(payload, indent=2) + '\n')
    print(json.dumps({'sampled_cars': len(paths), 'cars_with_hits': cars_with_hits, 'output': str(ns.output)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
