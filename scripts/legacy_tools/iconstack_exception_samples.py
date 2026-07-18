#!/usr/bin/env python3
"""Extract representative unresolved iconstack samples from installed CARs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from actool_linux.bom import BOMStore
from actool_linux.car import CARFile
from actool_linux.iconstack import parse_iconstack_group_style_reference, parse_iconstack_root_style_list
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
    ap.add_argument('--samples', type=int, default=40)
    ap.add_argument('--output', type=Path, default=Path('iconstack-exception-samples.json'))
    ns = ap.parse_args()
    roots = [Path(p) for p in ns.root] or [Path('/Applications'), Path('/System/Library')]
    paths = iter_cars(roots, ns.limit)

    root_part246_kind0: list[dict[str, object]] = []
    group_kind0: list[dict[str, object]] = []
    group_other_name: list[dict[str, object]] = []

    for path in paths:
        try:
            car = CARFile(BOMStore.from_path(str(path)))
        except Exception:
            continue
        id_to_name: dict[tuple[int, int], str] = {}
        for facet in car.facets:
            ident = facet.named_attributes.get('kCRThemeIdentifierName')
            part = facet.named_attributes.get('kCRThemePartName')
            if ident is not None and part is not None:
                id_to_name[(ident, part)] = facet.name
        for rendition in car.renditions:
            tlvmap = {tlv.tag: tlv.value for tlv in rendition.csi.tlvs}
            if rendition.csi.layout == 1019 and 1012 in tlvmap and 1020 in tlvmap and len(root_part246_kind0) < ns.samples:
                refs = parse_solidimagestack_layer_list(tlvmap[1012]).layers
                styles = parse_iconstack_root_style_list(tlvmap[1020]).entries
                for ref, style in zip(refs, styles):
                    pairs = dict(ref.referenced_key.attribute_value_pairs)
                    part = pairs.get(2, -1)
                    ident = pairs.get(17, -1)
                    if part == 246 and style.kind == 0 and len(root_part246_kind0) < ns.samples:
                        root_part246_kind0.append({
                            'path': str(path),
                            'stack_name': rendition.csi.name,
                            'appearance': rendition.key.get('kCRThemeAppearanceName'),
                            'child_part': part,
                            'child_identifier': ident,
                            'child_name': id_to_name.get((ident, part)),
                            'style': style.__dict__ | {'inferred_kind_name': style.inferred_kind_name},
                        })
            if rendition.csi.layout == 1020 and 1020 in tlvmap:
                try:
                    ref = parse_iconstack_group_style_reference(tlvmap[1020])
                except Exception:
                    continue
                row = {
                    'path': str(path),
                    'group_name': rendition.csi.name,
                    'appearance': rendition.key.get('kCRThemeAppearanceName'),
                    'reference': ref.__dict__ | {
                        'inferred_kind_name': ref.inferred_kind_name,
                        'inferred_name_kind': ref.inferred_name_kind,
                    },
                }
                if ref.kind == 0 and len(group_kind0) < ns.samples:
                    group_kind0.append(row)
                if ref.inferred_name_kind == 'other' and len(group_other_name) < ns.samples:
                    group_other_name.append(row)
            if len(root_part246_kind0) >= ns.samples and len(group_kind0) >= ns.samples and len(group_other_name) >= ns.samples:
                break

    payload = {
        'schema': 1,
        'root_part246_kind0': root_part246_kind0,
        'group_kind0': group_kind0,
        'group_other_name': group_other_name,
    }
    ns.output.write_text(json.dumps(payload, indent=2) + '\n')
    print(json.dumps({k: len(v) for k, v in payload.items() if isinstance(v, list)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
