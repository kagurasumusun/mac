"""Clean-room writer for CoreUI layered image stack aggregates.

Reproduces the observable Apple actool output for `.imagestack` /
`.brandassets` sources on the tvOS path:

- layout-1002 root rendition ("Contents.json", DATA, public.layeredimage UTI)
  with TLV 1012 (layer reference list), TLV 1020 (stack flags), TLV 1021
  (auxiliary records), TLV 1004 (blend), TLV 1005 (UTI), TLV 1006.
- one deepmap2 child image per applicable layer, keyed to its own facet
  ("<stack>/<Layer>/Content").
- ZZZZFlattenedImage-1.1.0-gamut0 (part 208, layout 0) holding the
  source-over premultiplied BGRA composite as chunked CBCK/LZFSE.
- ZZZZRadiosityImage-1.0.0 (part 209, layout 0) holding the mode-0 light-map
  container: canvas padded by 40px per side, 32x16 px cell grid of u16 pairs
  preceded by the constant f32 0.7255510687828064 (baked opacity-scale).
  The exact Apple irradiance kernel is private; values here are an
  alpha-derived approximation (see RADIOITY_APPROXIMATION note).
- Top Shelf images compile as ordinary idiom-tv deepmap images.

Everything was derived from observable outputs of Apple actool on
independently created inputs; no Apple code is used.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Sequence

from .carwriter import AssetRendition, _fixed, _identifier

# Idiom assignments observed in Apple tvOS output.
IDIOM_UNIVERSAL = 0
IDIOM_TV = 3
IDIOM_MARKETING = 6

# TLC constant baked into every observed radiosity container.
RADIOSITY_CONSTANT = struct.unpack("<f", bytes.fromhex("b7bd393f"))[0]  # 0.7255510687828064


def _csi_header(name: str, *, flags: int, width: int, height: int, scale: int,
                pixel_format: bytes, color_space: int, layout: int) -> bytearray:
    header = bytearray(184)
    header[:4] = b"ISTC"
    struct.pack_into("<5I", header, 4, 1, flags, width, height, scale * 100)
    header[24:28] = pixel_format
    struct.pack_into("<I", header, 28, color_space)
    struct.pack_into("<I2H", header, 32, 0, layout, 0)
    header[40:168] = _fixed(name, 128)
    return header


def _tlv(tag: int, payload: bytes) -> bytes:
    return struct.pack("<2I", tag, len(payload)) + payload


def tlv_layer_list(entries: Sequence[tuple[int, int, int, int, float, int]]) -> bytes:
    """TLV 1012: header (count, reserved) + per-layer 32B fixed + 16B key.

    entry: origin_x, origin_y, reserved0, width, height, reserved1, opacity,
           key_byte_length(16), key tokens (1,85)(2,181)(17,identifier)(0,0)
    """
    out = [struct.pack("<2I", len(entries), 0)]
    for origin_x, origin_y, width, height, opacity, identifier in entries:
        key = struct.pack("<8H", 1, 85, 2, 181, 17, identifier, 0, 0)
        out.append(struct.pack("<6IfI", origin_x, origin_y, 0, width, height, 0, opacity, len(key)))
        out.append(key)
    return b"".join(out)


def tlv_stack_flags(count: int) -> bytes:
    """TLV 1020: header (count, reserved) + 13-byte flag records (enabled=1)."""
    return struct.pack("<2I", count, 0) + b"".join(
        b"\x01" + b"\0" * 8 + b"\0" * 4 for _ in range(count)
    )


def tlv_stack_aux(count: int) -> bytes:
    """TLV 1021: header (count, reserved) + 20-byte zeroed auxiliary records."""
    return struct.pack("<2I", count, 0) + b"\0" * (20 * count)


TLV_BLEND = b"\x00\x00\x00\x00\x00\x00\x80\x3f"          # TLV 1004: mode 0, opacity 1.0
TLV_ORIENTATION = struct.pack("<I", 1)                  # TLV 1006


def tlv_uti(uti: str) -> bytes:
    raw = uti.encode("utf-8") + b"\x00"
    return struct.pack("<2I", len(raw), 0) + raw


def build_stack_root_csi(name: str, *, canvas: tuple[int, int], layer_identifiers: list[int]) -> bytes:
    """layout-1002 aggregate root rendition for a layered image stack."""
    width, height = canvas
    tlvs = b"".join((
        _tlv(1012, tlv_layer_list([(0, 0, width, height, 1.0, ident) for ident in layer_identifiers])),
        _tlv(1020, tlv_stack_flags(len(layer_identifiers))),
        _tlv(1021, tlv_stack_aux(len(layer_identifiers))),
        _tlv(1004, TLV_BLEND),
        _tlv(1005, tlv_uti("public.layeredimage")),
        _tlv(1006, TLV_ORIENTATION),
    ))
    payload = b"DWAR" + b"\0" * 8
    header = _csi_header("Contents.json", flags=0, width=width, height=height, scale=1,
                         pixel_format=b"ATAD", color_space=0, layout=1002)
    struct.pack_into("<4I", header, 168, len(tlvs), 1, 0, len(payload))
    return bytes(header) + tlvs + payload


def _lzfse_compress(data: bytes) -> bytes:
    from . import lzfse_compat
    return lzfse_compat.compress(data)


def cbck_container(pixels: bytes, width: int, height: int, bpp: int = 4, *, chunks: int = 3) -> bytes:
    """MLEC mode-3 codec-4 chunked CBCK/LZFSE container.

    Observed Apple flattened images always split into three KCBC chunks of
    ceil(height/3) rows each.
    """
    row_bytes = width * bpp
    rows_per = (height + chunks - 1) // chunks
    out = [b"MLEC", struct.pack("<3I", 3, 4, chunks)]
    for start in range(0, height, rows_per):
        rows = min(rows_per, height - start)
        raw = pixels[start * row_bytes: (start + rows) * row_bytes]
        compressed = _lzfse_compress(raw)
        out.append(b"KCBC" + struct.pack("<4I", 0, 0, rows, len(compressed)) + compressed)
    return b"".join(out)


def _premultiplied_bgra_from_pngs(pngs: Sequence[bytes]) -> tuple[int, int, bytes]:
    """Source-over composite of PNG layers into premultiplied BGRA."""
    from .carwriter import _png_premultiplied_bgra
    width = height = None
    canvas: list[int] = []
    for png in pngs:
        w, h, pixels, _ = _png_premultiplied_bgra(png)
        if width is None:
            width, height = w, h
            canvas = [0] * (w * h * 4)
        elif (w, h) != (width, height):
            raise ValueError(f"layer canvas mismatch: {w}x{h} != {width}x{height}")
        for i in range(width * height):
            sb, sg, sr, sa = pixels[4 * i: 4 * i + 4]
            db, dg, dr, da = canvas[4 * i: 4 * i + 4]
            # source-over with premultiplied components (0..255 ints).
            inv = 255 - sa
            ob = sb + (db * inv + 127) // 255
            og = sg + (dg * inv + 127) // 255
            orr = sr + (dr * inv + 127) // 255
            oa = sa + (da * inv + 127) // 255
            canvas[4 * i: 4 * i + 4] = (ob, og, orr, oa)
    assert width is not None and height is not None
    return width, height, bytes(canvas)


def build_flattened_payload(width: int, height: int, pixels: bytes) -> bytes:
    return cbck_container(pixels, width, height)


def build_radiosity_payload(width: int, height: int, flat_width: int, flat_height: int,
                            flattened: bytes) -> bytes:
    """Mode-0 radiosity container.

    Grammar (observed): MLEC, u32 mode=0, u32 codec=6, u32 data_length, then
    u16 width, u16 height, u16 32, u16 0, f32 RADIOSITY_CONSTANT, and a
    (width//32) x (height//16) cell-major grid of u16 pairs.

    RADIOSITY_APPROXIMATION: the exact Apple irradiance values are private.
    We emit an alpha-silhouette-derived smooth field: flat opaque icon
    interior receives high values toward the lower third, edges fall off with
    a 1-cell blur, producing the same shape family as observed fixtures
    (bright lower band, fade to zero outside the silhouette).
    """
    cells_x = max(1, width // 32)
    cells_y = max(1, height // 16)
    # Alpha coverage per cell from the flattened composite (offset 40px in).
    grid = []
    blur_radius = 1
    for gy in range(cells_y):
        for gx in range(cells_x):
            # cell center in flattened coordinates (radiosity canvas is
            # flattened canvas + 40px border on each side).
            fx = gx * 32 + 16 - 40
            fy = gy * 16 + 8 - 40
            coverage = 0.0
            for oy in (-blur_radius, 0, blur_radius):
                for ox in (-blur_radius * 2, 0, blur_radius * 2):
                    sx = min(max(fx + ox, 0), flat_width - 1)
                    sy = min(max(fy + oy, 0), flat_height - 1)
                    coverage += flattened[(sy * flat_width + sx) * 4 + 3] / 255.0
            coverage /= 9.0
            # vertical ramp: icon occupies (radiosity_h-80); bottom third is bright.
            top = 40.0
            bottom = 40.0 + flat_height
            if bottom > top and coverage > 0.0:
                rel = (gy * 16 + 8 - top) / (bottom - top)
                ramp = min(max((rel - 0.55) / 0.35, 0.0), 1.0)
            else:
                ramp = 0.0
            value = coverage * (0.10 + 0.90 * ramp)
            u = min(int(value * 65535 + 0.5), 65535)
            grid.append((u, u))
    data = [struct.pack("<4H", width, height, 32, 0), struct.pack("<f", RADIOSITY_CONSTANT)]
    for a, b in grid:
        data.append(struct.pack("<2H", a, b))
    body = b"".join(data)
    return b"MLEC" + struct.pack("<3I", 0, 6, len(body)) + body


def _image_tlvs(width: int, height: int, bpp: int, *, metrics: bool) -> bytes:
    tlvs = [struct.pack("<2I5I", 1001, 20, 1, 0, 0, width, height)]
    if metrics:
        tlvs.append(struct.pack("<2I7I", 1003, 28, 1, 0, 0, 0, 0, width, height))
    tlvs.append(struct.pack("<2I8s", 1004, 8, TLV_BLEND))
    tlvs.append(struct.pack("<2II", 1006, 4, 1))
    tlvs.append(struct.pack("<2II", 1007, 4, width * bpp))
    return b"".join(tlvs)


def build_flattened_csi(width: int, height: int, pixels: bytes, *, scale: int = 1) -> bytes:
    payload = build_flattened_payload(width, height, pixels)
    tlvs = _image_tlvs(width, height, 4, metrics=False)
    header = _csi_header("ZZZZFlattenedImage-1.1.0-gamut0", flags=0, width=width, height=height,
                         scale=scale, pixel_format=b"BGRA", color_space=1, layout=0)
    struct.pack_into("<4I", header, 168, len(tlvs), 1, 0, len(payload))
    return bytes(header) + tlvs + payload


def build_radiosity_csi(flat_width: int, flat_height: int, flattened: bytes, *, scale: int = 1) -> bytes:
    radio_w, radio_h = flat_width + 80, flat_height + 80
    payload = build_radiosity_payload(radio_w, radio_h, flat_width, flat_height, flattened)
    tlvs = _image_tlvs(radio_w, radio_h, 4, metrics=False)
    header = _csi_header("ZZZZRadiosityImage-1.0.0", flags=0, width=radio_w, height=radio_h,
                         scale=scale, pixel_format=b"BGRA", color_space=1, layout=0)
    struct.pack_into("<4I", header, 168, len(tlvs), 1, 0, len(payload))
    return bytes(header) + tlvs + payload


@dataclass(frozen=True)
class StackLayerImage:
    layer_name: str          # e.g. "Front"
    filename: str            # source filename, e.g. "content.png"
    png: bytes


def imagestack_renditions(stack_name: str, layers: Sequence[StackLayerImage], *,
                          root_idiom: int = IDIOM_UNIVERSAL,
                          child_idiom: int = IDIOM_UNIVERSAL,
                          flattened_idiom: int = IDIOM_UNIVERSAL,
                          scale: int = 1,
                          root_identifier: int | None = None) -> list[AssetRendition]:
    """Build the full aggregate rendition family for one layered image stack.

    `layers` must be ordered back-to-front (bottom-most first), matching the
    observed TLV-1012 ordering. `root_identifier` overrides the aggregate
    records' identifier (used for tvOS brandassets, where the marketing-size
    stack reuses the primary stack's identifier).
    """
    if len(layers) < 2:
        raise ValueError("a layered image stack needs at least two layer images")
    child_ids = [_identifier(f"{stack_name}/{layer.layer_name}/Content") for layer in layers]
    root_id = _identifier(stack_name) if root_identifier is None else root_identifier

    # Flatten composite (back-to-front source-over).
    flat_w, flat_h, flattened = _premultiplied_bgra_from_pngs([layer.png for layer in layers])

    result: list[AssetRendition] = []
    result.append(AssetRendition(
        stack_name, build_stack_root_csi(stack_name, canvas=(flat_w, flat_h), layer_identifiers=child_ids),
        181, 181, scale=scale, idiom=root_idiom, identifier_override=root_id))
    from .carwriter import make_deepmap_csi_variant  # local import to avoid cycles
    for index, layer in enumerate(layers):
        # Layer order from the source: writer receives back-to-front; the
        # bottom-most (back) rendition uses MLEC mode 2 when the image is a
        # uniform opaque fill, other layers use mode 0 (observed Apple rule).
        csi = make_deepmap_csi_variant(layer.png, layer.filename, scale=scale,
                                       prefer_cbck=False,
                                       stack_bottom=(index == 0))
        result.append(AssetRendition(
            f"{stack_name}/{layer.layer_name}/Content", csi, 181, scale=scale,
            idiom=child_idiom, identifier_override=child_ids[index]))
    result.append(AssetRendition(
        stack_name, build_flattened_csi(flat_w, flat_h, flattened, scale=scale), 208, 181,
        scale=scale, idiom=flattened_idiom, identifier_override=root_id))
    result.append(AssetRendition(
        stack_name, build_radiosity_csi(flat_w, flat_h, flattened, scale=scale), 209, 181,
        scale=scale, idiom=flattened_idiom, identifier_override=root_id))
    return result
