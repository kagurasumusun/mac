"""Packed CoreUI atlas metadata and deterministic shelf packer."""
from __future__ import annotations
from dataclasses import dataclass
import struct
import zlib

from .carwriter import AssetRendition, _csi_png_deepmap, _fixed, _identifier, build_assets_car


@dataclass(frozen=True)
class AtlasKeyToken:
    attribute: int
    value: int


@dataclass(frozen=True)
class AtlasLink:
    x: int
    y: int
    width: int
    height: int
    tokens: tuple[AtlasKeyToken, ...]
    variant: str = "generic"
    header_u16: int = 0
    header_u32: int = 0


@dataclass(frozen=True)
class AtlasNameList:
    names: tuple[str, ...]


@dataclass(frozen=True)
class AtlasTrim:
    original_width: int
    original_height: int
    origin_x: int
    origin_y: int
    trimmed_width: int
    trimmed_height: int


def parse_atlas_link(raw: bytes) -> AtlasLink:
    """Parse CoreUI TLV 1010 (INLK), supporting both observed public variants."""
    if len(raw) < 26 or raw[:4] != b"KLNI":
        raise ValueError("invalid atlas link magic or truncated header")
    version, x, y, width, height = struct.unpack_from("<5I", raw, 4)
    if version != 0 or not width or not height:
        raise ValueError("unsupported atlas link header")
    tokens = []
    if raw[24:26] == b"\0\0":
        if (len(raw) - 26) % 4:
            raise ValueError("invalid atlas token alignment")
        for off in range(26, len(raw), 4):
            attribute, value = struct.unpack_from("<2H", raw, off)
            if attribute == value == 0:
                break
            if attribute > 27:
                raise ValueError("atlas token attribute is out of range")
            tokens.append(AtlasKeyToken(attribute, value))
        else:
            raise ValueError("atlas token list has no terminator")
        return AtlasLink(x, y, width, height, tuple(tokens))
    if len(raw) < 34 or (len(raw) - 30) % 4:
        raise ValueError("invalid atlas token alignment")
    header_u16 = struct.unpack_from("<H", raw, 24)[0]
    header_u32 = struct.unpack_from("<I", raw, 26)[0]
    for off in range(30, len(raw), 4):
        attribute, value = struct.unpack_from("<2H", raw, off)
        if attribute == value == 0:
            break
        if attribute > 27:
            raise ValueError("atlas token attribute is out of range")
        tokens.append(AtlasKeyToken(attribute, value))
    else:
        raise ValueError("atlas token list has no terminator")
    return AtlasLink(x, y, width, height, tuple(tokens), variant="explicit", header_u16=header_u16, header_u32=header_u32)


def build_atlas_link(link: AtlasLink) -> bytes:
    if min(link.x, link.y) < 0 or not 0 < link.width <= 65535 or not 0 < link.height <= 65535:
        raise ValueError("invalid atlas rectangle")
    out = bytearray(b"KLNI" + struct.pack("<5I", 0, link.x, link.y, link.width, link.height))
    if link.variant == "generic":
        out += b"\0\0"
        for token in link.tokens:
            if not 0 < token.attribute <= 27 or not 0 <= token.value <= 65535:
                raise ValueError("invalid atlas key token")
            out += struct.pack("<2H", token.attribute, token.value)
        out += b"\0\0\0\0"
        return bytes(out)
    if link.variant == "explicit":
        out += struct.pack("<HI", link.header_u16, link.header_u32)
        for token in link.tokens:
            if not 0 < token.attribute <= 27 or not 0 <= token.value <= 65535:
                raise ValueError("invalid atlas key token")
            out += struct.pack("<2H", token.attribute, token.value)
        out += b"\0\0\0\0"
        return bytes(out)
    raise ValueError(f"unsupported atlas link variant: {link.variant}")


def _linked_csi(filename: str, link: AtlasLink, scale: int, *, trim_tlv: bytes | None = None, source_size: tuple[int, int] | None = None) -> bytes:
    h = bytearray(184)
    h[:4] = b"ISTC"
    struct.pack_into("<5I", h, 4, 1, 16, link.width, link.height, scale * 100)
    h[24:28] = b" 8AG"  # little-endian GA8
    struct.pack_into("<I2H", h, 32, 0, 1003, 0)
    h[40:168] = _fixed(filename, 128)
    source_width, source_height = source_size or (link.width, link.height)
    parts = [
        struct.pack("<2I5I", 1001, 20, 1, 0, 0, source_width, source_height),
        struct.pack("<2I7I", 1003, 28, 1, 0, 0, 0, 0, link.width, link.height),
        struct.pack("<2I", 1010, len(build_atlas_link(link))) + build_atlas_link(link),
        struct.pack("<2I8s", 1004, 8, b"\0\0\0\0\0\0\x80?"),
        struct.pack("<2II", 1006, 4, 1),
    ]
    if trim_tlv is not None:
        parts.append(trim_tlv)
    tlvs = b"".join(parts)
    struct.pack_into("<4I", h, 168, len(tlvs), 1, 0, 0)
    return bytes(h)+tlvs


def parse_atlas_name_list(raw: bytes) -> AtlasNameList:
    if len(raw) < 8:
        raise ValueError("atlas name-list payload is truncated")
    count, _reserved = struct.unpack_from("<2I", raw, 0)
    cursor = 8
    names: list[str] = []
    for _ in range(count):
        if cursor + 4 > len(raw):
            raise ValueError("atlas name-list entry header is truncated")
        length = struct.unpack_from("<I", raw, cursor)[0]
        cursor += 4
        if cursor + length > len(raw):
            raise ValueError("atlas name-list entry payload is truncated")
        names.append(raw[cursor:cursor + length].decode("utf-8", "replace"))
        cursor += length
    if cursor != len(raw):
        raise ValueError("atlas name-list payload has trailing bytes")
    return AtlasNameList(tuple(names))


def _atlas_name_list_tlv(names: list[str]) -> bytes:
    payload = bytearray(struct.pack("<2I", len(names), 0))
    for name in names:
        raw = name.encode("utf-8")
        payload += struct.pack("<I", len(raw)) + raw
    return struct.pack("<2I", 1013, len(payload)) + bytes(payload)


def _atlas_metadata_csi(names: list[str], *, scale: int = 1) -> bytes:
    h = bytearray(184)
    h[:4] = b"ISTC"
    struct.pack_into("<5I", h, 4, 1, 0, 0, 0, scale * 100)
    struct.pack_into("<I2H", h, 32, 0, 1005, 0)
    h[40:168] = _fixed("CoreStructuredImage", 128)
    tlvs = b"".join((
        struct.pack("<2I8s", 1004, 8, b"\0" * 8),
        struct.pack("<2II", 1006, 4, 1),
        _atlas_name_list_tlv(names),
    ))
    struct.pack_into("<4I", h, 168, len(tlvs), 1, 0, 0)
    return bytes(h) + tlvs


def _png_rgba(width: int, height: int, pixels: bytes) -> bytes:
    def chunk(t: bytes, d: bytes): return struct.pack(">I", len(d))+t+d+struct.pack(">I", zlib.crc32(t+d) & 0xffffffff)
    rows = b"".join(b"\0"+pixels[y*width*4:(y+1)*width*4] for y in range(height))
    return b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))+chunk(b"IDAT", zlib.compress(rows, 9))+chunk(b"IEND", b"")


def _alpha_bbox(width: int, height: int, rgba: bytes) -> tuple[int, int, int, int]:
    xs = []
    ys = []
    if len(rgba) != width * height * 4:
        raise ValueError("rgba buffer length does not match atlas dimensions")
    for y in range(height):
        row = rgba[y*width*4:(y+1)*width*4]
        for x in range(width):
            if row[x*4+3]:
                xs.append(x)
                ys.append(y)
    if not xs:
        return (0, 0, width, height)
    return (min(xs), min(ys), max(xs)+1, max(ys)+1)


def _crop_rgba(width: int, height: int, rgba: bytes, bbox: tuple[int, int, int, int]) -> tuple[int, int, bytes]:
    x0, y0, x1, y1 = bbox
    out_w, out_h = x1 - x0, y1 - y0
    out = bytearray(out_w * out_h * 4)
    for row in range(out_h):
        src = ((y0 + row) * width + x0) * 4
        dst = row * out_w * 4
        out[dst:dst + out_w*4] = rgba[src:src + out_w*4]
    return out_w, out_h, bytes(out)


def parse_atlas_trim(raw: bytes) -> AtlasTrim:
    if len(raw) != 32:
        raise ValueError("atlas trim payload length is invalid")
    tag, reserved, original_width, original_height, origin_x, origin_y, trimmed_width, trimmed_height = struct.unpack("<8I", raw)
    if tag != 1011 or reserved != 0:
        raise ValueError("atlas trim payload header is invalid")
    return AtlasTrim(original_width, original_height, origin_x, origin_y, trimmed_width, trimmed_height)


def _explicit_trim_tlv(original_width: int, original_height: int, bbox: tuple[int, int, int, int]) -> bytes:
    x0, y0, x1, y1 = bbox
    trimmed_w, trimmed_h = x1 - x0, y1 - y0
    payload = struct.pack("<8I", 1011, 0, original_width, original_height, x0, y0, trimmed_w, trimmed_h)
    return struct.pack("<2I", 1011, len(payload)) + payload


def packed_atlas_renditions(
    images: dict[str, bytes],
    *,
    scale: int = 1,
    max_width: int = 1024,
    max_height: int = 1024,
    sort_by: str = "name",
    deployment_token: int = 5,
    style: str = "generic",
    atlas_name: str = "Atlas",
) -> list[AssetRendition]:
    """Return atlas renditions without wrapping them in a CAR."""
    from .carwriter import _decode_png_8bit
    if not images:
        raise ValueError("atlas needs at least one image")
    if style not in ("generic", "explicit"):
        raise ValueError("unsupported atlas style")
    if not 0 <= deployment_token <= 65535:
        raise ValueError("invalid atlas deployment token")
    decoded = []
    for name, data in images.items():
        w, h, ct, pix, _ = _decode_png_8bit(data)
        if ct == 6:
            rgba = pix
        elif ct == 4:
            rgba = b"".join(bytes((g, g, g, a)) for g, a in zip(pix[::2], pix[1::2]))
        elif ct == 2:
            rgba = b"".join(bytes((r, g, b, 255)) for r, g, b in zip(pix[::3], pix[1::3], pix[2::3]))
        else:
            raise ValueError("indexed atlas input is not enabled")
        if w > max_width or h > max_height:
            raise ValueError("atlas item exceeds page bounds")
        decoded.append((name, w, h, rgba))

    if sort_by == "name":
        decoded.sort(key=lambda x: x[0])
    elif sort_by in ("height", "height_desc"):
        decoded.sort(key=lambda x: (-x[2], -x[1], x[0]))
    elif sort_by in ("width", "width_desc"):
        decoded.sort(key=lambda x: (-x[1], -x[2], x[0]))
    elif sort_by in ("area", "area_desc"):
        decoded.sort(key=lambda x: (-x[1]*x[2], -x[2], x[0]))
    elif sort_by in ("max_dim", "max_dim_desc"):
        decoded.sort(key=lambda x: (-max(x[1], x[2]), -x[2], x[0]))
    else:
        raise ValueError(f"unsupported atlas sorting heuristic: {sort_by}")

    # Each placement carries a 1-based page dimension used by INLK tokens.
    x = y = row_h = 0
    page = 1
    placements = []
    for name, w, h, pix in decoded:
        if x and x+w > max_width:
            x = 0
            y += row_h
            row_h = 0
        if y+h > max_height:
            page += 1
            x = y = row_h = 0
        placements.append((page, name, x, y, w, h, pix, (0, 0, 0, 0), w, h))
        x += w
        row_h = max(row_h, h)

    if style == "explicit":
        if page != 1:
            raise ValueError("explicit atlas style currently supports one page")
        placements = []
        x = 2
        top = 2
        for name, w, h, pix in decoded:
            bbox = _alpha_bbox(w, h, pix)
            cw, ch, cpix = _crop_rgba(w, h, pix, bbox)
            placements.append((1, name, x, top, cw, ch, cpix, bbox, w, h))
            x += cw + 2
        aw = max(px+w for _, _, px, _, w, _, _, _, _, _ in placements) + 1
        ah = max(py+h for _, _, _, py, _, h, _, _, _, _ in placements) + 2
        canvas = bytearray(aw*ah*4)
        for _, _, px, py, w, h, pix, _, _, _ in placements:
            for row in range(h):
                canvas[((py+row)*aw+px)*4:((py+row)*aw+px+w)*4] = pix[row*w*4:(row+1)*w*4]
        page_name = "ZZZZExplicitlyPackedAsset-1.0.0-gamut0"
        page_png = _png_rgba(aw, ah, bytes(canvas))
        page_csi = bytearray(_csi_png_deepmap(page_png, page_name, scale=scale))
        struct.pack_into("<H", page_csi, 36, 1004)
        struct.pack_into("<I", page_csi, 8, 0)
        names = [name for _, name, _, _, _, _, _, _, _, _ in placements]
        parent_identifier = _identifier(atlas_name)
        records = [
            AssetRendition(atlas_name, _atlas_metadata_csi(names, scale=scale), 127, 181,
                           scale=scale, element=9, identifier_override=parent_identifier),
            AssetRendition(atlas_name, bytes(page_csi), 181, scale=scale, element=9, identifier_override=parent_identifier),
        ]
        for _page_dimension, name, px, py, w, h, _pix, bbox, ow, oh in placements:
            tokens = (AtlasKeyToken(1, 9), AtlasKeyToken(2, 181), AtlasKeyToken(12, scale), AtlasKeyToken(17, parent_identifier))
            link = AtlasLink(px, py, w, h, tokens, variant="explicit", header_u16=12, header_u32=20)
            trim_tlv = None if bbox == (0, 0, ow, oh) else _explicit_trim_tlv(ow, oh, bbox)
            records.append(AssetRendition(name, _linked_csi(name+".png", link, scale, trim_tlv=trim_tlv, source_size=(ow, oh)), 181, scale=scale))
        return records

    records = []
    for page_dimension in range(1, page+1):
        page_items = [p for p in placements if p[0] == page_dimension]
        aw = max(px+w for _, _, px, _, w, _, _, _, _, _ in page_items)
        ah = max(py+h for _, _, _, py, _, h, _, _, _, _ in page_items)
        canvas = bytearray(aw*ah*4)
        for _, _, px, py, w, h, pix, _, _, _ in page_items:
            for row in range(h):
                canvas[((py+row)*aw+px)*4:((py+row)*aw+px+w)*4] = pix[row*w*4:(row+1)*w*4]
        page_name = f"ZZZZPackedAsset-1.0.{page_dimension}-gamut0"
        page_png = _png_rgba(aw, ah, bytes(canvas))
        page_csi = bytearray(_csi_png_deepmap(page_png, page_name, scale=scale))
        struct.pack_into("<H", page_csi, 36, 1004)
        struct.pack_into("<I", page_csi, 8, 0)
        records.append(AssetRendition(page_name, bytes(page_csi), 181, scale=scale, element=9, identifier_override=0,
                       dimension1=page_dimension, atlas_linked=True, deployment_target=deployment_token))
    for page_dimension, name, px, py, w, h, _, _, _, _ in placements:
        tokens_page = (AtlasKeyToken(24, 0), AtlasKeyToken(1, 9), AtlasKeyToken(2, 181), AtlasKeyToken(8, page_dimension), AtlasKeyToken(12, scale), AtlasKeyToken(25, deployment_token))
        link = AtlasLink(px, py, w, h, tokens_page)
        records.append(AssetRendition(name, _linked_csi(name+".png", link, scale), 181,
                       scale=scale, atlas_linked=True, deployment_target=deployment_token))
    return records


def packed_watch_complication_renditions(
    images: list[tuple[str, bytes]],
    *,
    scale: int = 2,
    atlas_name: str = "Complication",
) -> list[AssetRendition]:
    """Approximate the public .complicationset packed-page output observed from Apple.

    The current public oracle shows one explicit packed page named
    ``ZZZZPackedAsset-2.1.0-gamut0`` and explicit `KLNI` links carrying
    tokens `(1,9)`, `(2,181)`, `(12,scale)`, `(15,5)`.
    """
    from .carwriter import _decode_png_8bit
    if not images:
        raise ValueError("watch complication atlas needs at least one image")
    decoded = []
    for name, data in images:
        w, h, ct, pix, _ = _decode_png_8bit(data)
        if ct == 6:
            rgba = pix
        elif ct == 4:
            rgba = b"".join(bytes((g, g, g, a)) for g, a in zip(pix[::2], pix[1::2]))
        elif ct == 2:
            rgba = b"".join(bytes((r, g, b, 255)) for r, g, b in zip(pix[::3], pix[1::3], pix[2::3]))
        else:
            raise ValueError("watch complication atlas input must be direct-color PNG")
        decoded.append((name, w, h, rgba))
    # Column-major 2-row packing matches the current public oracle for three roles.
    positions = []
    row_height = max(h for _, _, h, _ in decoded)
    col_width = max(w for _, w, _, _ in decoded)
    for index, (name, w, h, rgba) in enumerate(decoded):
        col = index // 2
        row = index % 2
        x = 2 + col * (col_width + 2)
        y = 2 + row * (row_height + 2)
        positions.append((name, x, y, w, h, rgba))
    aw = max(x + w for _, x, _, w, _, _ in positions) + 2
    ah = max(y + h for _, _, y, _, h, _ in positions) + 2
    canvas = bytearray(aw * ah * 4)
    for _, px, py, w, h, rgba in positions:
        for row in range(h):
            canvas[((py + row) * aw + px) * 4:((py + row) * aw + px + w) * 4] = rgba[row * w * 4:(row + 1) * w * 4]
    page_name = f"ZZZZPackedAsset-{scale}.1.0-gamut0"
    page_png = _png_rgba(aw, ah, bytes(canvas))
    page_csi = bytearray(_csi_png_deepmap(page_png, page_name, scale=scale))
    struct.pack_into("<H", page_csi, 36, 1004)
    struct.pack_into("<I", page_csi, 8, 0)
    records = [AssetRendition(page_name, bytes(page_csi), 181, scale=scale, idiom=5, element=9, identifier_override=0)]
    for name, px, py, w, h, _ in positions:
        tokens = (AtlasKeyToken(1, 9), AtlasKeyToken(2, 181), AtlasKeyToken(12, scale), AtlasKeyToken(15, 5))
        link = AtlasLink(px, py, w, h, tokens, variant="explicit", header_u16=12, header_u32=20)
        records.append(AssetRendition(name, _linked_csi("image.png", link, scale, source_size=(w, h)), 181, scale=scale, idiom=5))
    return records


def build_packed_atlas_car(
    images: dict[str, bytes],
    *,
    scale: int = 1,
    max_width: int = 1024,
    max_height: int = 1024,
    sort_by: str = "name",
    platform: str = "macosx",
    target: str = "13.0",
    deployment_token: int = 5,
    style: str = "generic",
    atlas_name: str = "Atlas",
) -> bytes:
    """Shelf-pack PNGs into bounded pages using configurable heuristics."""
    return build_assets_car(
        packed_atlas_renditions(
            images,
            scale=scale,
            max_width=max_width,
            max_height=max_height,
            sort_by=sort_by,
            deployment_token=deployment_token,
            style=style,
            atlas_name=atlas_name,
        ),
        platform=platform,
        target=target,
    )
