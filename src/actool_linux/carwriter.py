from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import struct
import zlib

from .bomwriter import BOMWriter
from . import lzfse_compat
from .paletteimg import build_palette_img_wrapper
from .solidstack import (
    SolidImageStackLayerFlag,
    SolidImageStackLayerReference,
    SolidImageStackLayerReserved,
    SolidImageStackReferencedKey,
    build_solidimagestack_layer_flags,
    build_solidimagestack_layer_list,
    build_solidimagestack_layer_reserved,
)
from .texture import TextureAuxiliaryFlag, TextureReference, build_texture_auxiliary_flag, build_texture_reference_payload


KEY_ATTRIBUTES = (7, 13, 1, 2, 3, 17, 11, 12)
IOS_ATTRIBUTES = (7, 13, 12, 15, 16, 17, 1, 2)
APP_ICON_ATTRIBUTES = (7, 13, 12, 15, 16, 9, 17, 1, 2)      # adds dimension2
STACK_ATTRIBUTES = (7, 13, 12, 15, 16, 8, 17, 1, 2)        # adds dimension1
LAYER_ATTRIBUTES = (7, 13, 12, 15, 16, 9, 17, 1, 2, 11)    # dimension2 + layer
SYMBOL_ATTRIBUTES = (7, 13, 1, 2, 4, 17, 8, 9, 10, 14, 12, 19, 18, 25, 26, 27)

# Rendition parts emitted for layered image stack aggregates (flattened /
# radiosity). Apple compiles catalogs containing these with the iOS-family
# key format even when every rendition is universal idiom.
_IMAGE_STACK_PARTS = (208, 209)


def _select_key_attributes(assets) -> tuple[int, ...]:
    """Single source of truth for the CoreUI KEYFORMAT attribute tuple.

    The tuple families mirror the layouts Apple actool emits per rendition
    family; keep this ordered from most- to least-specific family.
    """
    seq = list(assets)
    if any(a.glyph_weight or a.glyph_size or a.atlas_linked for a in seq):
        return SYMBOL_ATTRIBUTES
    if any(a.layer for a in seq):
        return LAYER_ATTRIBUTES
    if any(a.dimension1 for a in seq):
        return STACK_ATTRIBUTES
    if any(a.dimension2 for a in seq):
        return APP_ICON_ATTRIBUTES
    if any(a.idiom or a.appearance or a.subtype for a in seq):
        return IOS_ATTRIBUTES
    if any(a.part in _IMAGE_STACK_PARTS for a in seq):
        return IOS_ATTRIBUTES
    return KEY_ATTRIBUTES

BITMAP_VALUE = bytes.fromhex(
    "01000000000000002400000008000000ffffffff01000000ffffffffffffffff"
    "01000000ffffffff0100000002000000"
)


@dataclass(frozen=True)
class AssetRendition:
    name: str
    csi: bytes
    part: int
    facet_part: int | None = None
    scale: int = 1
    idiom: int = 0
    appearance: int = 0
    subtype: int = 0
    dimension2: int = 0
    localization: str | None = None
    direction: int = 0
    dimension1: int = 0
    state: int = 0
    presentation_state: int = 0
    previous_state: int = 0
    previous_value: int = 0
    deployment_target: int = 0
    glyph_weight: int = 0
    glyph_size: int = 0
    element: int = 0x55
    identifier_override: int | None = None
    atlas_linked: bool = False
    layer: int = 0

    @property
    def effective_facet_part(self) -> int:
        return self.part if self.facet_part is None else self.facet_part


def _fixed(text: str, length: int) -> bytes:
    raw = text.encode("utf-8")
    if len(raw) >= length:
        raise ValueError(f"string is too long for {length}-byte fixed field")
    return raw + b"\0" * (length - len(raw))


def _identifier(name: str) -> int:
    # Stable nonzero 16-bit identifier. It only needs to be unique within a
    # catalog; collision handling belongs in the future multi-asset builder.
    value = int.from_bytes(hashlib.sha256(name.encode("utf-8")).digest()[:2], "little")
    return value or 1


def _car_header(rendition_count: int) -> bytes:
    return b"".join((
        b"RATC",
        struct.pack("<4I", 918, 17, 0, rendition_count),
        _fixed("@(#)PROGRAM:CoreUI  PROJECT:CoreUI-918.5\n", 128),
        _fixed("actool-linux clean-room writer", 256),
        b"\0" * 16,
        struct.pack("<4I", 0, 5, 1, 1),
    ))


def _extended_metadata(platform: str, target: str, thinning_arguments: str = "") -> bytes:
    return b"META" + b"".join((
        _fixed(thinning_arguments, 256), _fixed(target, 256), _fixed(platform, 256),
        _fixed("actool-linux clean-room CoreUI encoder", 256),
    ))


def _key_format(attributes: tuple[int, ...] = KEY_ATTRIBUTES) -> bytes:
    return b"tmfk" + struct.pack("<2I", 0, len(attributes)) + struct.pack(
        "<" + "I" * len(attributes), *attributes
    )


def _tree_descriptor(root: int, node_size: int, count: int, key_size: int, numeric_key: bool = False) -> bytes:
    return struct.pack(
        ">4s4IBII", b"tree", 1, root, node_size, count,
        1 if numeric_key else 0, key_size, 0,
    )


def _leaf_many(entries: list[tuple[int, int]], inline_keys: list[bytes], node_size: int) -> bytes:
    if inline_keys and len(inline_keys) != len(entries):
        raise ValueError("inline key count does not match tree entry count")
    raw = bytearray(struct.pack(">HHII", 1, len(entries), 0, 0))
    for value_id, key_id in entries:
        raw += struct.pack(">II", value_id, key_id)
    # A reserved u32 separates the reference array from inline key bytes.
    raw += b"\0" * 4
    inline = b"".join(inline_keys)
    raw += inline
    total = node_size + len(inline)
    if len(raw) > total:
        raise ValueError("tree leaf does not fit configured node size")
    return bytes(raw).ljust(total, b"\0")


def _leaf(value_id: int, key_id: int, inline_key: bytes, node_size: int) -> bytes:
    return _leaf_many([(value_id, key_id)], [inline_key] if inline_key else [], node_size)


def _facet_value(identifier: int, part: int) -> bytes:
    return struct.pack("<3H6H", 0, 0, 3, 1, 0x55, 2, part, 17, identifier)


def _rendition_key(identifier: int, part: int, scale: int = 1) -> bytes:
    values = (0, 0, 0x55, part, 0, identifier, 0, scale)
    return struct.pack("<8H", *values)


def _rendition_key_for(asset: AssetRendition, identifier: int, attributes: tuple[int, ...], localization_id: int = 0) -> bytes:
    values = {
        7: asset.appearance, 13: localization_id, 12: asset.scale, 15: asset.idiom,
        16: asset.subtype, 17: identifier if asset.identifier_override is None else asset.identifier_override, 1: asset.element, 2: asset.part,
        3: 0, 11: asset.layer, 9: asset.dimension2, 4: asset.direction,
        8: asset.dimension1, 10: asset.state, 14: asset.presentation_state,
        19: asset.previous_state, 18: asset.previous_value, 25: asset.deployment_target,
        26: asset.glyph_weight, 27: asset.glyph_size,
    }
    return struct.pack("<" + "H" * len(attributes), *(values[item] for item in attributes))


def _csi_data(data: bytes, uti: str) -> bytes:
    header = bytearray(184)
    header[:4] = b"ISTC"
    struct.pack_into("<5I", header, 4, 1, 0, 0, 0, 100)
    header[24:28] = b"ATAD"  # little-endian fourcc DATA
    struct.pack_into("<I", header, 28, 0)
    struct.pack_into("<I2H", header, 32, 0, 1000, 0)
    header[40:168] = _fixed("CoreStructuredImage", 128)
    uti_raw = uti.encode("utf-8") + b"\0"
    tlvs = b"".join((
        struct.pack("<2I8s", 1004, 8, b"\0\0\0\0\0\0\x80?"),
        struct.pack("<2I2I", 1005, 8 + len(uti_raw), len(uti_raw), 0) + uti_raw,
        struct.pack("<2II", 1006, 4, 1),
    ))
    payload = b"DWAR" + struct.pack("<2I", 0, len(data)) + data
    struct.pack_into("<4I", header, 168, len(tlvs), 1, 0, len(payload))
    return bytes(header) + tlvs + payload


def _jpeg_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        raise ValueError("input is not a JPEG stream")
    cursor = 2
    sof = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    while cursor + 4 <= len(data):
        if data[cursor] != 0xFF:
            cursor += 1
            continue
        while cursor < len(data) and data[cursor] == 0xFF:
            cursor += 1
        if cursor >= len(data):
            break
        marker = data[cursor]
        cursor += 1
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            continue
        if cursor + 2 > len(data):
            break
        length = int.from_bytes(data[cursor:cursor + 2], "big")
        if length < 2 or cursor + length > len(data):
            raise ValueError("JPEG segment is truncated")
        if marker in sof:
            if length < 7:
                raise ValueError("JPEG SOF segment is truncated")
            height = int.from_bytes(data[cursor + 3:cursor + 5], "big")
            width = int.from_bytes(data[cursor + 5:cursor + 7], "big")
            if not width or not height:
                raise ValueError("JPEG dimensions are zero")
            return width, height
        cursor += length
    raise ValueError("JPEG has no supported start-of-frame marker")


def _heif_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < 12 or data[4:8] != b"ftyp":
        raise ValueError("input is not an ISO BMFF/HEIF stream")
    cursor = 0
    while True:
        marker = data.find(b"ispe", cursor)
        if marker < 0:
            break
        if marker >= 4 and marker + 16 <= len(data):
            width = int.from_bytes(data[marker + 8:marker + 12], "big")
            height = int.from_bytes(data[marker + 12:marker + 16], "big")
            if width and height:
                return width, height
        cursor = marker + 4
    raise ValueError("HEIF stream has no valid ispe dimensions box")


def _csi_raw_image(data: bytes, filename: str, fourcc: str, width: int, height: int, scale: int = 1) -> bytes:
    header = bytearray(184)
    header[:4] = b"ISTC"
    struct.pack_into("<5I", header, 4, 1, 16, 0, 0, scale * 100)
    header[24:28] = fourcc.encode("ascii")[::-1]
    struct.pack_into("<I", header, 28, 0)
    struct.pack_into("<I2H", header, 32, 0, 12, 0)
    header[40:168] = _fixed(filename, 128)
    tlvs = b"".join((
        struct.pack("<2I5I", 1001, 20, 1, 0, 0, width, height),
        struct.pack("<2I7I", 1003, 28, 1, 0, 0, 0, 0, width, height),
        struct.pack("<2I8s", 1004, 8, b"\0\0\0\0\0\0\x80?"),
        struct.pack("<2II", 1006, 4, 1),
    ))
    payload = b"DWAR" + struct.pack("<2I", 0, len(data)) + data
    struct.pack_into("<4I", header, 168, len(tlvs), 1, 0, len(payload))
    return bytes(header) + tlvs + payload


def _csi_jpeg(data: bytes, filename: str, scale: int = 1) -> bytes:
    width, height = _jpeg_dimensions(data)
    return _csi_raw_image(data, filename, "JPEG", width, height, scale)


def _csi_heif(data: bytes, filename: str, scale: int = 1) -> bytes:
    width, height = _heif_dimensions(data)
    return _csi_raw_image(data, filename, "HEIF", width, height, scale)


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c; pa = abs(p - a); pb = abs(p - b); pc = abs(p - c)
    return a if pa <= pb and pa <= pc else b if pb <= pc else c


def _unfilter_png_rows(raw: bytes, row_bytes: int, rows: int, filter_bpp: int) -> list[bytes]:
    """Bounds-checked PNG scanline unfiltering (PNG spec section 6)."""
    if len(raw) != rows * (row_bytes + 1):
        raise ValueError("PNG scanline length mismatch")
    result: list[bytes] = []
    previous = bytearray(row_bytes)
    pos = 0
    for _ in range(rows):
        kind = raw[pos]
        pos += 1
        scan = bytearray(raw[pos:pos + row_bytes])
        pos += row_bytes
        if kind > 4:
            raise ValueError(f"unsupported PNG filter: {kind}")
        for x in range(row_bytes):
            left = scan[x - filter_bpp] if x >= filter_bpp else 0
            up = previous[x]
            upper_left = previous[x - filter_bpp] if x >= filter_bpp else 0
            predictor = (0 if kind == 0 else left if kind == 1 else up if kind == 2
                         else (left + up) // 2 if kind == 3 else _paeth(left, up, upper_left))
            scan[x] = (scan[x] + predictor) & 255
        result.append(bytes(scan))
        previous = scan
    return result


def _packed_sample(row: bytes, x: int, depth: int) -> int:
    bit = x * depth
    return (row[bit // 8] >> (8 - depth - bit % 8)) & ((1 << depth) - 1)


def _decode_indexed_png_for_palette_img(data: bytes) -> tuple[int, int, bytes, bytes]:
    """Return width, height, ARGB palette bytes, and one-byte-per-pixel indices."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("input is not a PNG stream")
    cursor = 8; ihdr = None; idat = bytearray(); palette = None; transparency = b""
    while cursor + 12 <= len(data):
        length = int.from_bytes(data[cursor:cursor + 4], "big"); kind = data[cursor + 4:cursor + 8]; end = cursor + 12 + length
        if end > len(data): raise ValueError("PNG chunk is truncated")
        payload = data[cursor + 8:cursor + 8 + length]; expected = int.from_bytes(data[cursor + 8 + length:end], "big")
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != expected: raise ValueError("PNG chunk CRC mismatch")
        if kind == b"IHDR": ihdr = payload
        elif kind == b"PLTE": palette = payload
        elif kind == b"tRNS": transparency = payload
        elif kind == b"IDAT": idat += payload
        elif kind == b"IEND": break
        cursor = end
    if ihdr is None or len(ihdr) != 13: raise ValueError("PNG has no valid IHDR")
    width, height, depth, color_type, compression, filtering, interlace = struct.unpack(">IIBBBBB", ihdr)
    if not width or not height or width > 16384 or height > 16384: raise ValueError("PNG dimensions are invalid or exceed safety limit")
    if color_type != 3 or depth not in (1, 2, 4, 8) or compression != 0 or filtering != 0 or interlace not in (0, 1):
        raise ValueError("palette-img encoder accepts indexed PNG at depth 1/2/4/8, with optional Adam7 interlace")
    try: raw = zlib.decompress(bytes(idat))
    except zlib.error as exc: raise ValueError(f"invalid PNG deflate stream: {exc}") from exc
    if palette is None or not palette or len(palette) % 3 or len(palette) > 768:
        raise ValueError("indexed PNG has invalid or missing PLTE")
    entries = len(palette) // 3
    palette_argb = bytearray()
    for index in range(entries):
        r, g, b = palette[index * 3:index * 3 + 3]; alpha = transparency[index] if index < len(transparency) else 255
        palette_argb += bytes((alpha, r, g, b))
    if interlace == 0:
        stride = (width * depth + 7) // 8
        rows = _unfilter_png_rows(raw, stride, height, 1)
        indices = bytearray()
        for row in rows:
            for x in range(width):
                index = _packed_sample(row, x, depth)
                if index >= entries: raise ValueError("indexed PNG references palette entry outside PLTE")
                indices.append(index)
        return width, height, bytes(palette_argb), bytes(indices)
    passes = ((0,0,8,8),(4,0,8,8),(0,4,4,8),(2,0,4,4),(0,2,2,4),(1,0,2,2),(0,1,1,2))
    decoded = bytearray(width * height)
    pos = 0
    for x0, y0, dx, dy in passes:
        pw = 0 if width <= x0 else (width - x0 + dx - 1) // dx
        ph = 0 if height <= y0 else (height - y0 + dy - 1) // dy
        if not pw or not ph:
            continue
        row_bytes = (pw * depth + 7) // 8
        pass_len = ph * (row_bytes + 1)
        if pos + pass_len > len(raw): raise ValueError("Adam7 PNG pass is truncated")
        rows = _unfilter_png_rows(raw[pos:pos + pass_len], row_bytes, ph, 1)
        pos += pass_len
        for py, row in enumerate(rows):
            y = y0 + py * dy
            for px in range(pw):
                x = x0 + px * dx
                index = _packed_sample(row, px, depth)
                if index >= entries: raise ValueError("indexed PNG references palette entry outside PLTE")
                decoded[y * width + x] = index
    if pos != len(raw): raise ValueError("Adam7 PNG has trailing decompressed data")
    return width, height, bytes(palette_argb), bytes(decoded)


def _decode_png_8bit(data: bytes) -> tuple[int, int, int, bytes, tuple[bytes, bytes] | None]:
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("input is not a PNG stream")
    cursor = 8; ihdr = None; idat = bytearray(); palette = None; transparency = b""
    while cursor + 12 <= len(data):
        length = int.from_bytes(data[cursor:cursor + 4], "big"); kind = data[cursor + 4:cursor + 8]; end = cursor + 12 + length
        if end > len(data): raise ValueError("PNG chunk is truncated")
        payload = data[cursor + 8:cursor + 8 + length]; expected = int.from_bytes(data[cursor + 8 + length:end], "big")
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != expected: raise ValueError("PNG chunk CRC mismatch")
        if kind == b"IHDR": ihdr = payload
        elif kind == b"PLTE": palette = payload
        elif kind == b"tRNS": transparency = payload
        elif kind == b"IDAT": idat += payload
        elif kind == b"IEND": break
        cursor = end
    if ihdr is None or len(ihdr) != 13: raise ValueError("PNG has no valid IHDR")
    width, height, depth, color_type, compression, filtering, interlace = struct.unpack(">IIBBBBB", ihdr)
    if not width or not height or width > 16384 or height > 16384: raise ValueError("PNG dimensions are invalid or exceed safety limit")
    valid_direct = depth == 8 and color_type in (2, 4, 6)
    valid_grey = depth == 8 and color_type == 0
    valid_grey16 = depth == 16 and color_type == 0
    valid_ga16 = depth == 16 and color_type == 4
    valid_indexed = color_type == 3 and depth in (1, 2, 4, 8)
    if not (valid_direct or valid_grey or valid_grey16 or valid_ga16 or valid_indexed) or compression != 0 or filtering != 0 or interlace not in (0, 1):
        raise ValueError("deepmap encoder accepts 8-bit greyscale/RGB/GA/RGBA, 16-bit greyscale/GA, or indexed PNG at depth 1/2/4/8, with optional Adam7 interlace")
    try: raw = zlib.decompress(bytes(idat))
    except zlib.error as exc: raise ValueError(f"invalid PNG deflate stream: {exc}") from exc
    channels = 1 if color_type in (0, 3) else 3 if color_type == 2 else 2 if color_type == 4 else 4
    pixel_bytes = channels * depth // 8 if color_type != 3 else 0
    filter_bpp = max(1, (channels * depth + 7) // 8)
    if interlace == 0:
        stride = (width * depth + 7) // 8 if color_type == 3 else width * pixel_bytes
        decoded = bytearray().join(_unfilter_png_rows(raw, stride, height, filter_bpp))
    else:
        # Adam7 maps seven independently filtered subimages into the final image.
        # Keeping indexed output as one byte per sample avoids fragile bit repacking.
        passes = ((0,0,8,8),(4,0,8,8),(0,4,4,8),(2,0,4,4),(0,2,2,4),(1,0,2,2),(0,1,1,2))
        output_bpp = 1 if color_type == 3 else pixel_bytes
        decoded = bytearray(width * height * output_bpp)
        pos = 0
        for x0, y0, dx, dy in passes:
            pw = 0 if width <= x0 else (width - x0 + dx - 1) // dx
            ph = 0 if height <= y0 else (height - y0 + dy - 1) // dy
            if not pw or not ph:
                continue
            row_bytes = (pw * depth + 7) // 8 if color_type == 3 else pw * pixel_bytes
            pass_len = ph * (row_bytes + 1)
            if pos + pass_len > len(raw):
                raise ValueError("Adam7 PNG pass is truncated")
            rows = _unfilter_png_rows(raw[pos:pos + pass_len], row_bytes, ph, filter_bpp)
            pos += pass_len
            for py, row in enumerate(rows):
                y = y0 + py * dy
                for px in range(pw):
                    x = x0 + px * dx
                    dst = (y * width + x) * output_bpp
                    if color_type == 3:
                        decoded[dst] = _packed_sample(row, px, depth)
                    else:
                        src = px * pixel_bytes
                        decoded[dst:dst + pixel_bytes] = row[src:src + pixel_bytes]
        if pos != len(raw):
            raise ValueError("Adam7 PNG has trailing decompressed data")
    if color_type == 4 and depth == 16:
        decoded = bytearray(value for i in range(0, len(decoded), 4) for value in (decoded[i], decoded[i + 2]))
    if color_type == 0:
        # Grayscale expands to grayscale+alpha. The optional tRNS gray sample
        # becomes the transparent key; all other pixels are fully opaque.
        trns_gray = struct.unpack(">H", transparency[:2])[0] if len(transparency) >= 2 else None
        expanded = bytearray()
        if depth == 16:
            for i in range(0, len(decoded), 2):
                sample = (decoded[i] << 8) | decoded[i + 1]
                alpha = 0 if (trns_gray is not None and sample == trns_gray) else 255
                expanded += bytes((decoded[i], alpha))
        else:
            for gray in decoded:
                alpha = 0 if (trns_gray is not None and gray == (trns_gray & 0xFF)) else 255
                expanded += bytes((gray, alpha))
        decoded = expanded
        color_type = 4
    if color_type == 3:
        if palette is None or not palette or len(palette) % 3 or len(palette) > 768:
            raise ValueError("indexed PNG has invalid or missing PLTE")
        entries = len(palette) // 3; rgba = bytearray(); indices = bytearray(); palette_bgra = bytearray()
        for index in range(entries):
            r, g, b = palette[index * 3:index * 3 + 3]; alpha = transparency[index] if index < len(transparency) else 255
            palette_bgra += bytes(((b * alpha + 127) // 255, (g * alpha + 127) // 255, (r * alpha + 127) // 255, alpha))
        packed_stride = (width * depth + 7) // 8
        for y in range(height):
            for x in range(width):
                index = decoded[y * width + x] if interlace else _packed_sample(decoded[y * packed_stride:(y + 1) * packed_stride], x, depth)
                if index >= entries: raise ValueError("indexed PNG references palette entry outside PLTE")
                indices.append(index); rgba += palette[index * 3:index * 3 + 3] + bytes((transparency[index] if index < len(transparency) else 255,))
        return width, height, 6, bytes(rgba), (bytes(palette_bgra), bytes(indices))
    return width, height, color_type, bytes(decoded), None



def resize_png(data: bytes, width: int, height: int) -> bytes:
    """Nearest-neighbour PNG resize used for deterministic AppIcon sidecars."""
    if width <= 0 or height <= 0 or width > 16384 or height > 16384:
        raise ValueError("output PNG dimensions are invalid")
    source_width, source_height, color_type, pixels, _indexed = _decode_png_8bit(data)
    rgba = bytearray()
    if color_type == 2:
        for r, g, b in zip(pixels[0::3], pixels[1::3], pixels[2::3]): rgba += bytes((r, g, b, 255))
    elif color_type == 4:
        for gray, alpha in zip(pixels[0::2], pixels[1::2]): rgba += bytes((gray, gray, gray, alpha))
    else:
        rgba += pixels
    scanlines = bytearray()
    for y in range(height):
        sy = min(source_height - 1, y * source_height // height)
        scanlines.append(0)
        for x in range(width):
            sx = min(source_width - 1, x * source_width // width)
            offset = (sy * source_width + sx) * 4
            scanlines += rgba[offset:offset + 4]
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(bytes(scanlines), 9)) + chunk(b"IEND", b"")

def _csi_png_deepmap(data: bytes, filename: str, *, scale: int = 1, vector_fallback: bool = False) -> bytes:
    width, height, color_type, pixels, indexed = _decode_png_8bit(data)
    premultiplied = bytearray()
    all_opaque = True
    if color_type == 4:
        for gray, alpha in zip(pixels[0::2], pixels[1::2]):
            premultiplied += bytes(((gray * alpha + 127) // 255, alpha)); all_opaque &= alpha == 255
        pixel_format, color_space, bpp = b" 8AG", 2, 2
    elif color_type == 2:
        for r, g, b in zip(pixels[0::3], pixels[1::3], pixels[2::3]): premultiplied += bytes((b, g, r, 255))
        pixel_format, color_space, bpp = b"BGRA", 1, 4
    else:
        for r, g, b, alpha in zip(pixels[0::4], pixels[1::4], pixels[2::4], pixels[3::4]):
            premultiplied += bytes(((b * alpha + 127) // 255, (g * alpha + 127) // 255, (r * alpha + 127) // 255, alpha)); all_opaque &= alpha == 255
        pixel_format, color_space, bpp = b"BGRA", 1, 4
    dmp2 = b"dmp2" + bytes((1, 1, 10, bpp)) + struct.pack("<HH", width, height) + premultiplied
    mode = 2 if all_opaque else 0
    if indexed is not None and width * height >= 4096:
        from . import lzfse_compat
        palette_bgra, indices = indexed; compressed = lzfse_compat.compress(indices)
        dmp2 = b"dmp2" + bytes((4, 1, 10, 4)) + struct.pack("<HHHH", width, height, len(palette_bgra) // 4, 4) + palette_bgra + struct.pack("<I", len(compressed)) + compressed
        mode = 2
    payload = b"MLEC" + struct.pack("<7I", mode, 11, 16 + len(dmp2), 1, bpp, len(dmp2), 0) + dmp2
    flags = 276 if vector_fallback else 16
    header = bytearray(184); header[:4] = b"ISTC"; struct.pack_into("<5I", header, 4, 1, flags, width, height, scale * 100)
    header[24:28] = pixel_format; struct.pack_into("<I", header, 28, color_space); struct.pack_into("<I2H", header, 32, 0, 12, 0); header[40:168] = _fixed(filename, 128)
    tlvs = b"".join((struct.pack("<2I5I",1001,20,1,0,0,width,height),struct.pack("<2I7I",1003,28,1,0,0,0,0,width,height),struct.pack("<2I8s",1004,8,b"\0\0\0\0\0\0\x80?"),struct.pack("<2II",1006,4,1),struct.pack("<2II",1007,4,width * bpp)))
    struct.pack_into("<4I", header, 168, len(tlvs), 1, 0, len(payload))
    return bytes(header) + tlvs + payload



def _csi_png_palette_img(data: bytes, filename: str, *, scale: int = 1) -> bytes:
    width, height, palette_argb, indices = _decode_indexed_png_for_palette_img(data)
    payload = build_palette_img_wrapper(palette_argb, indices, width=width, height=height)
    header = bytearray(184); header[:4] = b"ISTC"; struct.pack_into("<5I", header, 4, 1, 16, width, height, scale * 100)
    header[24:28] = b"BGRA"; struct.pack_into("<I", header, 28, 1); struct.pack_into("<I2H", header, 32, 0, 12, 0); header[40:168] = _fixed(filename, 128)
    tlvs = b"".join((struct.pack("<2I5I",1001,20,1,0,0,width,height),struct.pack("<2I7I",1003,28,1,0,0,0,0,width,height),struct.pack("<2I8s",1004,8,b"\0\0\0\0\0\0\x80?"),struct.pack("<2II",1006,4,1),struct.pack("<2II",1007,4,32)))
    struct.pack_into("<4I", header, 168, len(tlvs), 1, 0, len(payload))
    return bytes(header) + tlvs + payload


def _optional_lzfse():
    """LZFSE codec facade; always available via :mod:`lzfse_compat` fallback."""
    return lzfse_compat


# Observed Apple dmp2 chunking: deepmap CBCK splits by pixel rows so the raw
# per-chunk index plane stays just under one mebibyte.
DMP2_CBCK_CHUNK_RAW_CAP = 0xFFF00


def make_deepmap_csi_variant(data: bytes, filename: str, *, scale: int = 1,
                             prefer_cbck: bool = False, stack_bottom: bool = True) -> bytes:
    """Deepmap2 CSI using the grammar variants observed in Apple output.

    - uniform RGB(A) sources: dmp2 (4,1,10,4) palette-swatch + 1bpp index
      plane (LZFSE), MLEC mode 2 for bottom-most opaque layers, else mode 0.
    - varied RGB(A) sources: dmp2 (2,1,10,4) premultiplied-BGRA LZFSE stream,
      MLEC mode 0.
    - oversized sources with prefer_cbck: MLEC mode 3 codec 11 KCBC chunks;
      each chunk carries its own field header + per-band dmp2.
    - GA sources keep the original bounds-checked v1 grammar
      (already Apple consumer verified).
    """
    width, height, color_type, pixels, indexed = _decode_png_8bit(data)
    lzfse = lzfse_compat
    if color_type == 4 or indexed is not None:
        return _csi_png_deepmap(data, filename, scale=scale)
    premultiplied = bytearray()
    all_opaque = True
    if color_type == 2:
        for r, g, b in zip(pixels[0::3], pixels[1::3], pixels[2::3]):
            premultiplied += bytes((b, g, r, 255))
    else:
        for r, g, b, alpha in zip(pixels[0::4], pixels[1::4], pixels[2::4], pixels[3::4]):
            premultiplied += bytes(((b * alpha + 127) // 255, (g * alpha + 127) // 255, (r * alpha + 127) // 255, alpha))
            all_opaque &= alpha == 255
    premultiplied = bytes(premultiplied)
    uniform = premultiplied[:4] * (width * height) == premultiplied

    def band_dmp2(rows_pixels: bytes, band_height: int) -> bytes:
        band_uniform = rows_pixels[:4] * (width * band_height) == rows_pixels
        if band_uniform:
            indices = b"\x00" * (width * band_height)
            stream = lzfse.compress(indices)
            return (b"dmp2" + bytes((4, 1, 10, 4)) + struct.pack("<HHHH", width, band_height, 1, 4)
                    + rows_pixels[:4] + struct.pack("<I", len(stream)) + stream)
        stream = lzfse.compress(rows_pixels)
        return (b"dmp2" + bytes((2, 1, 10, 4)) + struct.pack("<HH", width, band_height)
                + struct.pack("<HH", len(stream), 0) + stream)

    row_bytes = width * 4
    use_cbck = prefer_cbck and (row_bytes * height > DMP2_CBCK_CHUNK_RAW_CAP * 4) and height > 1
    if use_cbck:
        # Rows per chunk chosen under the raw cap, at least one row.
        rows_per = max(1, DMP2_CBCK_CHUNK_RAW_CAP // row_bytes)
        bands = [(y, min(rows_per, height - y)) for y in range(0, height, rows_per)]
        chunks = []
        for y, rows in bands:
            band = band_dmp2(premultiplied[y * row_bytes:(y + rows) * row_bytes], rows)
            blob = struct.pack("<4I", 1, 4, len(band), 0) + band
            chunks.append(b"KCBC" + struct.pack("<4I", 0, 0, rows, len(blob)) + blob)
        payload = b"MLEC" + struct.pack("<3I", 3, 11, len(chunks)) + b"".join(chunks)
        mode_field = 3
    else:
        if uniform:
            dmp2 = band_dmp2(premultiplied, height)
            mode_field = 2 if (all_opaque and stack_bottom) else 0
        else:
            dmp2 = band_dmp2(premultiplied, height)
            mode_field = 0
        payload = b"MLEC" + struct.pack("<7I", mode_field, 11, 16 + len(dmp2), 1, 4, len(dmp2), 0) + dmp2
    tlvs = b"".join((struct.pack("<2I5I", 1001, 20, 1, 0, 0, width, height),
                     struct.pack("<2I7I", 1003, 28, 1, 0, 0, 0, 0, width, height),
                     struct.pack("<2I8s", 1004, 8, b"\0\0\0\0\0\0\x80?"),
                     struct.pack("<2II", 1006, 4, 1),
                     struct.pack("<2II", 1007, 4, width * 4)))
    header = bytearray(184); header[:4] = b"ISTC"; struct.pack_into("<5I", header, 4, 1, 16, width, height, scale * 100)
    header[24:28] = b"BGRA"; struct.pack_into("<I", header, 28, 1); struct.pack_into("<I2H", header, 32, 0, 12, 0); header[40:168] = _fixed(filename, 128)
    struct.pack_into("<4I", header, 168, len(tlvs), 1, 0, len(payload))
    return bytes(header) + tlvs + payload


def png_dimensions(data: bytes) -> tuple[int, int]:
    width, height, _color_type, _pixels, _indexed = _decode_png_8bit(data)
    return width, height


def _png_premultiplied_bgra(data: bytes) -> tuple[int, int, bytes, bool]:
    width, height, color_type, pixels, _indexed = _decode_png_8bit(data)
    output = bytearray(); opaque = True
    if color_type == 2:
        for r, g, b in zip(pixels[0::3], pixels[1::3], pixels[2::3]): output += bytes((b, g, r, 255))
    elif color_type == 4:
        for gray, alpha in zip(pixels[0::2], pixels[1::2]):
            value = (gray * alpha + 127) // 255; output += bytes((value, value, value, alpha)); opaque &= alpha == 255
    else:
        for r, g, b, alpha in zip(pixels[0::4], pixels[1::4], pixels[2::4], pixels[3::4]):
            output += bytes(((b*alpha+127)//255, (g*alpha+127)//255, (r*alpha+127)//255, alpha)); opaque &= alpha == 255
    return width, height, bytes(output), opaque


def _csi_png_cbck(data: bytes, filename: str, *, scale: int = 1) -> bytes:
    """Encode CoreUI chunked-bitmap (CBCK) with independent LZFSE streams."""
    width, height, pixels, _opaque = _png_premultiplied_bgra(data)
    row_bytes = width * 4
    # Xcode's 1024px AppIcon oracle uses 341-row chunks (0x155000 raw
    # bytes), followed by a one-row tail. 0x155555 is the inferred cap.
    rows_per_chunk = max(1, 0x155555 // row_bytes)
    chunks = []
    for y in range(0, height, rows_per_chunk):
        rows = min(rows_per_chunk, height - y)
        compressed = lzfse_compat.compress(pixels[y * row_bytes:(y + rows) * row_bytes])
        chunks.append(b"KCBC" + struct.pack("<4I", 0, 0, rows, len(compressed)) + compressed)
    payload = b"MLEC" + struct.pack("<3I", 3, 4, len(chunks)) + b"".join(chunks)
    header = bytearray(184); header[:4] = b"ISTC"
    struct.pack_into("<5I", header, 4, 1, 0, width, height, scale * 100)
    header[24:28] = b"BGRA"; struct.pack_into("<I", header, 28, 1)
    struct.pack_into("<I2H", header, 32, 0, 12, 0); header[40:168] = _fixed(filename, 128)
    tlvs = b"".join((struct.pack("<2I5I",1001,20,1,0,0,width,height),struct.pack("<2I7I",1003,28,1,0,0,0,0,width,height),struct.pack("<2I8s",1004,8,b"\0\0\0\0\0\0\x80?"),struct.pack("<2II",1006,4,1),struct.pack("<2II",1007,4,width * 4)))
    struct.pack_into("<4I", header, 168, len(tlvs), 1, 0, len(payload))
    return bytes(header) + tlvs + payload


def _csi_msis(name: str) -> bytes:
    header = bytearray(184); header[:4] = b"ISTC"
    struct.pack_into("<5I", header, 4, 1, 0, 0, 0, 100)
    struct.pack_into("<I2H", header, 32, 0, 1010, 0); header[40:168] = _fixed(name, 128)
    payload = b"SISM" + struct.pack("<5I", 1, 1, 1024, 4, 1)
    struct.pack_into("<4I", header, 168, 0, 1, 0, len(payload))
    return bytes(header) + payload


def _csi_texture_reference(name: str, reference: TextureReference, *, width: int, height: int, scale: int = 2, auxiliary_flag: TextureAuxiliaryFlag | None = None) -> bytes:
    header = bytearray(184); header[:4] = b"ISTC"
    struct.pack_into("<5I", header, 4, 1, 0, width, height, scale * 100)
    header[24:28] = b"ARGB"; struct.pack_into("<I2H", header, 32, 0, 1007, 0); header[40:168] = _fixed(name, 128)
    tlvs = [struct.pack("<2I8s",1004,8,b"\0\0\0\0\0\0\x80?"), struct.pack("<2II",1006,4,1)]
    if auxiliary_flag is not None:
        raw = build_texture_auxiliary_flag(auxiliary_flag)
        tlvs.append(struct.pack("<2I", 1014, len(raw)) + raw)
    payload = build_texture_reference_payload(reference)
    struct.pack_into("<4I", header, 168, sum(len(x) for x in tlvs), 1, 0, len(payload))
    return bytes(header) + b"".join(tlvs) + payload


def _csi_texture_data_from_png(data: bytes, filename: str, *, width: int, height: int, scale: int = 2, mode_field: int = 0x80000) -> bytes:
    tex_w, tex_h, pixels, _opaque = _png_premultiplied_bgra(data)
    row_bytes = tex_w * 4
    rows_per_chunk = max(1, 0x155555 // row_bytes)
    chunks = []
    for y in range(0, tex_h, rows_per_chunk):
        rows = min(rows_per_chunk, tex_h - y)
        compressed = lzfse_compat.compress(pixels[y * row_bytes:(y + rows) * row_bytes])
        chunks.append(b"KCBC" + struct.pack("<4I", 0, 0, rows, len(compressed)) + compressed)
    payload = b"MLEC" + struct.pack("<3I", 1, 4, len(chunks)) + b"".join(chunks)
    header = bytearray(184); header[:4] = b"ISTC"
    struct.pack_into("<5I", header, 4, 1, 0, width, height, scale * 100)
    header[24:28] = b"ARGB"; struct.pack_into("<I2H", header, 32, 0, 1008, 0); header[40:168] = _fixed(filename, 128)
    tlvs = b"".join((struct.pack("<2I8s",1004,8,b"\0\0\0\0\0\0\x80?"),struct.pack("<2II",1006,4,1),struct.pack("<2II",1007,4,mode_field)))
    struct.pack_into("<4I", header, 168, len(tlvs), 1, 0, len(payload))
    return bytes(header) + tlvs + payload


def _csi_solid_image_stack(name: str, *, canvas_points: tuple[int, int], scale: int, identifier_values: list[int]) -> bytes:
    width, height = canvas_points
    refs = [
        SolidImageStackLayerReference(0, 0, 0, width, height, 0, 1.0, SolidImageStackReferencedKey(((1,85),(2,181),(17,ident),(0,0))))
        for ident in identifier_values
    ]
    flags = [SolidImageStackLayerFlag(b"\0"*8, 1, b"\0"*4) for _ in identifier_values]
    reserved = [SolidImageStackLayerReserved(b"\0"*20) for _ in identifier_values]
    tlv1012 = build_solidimagestack_layer_list(refs)
    tlv1020 = build_solidimagestack_layer_flags(flags)
    tlv1021 = build_solidimagestack_layer_reserved(reserved)
    header = bytearray(184); header[:4] = b"ISTC"
    struct.pack_into("<5I", header, 4, 1, 0, width, height, 100)
    header[24:28] = b"ATAD"; struct.pack_into("<I2H", header, 32, 0, 1018, 0); header[40:168] = _fixed(name, 128)
    tlvs = b"".join((
        struct.pack("<2I",1012,len(tlv1012)) + tlv1012,
        struct.pack("<2I",1020,len(tlv1020)) + tlv1020,
        struct.pack("<2I",1021,len(tlv1021)) + tlv1021,
        struct.pack("<2I8s",1004,8,b"\0\0\0\0\0\0\x80?"),
        struct.pack("<2I2I",1005,8 + len(b"public.layeredimage\0"), len(b"public.layeredimage\0"), 0) + b"public.layeredimage\0",
        struct.pack("<2II",1006,4,1),
    ))
    payload = b"DWAR" + struct.pack("<2I", 0, 0)
    struct.pack_into("<4I", header, 168, len(tlvs), 1, 0, len(payload))
    return bytes(header) + tlvs + payload


def _csi_svg(data: bytes, filename: str) -> bytes:
    text = data.lstrip()
    if not text.startswith(b"<svg") and b"<svg" not in text[:512]:
        raise ValueError("input is not an SVG document")
    header = bytearray(184); header[:4] = b"ISTC"
    struct.pack_into("<5I", header, 4, 1, 4, 0, 0, 0)
    header[24:28] = b" GVS"  # little-endian fourcc 'SVG '
    struct.pack_into("<I", header, 28, 0)
    struct.pack_into("<I2H", header, 32, 0, 9, 0)
    header[40:168] = _fixed(filename, 128)
    tlvs = b"".join((struct.pack("<2I8s",1004,8,b"\0\0\0\0\0\0\x80?"),struct.pack("<2II",1006,4,1)))
    payload = b"DWAR" + struct.pack("<2I", 0, len(data)) + data
    struct.pack_into("<4I", header, 168, len(tlvs), 1, 0, len(payload))
    return bytes(header) + tlvs + payload

def _csi_symbol_svg(data: bytes, filename: str) -> bytes:
    """CoreUI symbol-vector CSI (part 59, layout 1017)."""
    text = data.lstrip()
    if b"<svg" not in text[:512] and b":svg" not in text[:512]:
        raise ValueError("input is not an SVG document")
    header = bytearray(184); header[:4] = b"ISTC"
    struct.pack_into("<5I", header, 4, 1, 4, 0, 0, 100)
    header[24:28] = b" GVS"
    struct.pack_into("<I2H", header, 32, 0, 1017, 0)
    header[40:168] = _fixed(filename, 128)
    # 1018 is CoreUI symbol metrics. These neutral metrics are finite and the
    # 1019 tuple advertises one monochrome layer / one vector representation.
    metrics = bytes.fromhex("070000000d0000000000803f0000803f000000000000803f0000803f0000803f0000000000000000")
    symbol_info = struct.pack("<3I", 1, 1, 3)
    tlvs = b"".join((
        struct.pack("<2I8s",1004,8,b"\0\0\0\0\0\0\x80?"),
        struct.pack("<2II",1006,4,1),
        struct.pack("<2I",1018,len(metrics)) + metrics,
        struct.pack("<2I",1019,len(symbol_info)) + symbol_info,
    ))
    payload = b"DWAR" + struct.pack("<2I", 0, len(data)) + data
    struct.pack_into("<4I", header, 168, len(tlvs), 1, 0, len(payload))
    return bytes(header) + tlvs + payload


def _csi_pdf(data: bytes, filename: str) -> bytes:
    if not data.startswith(b"%PDF-"):
        raise ValueError("input is not a PDF stream")
    header = bytearray(184)
    header[:4] = b"ISTC"
    struct.pack_into("<5I", header, 4, 1, 4, 0, 0, 0)
    header[24:28] = b" FDP"  # little-endian fourcc 'PDF '
    struct.pack_into("<I", header, 28, 0)
    struct.pack_into("<I2H", header, 32, 0, 9, 0)
    header[40:168] = _fixed(filename, 128)
    tlvs = b"".join((
        struct.pack("<2I8s", 1004, 8, b"\0\0\0\0\0\0\x80?"),
        struct.pack("<2II", 1006, 4, 1),
    ))
    payload = b"DWAR" + struct.pack("<2I", 0, len(data)) + data
    struct.pack_into("<4I", header, 168, len(tlvs), 1, 0, len(payload))
    return bytes(header) + tlvs + payload


def _csi_color(name: str, components: tuple[float, float, float, float], color_space_id: int = 1) -> bytes:
    header = bytearray(184)
    header[:4] = b"ISTC"
    struct.pack_into("<5I", header, 4, 1, 0, 0, 0, 0)
    header[24:28] = b"\0" * 4
    struct.pack_into("<I", header, 28, 0)
    struct.pack_into("<I2H", header, 32, 0, 1009, 0)
    header[40:168] = _fixed(name, 128)
    tlvs = b"".join((
        struct.pack("<2I8s", 1004, 8, b"\0" * 8),
        struct.pack("<2II", 1006, 4, 1),
    ))
    payload = b"RLOC" + struct.pack("<3I4d", 1, color_space_id, 4, *components)
    struct.pack_into("<4I", header, 168, len(tlvs), 1, 0, len(payload))
    return bytes(header) + tlvs + payload



def _leaf_many_links(entries: list[tuple[int, int]], inline_keys: list[bytes], node_size: int, forward: int, backward: int) -> bytes:
    raw = bytearray(_leaf_many(entries, inline_keys, node_size))
    struct.pack_into(">II", raw, 4, forward, backward)
    return bytes(raw)


def _internal_node(children: list[tuple[int, int, bytes]], node_size: int, *, numeric_key: bool = False) -> bytes:
    """Build N separator pairs plus the required final (N+1th) child."""
    if len(children) < 2:
        raise ValueError("internal tree node needs at least two children")
    raw = bytearray(struct.pack(">HHII", 0, len(children) - 1, 0, 0))
    for child_id, maximum_key_id, _maximum_key in children[:-1]:
        raw += struct.pack(">II", child_id, maximum_key_id)
    raw += struct.pack(">I", children[-1][0])
    # Unlike leaves, internal nodes have no reserved u32 between the final
    # child and inline separator bytes.
    inline = b"" if numeric_key else b"".join(maximum_key for _, _, maximum_key in children[:-1])
    raw += inline
    total = node_size + len(inline)
    if len(raw) > total:
        raise ValueError("internal tree node exceeds configured node size")
    return bytes(raw).ljust(total, b"\0")


def _add_multilevel_tree(
    writer: BOMWriter, name: str, records: list[tuple[int, int, bytes]], *,
    node_size: int, key_size: int, numeric_key: bool = False, leaf_limit: int = 128,
) -> int:
    """Allocate and fill an arbitrary-depth deterministic BOM B+ tree."""
    if not records:
        raise ValueError("tree requires at least one record")
    descriptor_id = writer.add_block(b"", name)
    leaves: list[tuple[int, int, bytes]] = []
    chunks = [records[i:i + leaf_limit] for i in range(0, len(records), leaf_limit)]
    leaf_ids = [writer.add_block(b"") for _ in chunks]
    for index, (leaf_id, chunk) in enumerate(zip(leaf_ids, chunks)):
        entries = [(value_id, key_id) for value_id, key_id, _ in chunk]
        inline = [] if numeric_key else [key for _, _, key in chunk]
        forward = leaf_ids[index + 1] if index + 1 < len(leaf_ids) else 0
        backward = leaf_ids[index - 1] if index else 0
        writer.replace_block(leaf_id, _leaf_many_links(entries, inline, node_size, forward, backward))
        leaves.append((leaf_id, chunk[-1][1], chunk[-1][2]))
    level = leaves
    max_children = max(2, (node_size - 20) // 8 + 1)
    while len(level) > 1:
        groups = [level[i:i + max_children] for i in range(0, len(level), max_children)]
        next_level: list[tuple[int, int, bytes]] = []
        for group in groups:
            if len(group) == 1:
                next_level.append(group[0])
                continue
            node_id = writer.add_block(b"")
            writer.replace_block(node_id, _internal_node(group, node_size, numeric_key=numeric_key))
            next_level.append((node_id, group[-1][1], group[-1][2]))
        level = next_level
    root_id = level[0][0]
    writer.replace_block(descriptor_id, _tree_descriptor(root_id, node_size, len(records), key_size, numeric_key))
    return descriptor_id


def _build_assets_car_multilevel(assets: list[AssetRendition], *, platform: str, target: str, thinning_arguments: str = "") -> bytes:
    """Large-catalog writer using true multi-level trees for all indexes."""
    ordered = sorted(assets, key=lambda item: (item.name.encode("utf-8"), item.part, item.scale, item.csi))
    facet_names = sorted({asset.name for asset in ordered}, key=lambda item: item.encode("utf-8"))
    names = [name.encode("utf-8") for name in facet_names]
    if any(not name or len(name) > 255 for name in names): raise ValueError("asset names must contain 1..255 UTF-8 bytes")
    identifiers = {name: _identifier(name) for name in facet_names}
    if len(set(identifiers.values())) != len(identifiers): raise ValueError("asset identifier collision; rename one of the colliding assets")
    facet_parts: dict[str, int] = {}
    for asset in ordered:
        old = facet_parts.setdefault(asset.name, asset.effective_facet_part)
        if old != asset.effective_facet_part: raise ValueError(f"renditions for {asset.name!r} disagree on facet part")
    attrs = _select_key_attributes(ordered)
    locale_names = sorted({a.localization for a in ordered if a.localization}, key=lambda x: x.encode("utf-8"))
    locale_ids = {name: _identifier("localization:" + name) for name in locale_names}
    if len(set(locale_ids.values())) != len(locale_ids): raise ValueError("localization identifier collision")
    keys = [_rendition_key_for(asset, identifiers[asset.name], attrs, locale_ids.get(asset.localization, 0)) for asset in ordered]
    if len(set(keys)) != len(keys): raise ValueError("duplicate rendition key")

    writer = BOMWriter(); writer.add_block(_car_header(len(ordered)), "CARHEADER")
    if locale_names:
        locale_records = []
        for locale in locale_names:
            key_id = writer.add_block(locale.encode("utf-8")); value_id = writer.add_block(struct.pack("<H", locale_ids[locale]))
            locale_records.append((value_id, key_id, locale.encode("utf-8")))
        _add_multilevel_tree(writer, "LOCALIZATIONKEYS", locale_records, node_size=4096, key_size=0xFFFFFFFF)
    # Allocate payload blocks before indexes; BOM references are stable and do
    # not require a historical Apple block ordering.
    facet_blocks = []
    for name, raw_name in zip(facet_names, names):
        key_id = writer.add_block(raw_name); value_id = writer.add_block(_facet_value(identifiers[name], facet_parts[name]))
        facet_blocks.append((value_id, key_id, raw_name))
    writer.add_block(_key_format(attrs), "KEYFORMAT")
    rendition_blocks = []
    for asset, key in zip(ordered, keys):
        key_id = writer.add_block(key); value_id = writer.add_block(asset.csi)
        rendition_blocks.append((value_id, key_id, key))
    rendition_blocks.sort(key=lambda item: item[2]); facet_blocks.sort(key=lambda item: item[2])
    equal = len({len(x) for x in names}) == 1
    _add_multilevel_tree(writer, "RENDITIONS", rendition_blocks, node_size=4096, key_size=len(attrs)*2)
    _add_multilevel_tree(writer, "FACETKEYS", facet_blocks, node_size=4096, key_size=len(names[0]) if equal else 0xFFFFFFFF)
    writer.add_block(_extended_metadata(platform, target, thinning_arguments), "EXTENDED_METADATA")
    bitmap_records = []
    for name in facet_names:
        value_id = writer.add_block(BITMAP_VALUE); identifier = identifiers[name]
        bitmap_records.append((value_id, identifier, struct.pack(">I", identifier)))
    _add_multilevel_tree(writer, "BITMAPKEYS", bitmap_records, node_size=1024, key_size=0, numeric_key=True, leaf_limit=64)
    return writer.build()

def build_assets_car(assets: list[AssetRendition], *, platform: str = "macosx", target: str = "13.0", thinning_arguments: str = "") -> bytes:
    """Build a CAR with any number of facets and renditions per facet.

    Renditions sharing ``name`` share one FACETKEYS record and identifier. This
    is required for ordinary 1x/2x/3x image sets. Duplicate CoreUI keys are
    rejected because lookup would otherwise be ambiguous.
    """
    if not assets:
        raise ValueError("at least one asset is required")
    if len(assets) > 128 or len({asset.name for asset in assets}) > 128:
        return _build_assets_car_multilevel(assets, platform=platform, target=target, thinning_arguments=thinning_arguments)
    ordered = sorted(assets, key=lambda item: (item.name.encode("utf-8"), item.part, item.scale, item.csi))
    facet_names = sorted({asset.name for asset in ordered}, key=lambda item: item.encode("utf-8"))
    names = [name.encode("utf-8") for name in facet_names]
    if any(not name or len(name) > 255 for name in names):
        raise ValueError("asset names must contain 1..255 UTF-8 bytes")
    identifiers = {name: _identifier(name) for name in facet_names}
    if len(set(identifiers.values())) != len(identifiers):
        raise ValueError("asset identifier collision; rename one of the colliding assets")
    facet_parts: dict[str, int] = {}
    for asset in ordered:
        previous = facet_parts.setdefault(asset.name, asset.effective_facet_part)
        if previous != asset.effective_facet_part:
            raise ValueError(f"renditions for {asset.name!r} disagree on facet part")
    key_attributes = _select_key_attributes(ordered)
    locale_names = sorted({a.localization for a in ordered if a.localization}, key=lambda x: x.encode("utf-8"))
    locale_ids = {name: _identifier("localization:" + name) for name in locale_names}
    if len(set(locale_ids.values())) != len(locale_ids): raise ValueError("localization identifier collision")
    keys = [_rendition_key_for(asset, identifiers[asset.name], key_attributes, locale_ids.get(asset.localization, 0)) for asset in ordered]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate rendition key for the same asset, part, and scale")
    rendition_count = len(ordered); facet_count = len(facet_names)
    used_appearances = {asset.appearance for asset in ordered if asset.appearance}
    appearance_names = {0: "UIAppearanceAny", 1: "UIAppearanceDark", 2: "UIAppearanceHighContrastAny"}
    appearance_registry = sorted(
        [(appearance_names[0], 0)] + [(appearance_names[value], value) for value in used_appearances],
        key=lambda item: item[0].encode("utf-8"),
    ) if used_appearances else []
    has_appearances = bool(appearance_registry)

    # IDs 1..5 are CARHEADER and rendition/facet descriptor+root. Appearance
    # descriptor/root occupy 6..7 and each registry record uses key+value.
    prefix_next = 8 + 2 * len(appearance_registry) if has_appearances else 6
    localization_descriptor_id = prefix_next if locale_names else 0
    if locale_names: prefix_next += 2 + 2 * len(locale_names)
    facet_base = prefix_next
    key_format_id = facet_base + 2 * facet_count
    rendition_base = key_format_id + 1
    metadata_id = rendition_base + 2 * rendition_count
    bitmap_descriptor_id = metadata_id + 1
    bitmap_root_id = bitmap_descriptor_id + 1
    bitmap_value_base = bitmap_root_id + 1

    facet_entries = [(facet_base + 2 * i + 1, facet_base + 2 * i) for i in range(facet_count)]
    equal_name_size = len({len(name) for name in names}) == 1
    facet_key_size = len(names[0]) if equal_name_size else 0xFFFFFFFF
    facet_inline = names if equal_name_size else []
    rendition_records = []
    for i, (asset, key) in enumerate(zip(ordered, keys)):
        rendition_records.append((key, rendition_base + 2 * i + 1, rendition_base + 2 * i))
    rendition_records.sort(key=lambda item: item[0])
    rendition_entries = [(value_id, key_id) for _, value_id, key_id in rendition_records]
    rendition_inline = [key for key, *_ in rendition_records]
    bitmap_entries = [(bitmap_value_base + i, identifiers[name]) for i, name in enumerate(facet_names)]

    writer = BOMWriter()
    writer.add_block(_car_header(rendition_count), "CARHEADER")
    writer.add_block(_tree_descriptor(3, 4096, rendition_count, len(key_attributes) * 2), "RENDITIONS")
    writer.add_block(_leaf_many(rendition_entries, rendition_inline, 4096))
    writer.add_block(_tree_descriptor(5, 4096, facet_count, facet_key_size), "FACETKEYS")
    writer.add_block(_leaf_many(facet_entries, facet_inline, 4096))
    if has_appearances:
        appearance_entries = [(9 + 2 * i, 8 + 2 * i) for i in range(len(appearance_registry))]
        writer.add_block(_tree_descriptor(7, 4096, len(appearance_registry), 0xFFFFFFFF), "APPEARANCEKEYS")
        writer.add_block(_leaf_many(appearance_entries, [], 4096))
        for appearance_name, appearance_id in appearance_registry:
            writer.add_block(appearance_name.encode("utf-8"))
            writer.add_block(struct.pack("<H", appearance_id))
    if locale_names:
        locale_root = localization_descriptor_id + 1
        locale_entries = [(localization_descriptor_id + 3 + 2*i, localization_descriptor_id + 2 + 2*i) for i in range(len(locale_names))]
        writer.add_block(_tree_descriptor(locale_root, 4096, len(locale_names), 0xFFFFFFFF), "LOCALIZATIONKEYS")
        writer.add_block(_leaf_many(locale_entries, [], 4096))
        for locale in locale_names:
            writer.add_block(locale.encode("utf-8")); writer.add_block(struct.pack("<H", locale_ids[locale]))
    for name, name_raw in zip(facet_names, names):
        writer.add_block(name_raw)
        writer.add_block(_facet_value(identifiers[name], facet_parts[name]))
    writer.add_block(_key_format(key_attributes), "KEYFORMAT")
    for asset, key in zip(ordered, keys):
        writer.add_block(key)
        writer.add_block(asset.csi)
    writer.add_block(_extended_metadata(platform, target, thinning_arguments), "EXTENDED_METADATA")
    writer.add_block(_tree_descriptor(bitmap_root_id, 1024, facet_count, 0, True), "BITMAPKEYS")
    writer.add_block(_leaf_many(bitmap_entries, [], 1024))
    for _ in facet_names:
        writer.add_block(BITMAP_VALUE)
    return writer.build()


def build_pdf_fallback_car(name: str, pdf: bytes, png_1x: bytes, png_2x: bytes, filename: str = "image.pdf", *, png_3x: bytes | None = None, platform: str = "macosx", target: str = "13.0") -> bytes:
    """Build a preserved PDF plus Xcode-style GA8 deepmap fallbacks."""
    name_raw = name.encode("utf-8")
    if not name_raw or len(name_raw) > 255: raise ValueError("asset name must contain 1..255 UTF-8 bytes")
    identifier = _identifier(name)
    fallbacks = [(1, png_1x), (2, png_2x)]
    if png_3x is not None: fallbacks.append((3, png_3x))
    records = [(_rendition_key(identifier, 42, 1), _csi_pdf(bytes(pdf), filename))]
    records += [(_rendition_key(identifier, 0xB5, scale), _csi_png_deepmap(bytes(png), filename, scale=scale, vector_fallback=True)) for scale, png in fallbacks]
    count = len(records); metadata_id = 9 + 2 * count; bitmap_descriptor_id = metadata_id + 1; bitmap_root_id = bitmap_descriptor_id + 1; bitmap_value_id = bitmap_root_id + 1
    sorted_records = sorted(enumerate(records), key=lambda item: item[1][0])
    entries = [(10 + index * 2, 9 + index * 2) for index, _ in sorted_records]
    inline = [record[0] for _, record in sorted_records]
    writer = BOMWriter(); writer.add_block(_car_header(count), "CARHEADER")
    writer.add_block(_tree_descriptor(3, 4096, count, 16), "RENDITIONS"); writer.add_block(_leaf_many(entries, inline, 4096))
    writer.add_block(_tree_descriptor(5, 4096, 1, len(name_raw)), "FACETKEYS"); writer.add_block(_leaf(7, 6, name_raw, 4096))
    writer.add_block(name_raw); writer.add_block(_facet_value(identifier, 0xB5)); writer.add_block(_key_format(), "KEYFORMAT")
    for key, csi in records: writer.add_block(key); writer.add_block(csi)
    writer.add_block(_extended_metadata(platform, target), "EXTENDED_METADATA")
    writer.add_block(_tree_descriptor(bitmap_root_id, 1024, 1, 0, True), "BITMAPKEYS")
    writer.add_block(_leaf(bitmap_value_id, identifier, b"", 1024)); writer.add_block(BITMAP_VALUE)
    return writer.build()




def svg_renditions(name: str, svg: bytes, filename: str = "image.svg", *, fallback_scales: tuple[int, ...] = (1, 2, 3)) -> list[AssetRendition]:
    """Preserve SVG and automatically rasterize deepmap fallbacks."""
    vector = AssetRendition(name, _csi_svg(bytes(svg), filename), 42, 181)
    if not fallback_scales:
        return [vector]
    if any(scale not in (1, 2, 3) for scale in fallback_scales):
        raise ValueError("SVG fallback scales must be 1, 2, or 3")
    try:
        import cairosvg
    except ImportError as exc:
        raise ValueError("automatic SVG fallback generation requires cairosvg") from exc
    result = [vector]
    for scale in fallback_scales:
        png = cairosvg.svg2png(bytestring=bytes(svg), scale=scale)
        result.append(AssetRendition(name, _csi_png_deepmap(png, filename, scale=scale, vector_fallback=True), 181, 181, scale=scale))
    return result


def build_svg_car(name: str, svg: bytes, filename: str = "image.svg", *, fallback_scales: tuple[int, ...] = (1, 2, 3), platform: str = "iphoneos", target: str = "15.0") -> bytes:
    return build_assets_car(svg_renditions(name, svg, filename, fallback_scales=fallback_scales), platform=platform, target=target)


def cbck_png_rendition(name: str, png: bytes, filename: str = "image.png", *, scale: int = 1, idiom: str | int = 0) -> AssetRendition:
    """Build an ordinary image rendition using chunked CBCK/LZFSE storage."""
    idioms = {"universal": 0, "iphone": 1, "phone": 1, "ipad": 2, "pad": 2, "tv": 3, "car": 4, "carplay": 4, "watch": 5, "marketing": 6, "mac": 7, "vision": 8, "visionos": 8}
    try: idiom_id = idioms[idiom] if isinstance(idiom, str) else int(idiom)
    except (KeyError, ValueError) as exc: raise ValueError(f"unsupported idiom: {idiom}") from exc
    if scale not in (1, 2, 3) or idiom_id not in range(9):
        raise ValueError("invalid CBCK scale or idiom")
    return AssetRendition(name, _csi_png_cbck(bytes(png), filename, scale=scale), 181, scale=scale, idiom=idiom_id)


def layered_image_renditions(name: str, layers: list[bytes], *, idiom: str | int = 3, scale: int = 1, depths: list[int] | None = None) -> list[AssetRendition]:
    """Create ordered CoreUI layer-key renditions for tvOS/visionOS image stacks."""
    if not layers: raise ValueError("layered image needs at least one layer")
    idioms={"tv":3,"vision":8,"visionos":8,"universal":0}
    try: idiom_id=idioms[idiom] if isinstance(idiom,str) else int(idiom)
    except (KeyError,ValueError) as exc: raise ValueError(f"unsupported layered-image idiom: {idiom}") from exc
    if idiom_id not in (0,3,8): raise ValueError("layered images support universal, tv, or vision idioms")
    if depths is None: depths = list(range(1, len(layers) + 1)) if idiom_id == 8 else [0] * len(layers)
    if len(depths) != len(layers) or any(not 0 <= x <= 65535 for x in depths): raise ValueError("invalid layer depth list")
    return [AssetRendition(name,_csi_png_deepmap(bytes(png),f"{name}-layer-{index}.png",scale=scale),181,scale=scale,idiom=idiom_id,layer=index,dimension2=depths[index-1])
            for index,png in enumerate(layers,1)]


def build_layered_icon_car(name: str, layers: list[bytes], *, platform: str = "appletvos", target: str = "15.0", scale: int = 1, depths: list[int] | None = None) -> bytes:
    idiom="vision" if platform.lower() in ("xros","xrsimulator","visionos") else "tv"
    return build_assets_car(layered_image_renditions(name,layers,idiom=idiom,scale=scale,depths=depths),platform=platform,target=target)


def solid_image_stack_aggregate_renditions(name: str, layers: list[tuple[str, bytes]], *, platform: str = "xros", scale: int = 2, canvas_points: tuple[int, int] | None = None) -> list[AssetRendition]:
    """Experimental aggregate-oriented SolidImageStack rendition set.

    This models the currently observed public visionOS `solidimagestack` oracle:
    one layout-1018 aggregate metadata rendition, ordinary image renditions for
    each content layer, and texture-oriented 1007/1008 side renditions for two
    dimension1 modes. The exact Apple writer is still more complex.
    """
    if len(layers) < 1:
        raise ValueError("solid image stack needs at least one layer")
    idiom = 8 if platform.lower() in ("xros", "xrsimulator", "visionos") else 3
    if idiom != 8:
        raise ValueError("aggregate solid image stack is currently enabled for visionOS only")
    child_names = [f"{name}/{layer_name}/Content" for layer_name, _ in layers]
    child_ids = [_identifier(child_name) for child_name in child_names]
    width = height = None
    image_renditions: list[AssetRendition] = []
    aggregate: list[AssetRendition] = []
    for (layer_name, png_bytes), child_name, child_id in zip(layers, child_names, child_ids):
        w, h = png_dimensions(png_bytes)
        width = w if width is None else width
        height = h if height is None else height
        image_renditions.append(AssetRendition(child_name, _csi_png_deepmap(bytes(png_bytes), 'content.png', scale=scale), 181, scale=scale, idiom=idiom, identifier_override=child_id))
        for dim1, payload_value, mode_field in ((1, 55, 0x80000), (2, 32, 0x40000)):
            ref_pairs = ((1, 41), (2, 181), (8, dim1), (12, scale), (17, child_id), (15, idiom), (0, 0))
            ref = TextureReference(payload_value, 0, 1, 1, 0x1C, ref_pairs)
            aux = TextureAuxiliaryFlag(b'\0'*8 + (b'\1' if layer_name == 'Back' and dim1 == 1 else b'\0') + b'\0'*4, (0, 0, 1 if layer_name == 'Back' and dim1 == 1 else 0))
            aggregate.append(AssetRendition(child_name, _csi_texture_reference('content.png', ref, width=w, height=h, scale=scale, auxiliary_flag=aux), 0, 181, scale=scale, idiom=idiom, dimension1=dim1, element=41, identifier_override=child_id))
            aggregate.append(AssetRendition(child_name, _csi_texture_data_from_png(bytes(png_bytes), 'content.png', width=w, height=h, scale=scale, mode_field=mode_field), 181, 181, scale=scale, idiom=idiom, dimension1=dim1, element=41, identifier_override=child_id))
    if width is None or height is None:
        raise ValueError("solid image stack needs image content")
    if canvas_points is None:
        canvas_points = (width // scale, height // scale)
    aggregate.insert(0, AssetRendition(name, _csi_solid_image_stack('Contents.json', canvas_points=canvas_points, scale=scale, identifier_values=child_ids), 181, 181, idiom=0, scale=1))
    return aggregate + image_renditions


def build_solid_image_stack_aggregate_car(name: str, layers: list[tuple[str, bytes]], *, platform: str = 'xros', target: str = '1.0', scale: int = 2, canvas_points: tuple[int, int] | None = None) -> bytes:
    return build_assets_car(solid_image_stack_aggregate_renditions(name, layers, platform=platform, scale=scale, canvas_points=canvas_points), platform=platform, target=target)


WATCH_COMPLICATION_FAMILIES = {"circularSmall":1,"extraLarge":2,"graphicBezel":3,"graphicCircular":4,"graphicCorner":5,"graphicExtraLarge":6,"graphicRectangular":7,"modularLarge":8,"modularSmall":9,"utilitarianLarge":10,"utilitarianSmall":11,"utilitarianSmallFlat":12}
WATCH_COMPLICATION_ROLES = {"background":1,"foreground":2,"mask":3,"ring":4,"template":5}


def watch_complication_renditions(name: str, images: list[bytes], *, scale: int = 2, families: list[str] | None = None, roles: list[str] | None = None) -> list[AssetRendition]:
    """Encode watch family in subtype and role in dimension2 keys."""
    if not images: raise ValueError("complication needs at least one image")
    if families is None:
        available = tuple(WATCH_COMPLICATION_FAMILIES)
        if len(images) > len(available): raise ValueError("too many complication images without explicit families")
        families = list(available[:len(images)])
    roles = roles or ["template"] * len(images)
    if len(families)!=len(images) or len(roles)!=len(images): raise ValueError("complication metadata count mismatch")
    try: pairs=[(WATCH_COMPLICATION_FAMILIES[f],WATCH_COMPLICATION_ROLES[r]) for f,r in zip(families,roles)]
    except KeyError as exc: raise ValueError(f"unsupported complication family or role: {exc.args[0]}") from exc
    return [AssetRendition(name,_csi_png_deepmap(bytes(png),f"{name}-{families[i-1]}-{roles[i-1]}.png",scale=scale),181,scale=scale,idiom=5,subtype=family,dimension2=role)
            for i,(png,(family,role)) in enumerate(zip(images,pairs),1)]


def build_watch_complication_car(name: str, images: list[bytes], *, target: str = "8.0", scale: int = 2, families: list[str] | None = None, roles: list[str] | None = None) -> bytes:
    return build_assets_car(watch_complication_renditions(name,images,scale=scale,families=families,roles=roles),platform="watchos",target=target)


APP_ICON_IDIOMS = {
    "iphoneos": (1, 2), "iphonesimulator": (1, 2), "ios": (1, 2),
    "appletvos": (3,), "appletvsimulator": (3,), "tvos": (3,),
    "watchos": (5,), "watchsimulator": (5,),
    "macosx": (7,), "macos": (7,),
    "xros": (8,), "xrsimulator": (8,), "visionos": (8,),
}


def app_icon_renditions(name: str, png: bytes, filename: str = "icon.png", *, platform: str = "iphoneos") -> list[AssetRendition]:
    """Return platform-specific MSIS and CBCK records for a modern AppIcon."""
    try: idioms = APP_ICON_IDIOMS[platform.lower()]
    except KeyError as exc: raise ValueError(f"unsupported AppIcon platform: {platform}") from exc
    csi = _csi_png_cbck(bytes(png), filename)
    records: list[AssetRendition] = []
    for idiom in idioms:
        records.append(AssetRendition(name, _csi_msis(filename), 218, 220, idiom=idiom))
        records.append(AssetRendition(name, csi, 220, 220, idiom=idiom, dimension2=1))
    return records


def build_app_icon_car(name: str, png: bytes, filename: str = "icon.png", *, platform: str = "iphoneos", target: str = "15.0") -> bytes:
    return build_assets_car(app_icon_renditions(name, png, filename, platform=platform), platform=platform, target=target)


def data_rendition(name: str, data: bytes, uti: str = "public.data", *, idiom: str | int = 0, appearance: str | int = 0, localization: str | None = None) -> AssetRendition:
    idiom_id, appearance_id = _selector_ids(idiom, appearance)
    return AssetRendition(name, _csi_data(bytes(data), uti), 0xB5, idiom=idiom_id, appearance=appearance_id, localization=localization)


def _selector_ids(idiom: str | int = 0, appearance: str | int = 0) -> tuple[int, int]:
    idioms = {"universal": 0, "iphone": 1, "phone": 1, "ipad": 2, "pad": 2, "tv": 3, "car": 4, "carplay": 4, "watch": 5, "marketing": 6, "mac": 7, "vision": 8, "visionos": 8}
    appearances = {"any": 0, "light": 0, "dark": 1, "high-contrast": 2, "high": 2}
    try: idiom_id = idioms[idiom] if isinstance(idiom, str) else int(idiom)
    except (KeyError, ValueError) as exc: raise ValueError(f"unsupported idiom: {idiom}") from exc
    try: appearance_id = appearances[appearance] if isinstance(appearance, str) else int(appearance)
    except (KeyError, ValueError) as exc: raise ValueError(f"unsupported appearance: {appearance}") from exc
    if idiom_id not in range(9): raise ValueError("invalid idiom")
    if appearance_id not in (0, 1, 2): raise ValueError("invalid appearance")
    return idiom_id, appearance_id


def jpeg_rendition(name: str, data: bytes, filename: str = "image.jpg", *, scale: int = 1, idiom: str | int = 0, appearance: str | int = 0, localization: str | None = None) -> AssetRendition:
    if scale not in (1, 2, 3): raise ValueError("image scale must be 1, 2, or 3")
    idiom_id, appearance_id = _selector_ids(idiom, appearance)
    return AssetRendition(name, _csi_jpeg(bytes(data), filename, scale), 0xB5, scale=scale, idiom=idiom_id, appearance=appearance_id, localization=localization)


def heif_rendition(name: str, data: bytes, filename: str = "image.heic", *, scale: int = 1, idiom: str | int = 0, appearance: str | int = 0, localization: str | None = None) -> AssetRendition:
    if scale not in (1, 2, 3): raise ValueError("image scale must be 1, 2, or 3")
    idiom_id, appearance_id = _selector_ids(idiom, appearance)
    return AssetRendition(name, _csi_heif(bytes(data), filename, scale), 0xB5, scale=scale, idiom=idiom_id, appearance=appearance_id, localization=localization)


def png_rendition(name: str, data: bytes, filename: str = "image.png", *, scale: int = 1, idiom: str | int = 0, appearance: str | int = 0, localization: str | None = None) -> AssetRendition:
    if scale not in (1, 2, 3):
        raise ValueError("image scale must be 1, 2, or 3")
    idioms = {"universal": 0, "iphone": 1, "phone": 1, "ipad": 2, "pad": 2, "tv": 3, "car": 4, "carplay": 4, "watch": 5, "marketing": 6, "mac": 7, "vision": 8, "visionos": 8}
    appearances = {"any": 0, "light": 0, "dark": 1, "high-contrast": 2, "high": 2}
    try: idiom_id = idioms[idiom] if isinstance(idiom, str) else int(idiom)
    except (KeyError, ValueError) as exc: raise ValueError(f"unsupported idiom: {idiom}") from exc
    try: appearance_id = appearances[appearance] if isinstance(appearance, str) else int(appearance)
    except (KeyError, ValueError) as exc: raise ValueError(f"unsupported appearance: {appearance}") from exc
    if idiom_id not in range(9): raise ValueError("enabled idioms are universal, iphone, ipad, tv, car, watch, marketing, mac, and vision")
    if appearance_id not in (0, 1, 2): raise ValueError("enabled appearances are any/light, dark, and high-contrast")
    if localization is not None and (not localization or len(localization.encode("utf-8")) > 255): raise ValueError("invalid localization tag")
    return AssetRendition(name, _csi_png_deepmap(bytes(data), filename, scale=scale), 0xB5, scale=scale, idiom=idiom_id, appearance=appearance_id, localization=localization)


def palette_png_rendition(name: str, data: bytes, filename: str = "image.png", *, scale: int = 1, idiom: str | int = 0, appearance: str | int = 0, localization: str | None = None) -> AssetRendition:
    """Build a legacy quantized `palette-img` rendition from an indexed PNG input."""
    if scale not in (1, 2, 3):
        raise ValueError("image scale must be 1, 2, or 3")
    idiom_id, appearance_id = _selector_ids(idiom, appearance)
    if localization is not None and (not localization or len(localization.encode("utf-8")) > 255):
        raise ValueError("invalid localization tag")
    return AssetRendition(name, _csi_png_palette_img(bytes(data), filename, scale=scale), 0xB5, scale=scale, idiom=idiom_id, appearance=appearance_id, localization=localization)


SYMBOL_WEIGHTS = {"Ultralight":1, "Thin":2, "Light":3, "Regular":4, "Medium":5, "Semibold":6, "Bold":7, "Heavy":8, "Black":9}
SYMBOL_SIZES = {"S":1, "M":2, "L":3}


def symbol_template_renditions(name: str, svg: bytes, filename: str = "symbol.svg", *, deployment_target: int = 0) -> list[AssetRendition]:
    """Expand SF Symbols template groups such as ``Regular-M`` into glyph records."""
    import xml.etree.ElementTree as ET
    try: root = ET.fromstring(svg)
    except ET.ParseError as exc: raise ValueError(f"invalid symbol SVG: {exc}") from exc
    found: list[tuple[int,int,bytes]] = []
    for element in root.iter():
        ident = element.attrib.get("id", "")
        if "-" not in ident: continue
        weight_name, size_name = ident.rsplit("-", 1)
        if weight_name not in SYMBOL_WEIGHTS or size_name not in SYMBOL_SIZES: continue
        # Preserve definitions/style and the selected glyph. CoreUI accepts a
        # normal SVG payload per weight/size; template-only guide groups are omitted.
        wrapper = ET.Element(root.tag, dict(root.attrib))
        for child in root:
            if child.tag.rsplit("}",1)[-1] == "defs": wrapper.append(ET.fromstring(ET.tostring(child)))
        wrapper.append(ET.fromstring(ET.tostring(element)))
        found.append((SYMBOL_WEIGHTS[weight_name], SYMBOL_SIZES[size_name], ET.tostring(wrapper, encoding="utf-8", xml_declaration=True)))
    if not found:
        raise ValueError("symbol template has no recognized weight-size glyph groups")
    return [symbol_rendition(name, payload, filename, weight=weight, size=size, deployment_target=deployment_target)
            for weight,size,payload in sorted(found)]


def build_symbol_template_car(name: str, svg: bytes, filename: str = "symbol.svg", *, platform: str = "macosx", target: str = "13.0") -> bytes:
    return build_assets_car(symbol_template_renditions(name, svg, filename), platform=platform, target=target)


def symbol_rendition(name: str, data: bytes, filename: str = "symbol.svg", *, weight: int = 4, size: int = 2, deployment_target: int = 0) -> AssetRendition:
    if weight not in range(1, 10): raise ValueError("symbol weight must be 1..9")
    if size not in range(1, 4): raise ValueError("symbol size must be 1..3")
    return AssetRendition(name, _csi_symbol_svg(bytes(data), filename), 59, 59, glyph_weight=weight, glyph_size=size, deployment_target=deployment_target)

def build_symbol_car(name: str, svg: bytes, filename: str = "symbol.svg", *, platform: str = "macosx", target: str = "13.0", weight: int = 4, size: int = 2) -> bytes:
    return build_assets_car([symbol_rendition(name, svg, filename, weight=weight, size=size)], platform=platform, target=target)


def pdf_rendition(name: str, data: bytes, filename: str = "image.pdf") -> AssetRendition:
    # Preserved-vector rendition uses part 42 while the facet advertises the
    # ordinary image part (181), matching Xcode's CoreUI key relationship.
    return AssetRendition(name, _csi_pdf(bytes(data), filename), 42, 0xB5)


def build_data_car(name: str, data: bytes, uti: str = "public.data", *, platform: str = "macosx", target: str = "13.0") -> bytes:
    return build_assets_car([data_rendition(name, data, uti)], platform=platform, target=target)


def build_jpeg_car(name: str, data: bytes, filename: str = "image.jpg", *, platform: str = "macosx", target: str = "13.0") -> bytes:
    return build_assets_car([jpeg_rendition(name, data, filename)], platform=platform, target=target)


def build_heif_car(name: str, data: bytes, filename: str = "image.heic", *, platform: str = "macosx", target: str = "13.0") -> bytes:
    return build_assets_car([heif_rendition(name, data, filename)], platform=platform, target=target)


def build_png_car(name: str, data: bytes, filename: str = "image.png", *, platform: str = "macosx", target: str = "13.0") -> bytes:
    return build_assets_car([png_rendition(name, data, filename)], platform=platform, target=target)


def build_palette_img_car(name: str, data: bytes, filename: str = "image.png", *, platform: str = "macosx", target: str = "13.0") -> bytes:
    return build_assets_car([palette_png_rendition(name, data, filename)], platform=platform, target=target)


def build_pdf_car(name: str, data: bytes, filename: str = "image.pdf", *, platform: str = "macosx", target: str = "13.0") -> bytes:
    return build_assets_car([pdf_rendition(name, data, filename)], platform=platform, target=target)


def color_rendition(name: str, red: float, green: float, blue: float, alpha: float = 1.0, *, color_space: str = "srgb", idiom: str | int = 0, appearance: str | int = 0) -> AssetRendition:
    components = (float(red), float(green), float(blue), float(alpha))
    if any(not 0.0 <= value <= 1.0 for value in components):
        raise ValueError("color components must be between 0 and 1")
    color_space_ids = {"srgb": 1, "display-p3": 3}
    try:
        color_space_id = color_space_ids[color_space]
    except KeyError as exc:
        raise ValueError(f"unsupported color space: {color_space}") from exc
    idiom_id, appearance_id = _selector_ids(idiom, appearance)
    return AssetRendition(name, _csi_color(name, components, color_space_id), 0xD9, idiom=idiom_id, appearance=appearance_id)


def build_color_car(name: str, red: float, green: float, blue: float, alpha: float = 1.0, *, color_space: str = "srgb", platform: str = "macosx", target: str = "13.0") -> bytes:
    return build_assets_car(
        [color_rendition(name, red, green, blue, alpha, color_space=color_space)],
        platform=platform, target=target,
    )


def write_data_car(path: Path | str, name: str, data: bytes, uti: str = "public.data", **kwargs) -> None:
    Path(path).write_bytes(build_data_car(name, data, uti, **kwargs))


def write_jpeg_car(path: Path | str, name: str, data: bytes, filename: str = "image.jpg", **kwargs) -> None:
    Path(path).write_bytes(build_jpeg_car(name, data, filename, **kwargs))


def write_heif_car(path: Path | str, name: str, data: bytes, filename: str = "image.heic", **kwargs) -> None:
    Path(path).write_bytes(build_heif_car(name, data, filename, **kwargs))


def write_color_car(path: Path | str, name: str, red: float, green: float, blue: float, alpha: float = 1.0, **kwargs) -> None:
    Path(path).write_bytes(build_color_car(name, red, green, blue, alpha, **kwargs))
