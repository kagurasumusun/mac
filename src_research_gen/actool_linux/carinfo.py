from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from .atlas import parse_atlas_link, parse_atlas_name_list, parse_atlas_trim
from .bom import BOMError, BOMStore
from .car import CARFile
from .iconstack import (
    parse_iconstack_aux_list,
    parse_iconstack_group_style_reference,
    parse_iconstack_root_style_list,
    parse_named_gradient_payload,
)
from .paletteimg import decode_quantized_image_payload, parse_theme_pixel_rendition
from .solidstack import (
    parse_solidimagestack_layer_flags,
    parse_solidimagestack_layer_list,
    parse_solidimagestack_layer_reserved,
)
from .texture import parse_texture_auxiliary_flag, parse_texture_reference_payload


def _decoded_tlvs(rendition) -> list[dict[str, object]]:
    rows = []
    layout = rendition.csi.layout
    part = rendition.key.get('kCRThemePartName')
    for tlv in rendition.csi.tlvs:
        item: dict[str, object] = {'tag': tlv.tag, 'length': len(tlv.value)}
        try:
            if tlv.tag == 1010:
                link = parse_atlas_link(tlv.value)
                item['atlas_link'] = {
                    'x': link.x,
                    'y': link.y,
                    'width': link.width,
                    'height': link.height,
                    'variant': link.variant,
                    'header_u16': link.header_u16,
                    'header_u32': link.header_u32,
                    'tokens': [{'attribute': t.attribute, 'value': t.value} for t in link.tokens],
                }
            elif tlv.tag == 1011:
                trim = parse_atlas_trim(tlv.value)
                item['atlas_trim'] = trim.__dict__
            elif tlv.tag == 1013:
                item['atlas_name_list'] = list(parse_atlas_name_list(tlv.value).names)
            elif tlv.tag == 1012:
                layers = parse_solidimagestack_layer_list(tlv.value)
                key = (
                    'solid_image_stack_layers' if layout == 1018
                    else 'layer_stack_layers' if layout == 1002
                    else 'icon_stack_layers' if layout == 1019
                    else 'icon_group_layers' if layout == 1020
                    else 'stack_layers'
                )
                item[key] = [
                    {
                        'origin_x': layer.origin_x,
                        'origin_y': layer.origin_y,
                        'reserved0': layer.reserved0,
                        'width': layer.width,
                        'height': layer.height,
                        'reserved1': layer.reserved1,
                        'opacity': layer.opacity,
                        'referenced_key': list(layer.referenced_key.attribute_value_pairs),
                    }
                    for layer in layers.layers
                ]
            elif tlv.tag == 1020:
                if layout == 1018:
                    flags = parse_solidimagestack_layer_flags(tlv.value)
                    item['solid_image_stack_flags'] = [
                        {
                            'enabled': flag.enabled,
                            'reserved0_hex': flag.reserved0.hex(),
                            'reserved1_hex': flag.reserved1.hex(),
                        }
                        for flag in flags.flags
                    ]
                elif layout == 1019:
                    styles = parse_iconstack_root_style_list(tlv.value)
                    references_list: list[Any] = []
                    try:
                        parsed_list = parse_solidimagestack_layer_list(next(x.value for x in rendition.csi.tlvs if x.tag == 1012))
                        references_list = list(parsed_list.layers)
                    except Exception:
                        references_list = []
                    decoded = []
                    for index, entry in enumerate(styles.entries):
                        row = entry.__dict__ | {'inferred_kind_name': entry.inferred_kind_name}
                        if index < len(references_list):
                            pairs = dict(references_list[index].referenced_key.attribute_value_pairs)
                            refpart = pairs.get(2)
                            if refpart is not None:
                                row['inferred_role_for_referenced_part'] = entry.inferred_role_for_referenced_part(refpart)
                        decoded.append(row)
                    item['icon_stack_rendering_properties'] = decoded
                elif layout == 1020 and part == 246:
                    ref = parse_iconstack_group_style_reference(tlv.value)
                    item['icon_group_rendering_properties'] = ref.__dict__ | {
                        'inferred_kind_name': ref.inferred_kind_name,
                        'inferred_name_kind': ref.inferred_name_kind,
                    }
                else:
                    flags = parse_solidimagestack_layer_flags(tlv.value)
                    item['stack_flags'] = [
                        {
                            'enabled': flag.enabled,
                            'reserved0_hex': flag.reserved0.hex(),
                            'reserved1_hex': flag.reserved1.hex(),
                        }
                        for flag in flags.flags
                    ]
            elif tlv.tag == 1021:
                if layout == 1018:
                    reserved = parse_solidimagestack_layer_reserved(tlv.value)
                    item['solid_image_stack_reserved'] = [entry.raw.hex() for entry in reserved.entries]
                elif layout in (1002, 1019, 1020):
                    aux = parse_iconstack_aux_list(tlv.value)
                    item['icon_stack_auxiliary'] = [entry.__dict__ for entry in aux.entries]
                else:
                    reserved = parse_solidimagestack_layer_reserved(tlv.value)
                    item['stack_reserved'] = [entry.raw.hex() for entry in reserved.entries]
            elif tlv.tag == 1014:
                aux_flag = parse_texture_auxiliary_flag(tlv.value)
                item['texture_auxiliary_flag'] = {'values': list(aux_flag.values), 'raw_hex': aux_flag.raw.hex()}
        except Exception as exc:
            item['decode_error'] = str(exc)
        rows.append(item)
    return rows


def _decoded_payload(rendition) -> dict[str, object] | None:
    if rendition.csi.rendition_data[:4] == b'RTXT':
        try:
            ref = parse_texture_reference_payload(rendition.csi.rendition_data)
            return {
                'texture_reference': {
                    'payload_value': ref.payload_value,
                    'u32_2': ref.u32_2,
                    'u32_3': ref.u32_3,
                    'u32_4': ref.u32_4,
                    'key_pairs': list(ref.key_pairs),
                }
            }
        except Exception as exc:
            return {'texture_reference_error': str(exc)}
    if rendition.key.get('kCRThemePartName') == 247 and rendition.csi.rendition_data[:4] == b'ARGG':
        try:
            gradient = parse_named_gradient_payload(rendition.csi.rendition_data)
            return {
                'named_gradient': {
                    'signature': gradient.signature,
                    'stop_count': gradient.stop_count,
                    'mode': gradient.mode,
                    'scalar_1': gradient.scalar_1,
                    'scalar_2': gradient.scalar_2,
                    'scalar_3': gradient.scalar_3,
                    'scalar_4': gradient.scalar_4,
                    'scalar_5': gradient.scalar_5,
                    'stops': [{'position': stop.position, 'name': stop.name} for stop in gradient.stops],
                }
            }
        except Exception as exc:
            return {'named_gradient_error': str(exc)}
    try:
        wrapper = parse_theme_pixel_rendition(rendition.csi.rendition_data)
    except Exception:
        return None
    result: dict[str, object] = {
        'wrapper_version': wrapper.version,
        'compression_type': wrapper.compression_type,
        'raw_payload_length': len(wrapper.raw_data),
    }
    if wrapper.compression_type == 8:
        try:
            decoded = decode_quantized_image_payload(
                wrapper.raw_data,
                width=rendition.csi.width,
                height=rendition.csi.height,
                pixel_format=rendition.csi.pixel_format,
            )
            result['quantized'] = {
                'version': decoded.version,
                'palette_count': len(decoded.palette),
                'bits_per_index': decoded.bits_per_index,
                'decoded_indices': len(decoded.indices),
            }
        except Exception as exc:
            result['quantized_error'] = str(exc)
    return result


def inspect(path: Path) -> dict[str, object]:
    store = BOMStore.from_path(path)
    car = CARFile(store)
    return {
        'path': str(path),
        'size': path.stat().st_size,
        'bom_version': store.header.version,
        'block_count_hint': store.header.block_count_hint,
        'allocated_blocks': len(store.blocks),
        'car_header': {
            'byte_order': car.header.byte_order,
            'core_ui_version': car.header.core_ui_version,
            'storage_version': car.header.storage_version,
            'storage_timestamp': car.header.storage_timestamp,
            'schema_version': car.header.schema_version,
            'rendition_count': car.header.rendition_count,
            'main_version': car.header.main_version,
            'version_string': car.header.version_string,
            'identifier': car.header.identifier,
            'associated_checksum': car.header.associated_checksum,
            'color_space_id': car.header.color_space_id,
            'key_semantics': car.header.key_semantics,
        },
        'extended_metadata': car.extended_metadata.__dict__ if car.extended_metadata else None,
        'appearances': [entry.__dict__ for entry in car.appearances],
        'localizations': [entry.__dict__ for entry in car.localizations],
        'key_format': list(car.key_format.names),
        'facets': [
            {
                'name': facet.name,
                'cursor_hotspot': list(facet.cursor_hotspot),
                'attributes': facet.named_attributes,
            }
            for facet in car.facets
        ],
        'renditions': [
            {
                'name': rendition.csi.name,
                'width': rendition.csi.width,
                'height': rendition.csi.height,
                'scale': rendition.csi.scale,
                'pixel_format': rendition.csi.pixel_format,
                'color_space_id': rendition.csi.color_space_id,
                'layout': rendition.csi.layout,
                'flags': rendition.csi.flags,
                'key': rendition.key,
                'tlvs': _decoded_tlvs(rendition),
                'payload_length': len(rendition.csi.rendition_data),
                'decoded_payload': _decoded_payload(rendition),
            }
            for rendition in car.renditions
        ],
        'named_blocks': [
            {'name': name, 'identifier': identifier, 'size': len(store.block(identifier))}
            for name, identifier in store.variables.items()
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='actool-car-info')
    parser.add_argument('car', type=Path)
    ns = parser.parse_args(argv)
    try:
        print(json.dumps(inspect(ns.car), indent=2))
    except (OSError, BOMError) as exc:
        print(f'actool-car-info: error: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
