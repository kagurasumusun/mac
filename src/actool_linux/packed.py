"""CoreUI packed-asset (ZZZZPackedAsset / LINK) writer.

Observed Apple behavior (Xcode 26.x oracles; derived only from observable
outputs on independently created input catalogs):

Apple replaces the pixel data of every scale-1, non-localized, universal-
idiom image rendition that shares a *packing class* with at least one other
such rendition (probe3/probe5 oracles):

- The rendition becomes layout 1003 with TLVs [1001, 1003, 1010, 1004, 1006]
  and an empty payload. TLV 1010 ("LINK") carries the (x, y, w, h) rectangle
  inside the atlas plus the key of the atlas rendition.
- Packing classes are ``(appearance, alpha-class, color-class)`` where
  alpha-class is "any pixel not fully opaque" and color-class is "every
  pixel has r == g == b" (grayscale or grayscale-representable RGB(A)).
  Atlases are named ``ZZZZPackedAsset-1.{opaque?1:0}.{gray?1:0}-gamut0`` and
  there is one atlas rendition per class. Sources are only packed when their
  class registers >= 2 candidates (verified threshold: 2 packs, 1 does not;
  no appearance/localization registry is required). Whether Apple also
  tests the bit-depth / premultiplied-input color space before classifying
  is unobserved.
- Atlas keys carry identifier=0, element=9, part=181, scale=1, appearance=A.
  When an appearance owns more than one atlas page the whole catalog's
  KEYFORMAT gains attribute 8 (dimension1) — (7,13,12,15,16,8,17,1,2) for
  iOS-family platforms, (7,13,1,2,3,17,8,11,12) for macosx — and the atlas
  page serial lives in dimension1, pages numbered in class-name order.
  LINK tails then reference the page with an (8, page) attribute pair
  (omitted for page 0). Multiple pages per class (Apple's bigint pagination
  heuristic) are not yet replicated: this writer emits one page per class,
  which matches every single-page oracle (documented cosmetic difference).
- Atlas payload: MLEC (mode 2 for opaque classes, 0 for alpha classes)
  codec 11 wrapping dmp2: palette grammar v4 for color atlases (<=255
  distinct colors + transparent padding swatch 0), raw LZFSE grammar v2
  for grayscale atlases or >255 colors. Pixels are premultiplied BGRA
  (v,a for grayscale); atlas padding is transparent.
- Non-1x scales, localized renditions, non-universal idioms and vector
  fallbacks are never packed.

The exact Apple bin-packing heuristic is private; this module uses a
deterministic shelf packer. Offsets written into LINK renditions always
match our own atlas, so consumer resolution is unaffected (documented
cosmetic difference).
"""
from __future__ import annotations

import struct
from dataclasses import replace

from .carwriter import AssetRendition, _fixed, lzfse_compat, _dmp2_lzfse_stream
from . import dmp2mini

ATLAS_PADDING = 2
_LINK_MAGIC = bytes.fromhex("4b4c4e49")
_MAX_V4_COLORS = 255  # swatch 0 reserved for transparent padding


def atlas_name(opaque: bool, gray: bool) -> str:
    """Atlas rendition naming scheme observed in Xcode 26.5 oracles (may
    change with CoreUI versions; keep in sync with probe oracles)."""
    return f"ZZZZPackedAsset-1.{1 if opaque else 0}.{1 if gray else 0}-gamut0"


def _decode_deepmap_pixels(csi: bytes) -> tuple[int, int, bytes, bytes] | None:
    """Recover ``(width, height, premultiplied BGRA, premultiplied GA)`` view.

    Returns None for anything not understood. Understands the grammars this
    package emits: color v1/v2/v4 (bpp 4), grayscale v1 (bpp 2, legacy test
    fixtures), and the shared v2/v3 LZFSE frame (both bpp values; GA v3 is
    what our writer emits for constant-straight-gray sources). The GA view is
    only set for grayscale sources.
    """
    if len(csi) < 184 or csi[:4] != b"ISTC":
        return None
    layout = struct.unpack_from("<H", csi, 36)[0]
    if layout != 12:
        return None
    width, height = struct.unpack_from("<2I", csi, 12)
    pixel_format = csi[24:28]
    if pixel_format == b" 8AG":       # grayscale+alpha, 2 bytes/px
        bpp = 2
    elif pixel_format == b"BGRA":
        bpp = 4
    else:
        return None
    tlv_length, one, zero, payload_length = struct.unpack_from("<4I", csi, 168)
    payload = csi[184 + tlv_length: 184 + tlv_length + payload_length]
    if len(payload) != payload_length or len(payload) < 32 or payload[:4] != b"MLEC":
        return None
    mode, codec, flen, f1, pbpp, dlen, zero2 = struct.unpack_from("<7I", payload, 4)
    if pbpp != bpp or codec != 11:
        return None
    dmp2 = payload[32:32 + dlen]
    if len(dmp2) != dlen or dmp2[:4] != b"dmp2":
        return None
    version = dmp2[4]
    w2, h2 = struct.unpack_from("<HH", dmp2, 8)
    if (w2, h2) != (width, height):
        return None
    npix = width * height
    raw: bytes | None = None
    if version == 1:
        body = dmp2[12:]
        raw = bytes(body) if len(body) == npix * bpp else None
    elif version == 3:
        # Either Apple's v3-mini opcode form or an LZFSE stream frame.
        raw = dmp2mini.decode_mini(dmp2, width, height, bpp)
        if raw is None:
            (stream_length,) = struct.unpack_from("<I", dmp2, 12)
            stream = dmp2[16:16 + stream_length]
            try:
                body = lzfse_compat.decompress(stream)
            except ValueError:
                return None
            raw = body if len(body) == npix * bpp else None
    elif version == 2:
        (stream_length,) = struct.unpack_from("<I", dmp2, 12)
        stream = dmp2[16:16 + stream_length]
        try:
            body = lzfse_compat.decompress(stream)
        except ValueError:
            return None
        raw = body if len(body) == npix * bpp else None
    elif version == 4 and bpp == 4:
        count, bppv = struct.unpack_from("<HH", dmp2, 12)
        if bppv != 4 or not 1 <= count <= 256:
            return None
        mini = None
        if count == 1:
            mini = dmp2mini.decode_mini(dmp2, width, height, bpp)
        if mini is not None:
            raw = mini
        else:
            palette = dmp2[16:16 + 4 * count]
            stream_length = struct.unpack_from("<I", dmp2, 16 + 4 * count)[0]
            stream = dmp2[20 + 4 * count: 20 + 4 * count + stream_length]
            try:
                indices = lzfse_compat.decompress(stream)
            except ValueError:
                return None
            if len(indices) != npix:
                return None
            out = bytearray(npix * 4)
            for i, idx in enumerate(indices):
                if idx >= count:
                    return None
                out[4 * i:4 * i + 4] = palette[4 * idx:4 * idx + 4]
            raw = bytes(out)
    if raw is None:
        return None
    if bpp == 2:
        # grayscale sources also report a BGRA rendering for RGB blending
        bgra = bytearray(npix * 4)
        for i in range(npix):
            v, a = raw[2 * i], raw[2 * i + 1]
            bgra[4 * i:4 * i + 4] = bytes((v, v, v, a))
        return width, height, bytes(bgra), raw
    return width, height, raw, raw


def _classify(asset: AssetRendition, decoded: tuple[int, int, bytes, bytes]) -> tuple[bool, bool]:
    """(gray, alpha) packing class from *source* pixel data."""
    _w, _h, bgra, ga = decoded
    if asset.csi[24:28] == b" 8AG":
        return True, any(ga[2 * i + 1] != 255 for i in range(len(ga) // 2))
    gray = True
    alpha = False
    for i in range(0, len(bgra), 4):
        if not (bgra[i] == bgra[i + 1] == bgra[i + 2]):
            gray = False
        if bgra[i + 3] != 255:
            alpha = True
        if not gray and alpha:
            break
    return gray, alpha


def is_pack_candidate(asset: AssetRendition) -> bool:
    # Renditions with an identifier override (image-stack children/aggregates,
    # texture references, brandassets marketing reuse) belong to aggregate
    # structures and are never packed (imagestack oracles: children stay
    # layout 12 even when two same-class candidates exist). Ordinary image
    # renditions have identifier_override=None; the atlases we emit use
    # override 0 and are excluded too.
    if asset.skip_facet or asset.identifier_override is not None:
        return False
    if asset.part != 181 or asset.effective_facet_part != 181 or asset.element != 85:
        return False
    if asset.scale != 1 or asset.idiom != 0 or asset.subtype:
        return False
    if asset.localization is not None or asset.layer:
        return False
    if asset.dimension1 or asset.dimension2 or asset.glyph_weight or asset.glyph_size:
        return False
    if asset.state or asset.direction or asset.atlas_linked:
        return False
    return _decode_deepmap_pixels(asset.csi) is not None


def _shelf_pack(rects: list[tuple[int, int]]) -> tuple[list[tuple[int, int]], int, int]:
    """Apple-compatible atlas packer (probed 16/16 on Xcode 26.5 oracles).

    Probed rules (m1..m8 / n1..n8 geometry corpus + probe5 c05, 2026-07):

    * insertion order: area DESC, then width DESC, height DESC, then
      reverse RENDITIONS tree order (later tree members insert first);
    * positions are absolute pixels including the 2px top/left margin, with
      a 2px gutter between rects;
    * free space is tracked as guillotine-split rectangles (right split and
      below split per placement); each rect takes the topmost, then
      leftmost, free rectangle that fits — reproducing Apple's hole filling
      seen in probe5 c05 (an 8x8 image nests at (36,20) below the 16x16
      sibling instead of opening a new band);
    * candidate widths are the prefix sums ``2 + sum(w + 2)`` over the
      first k inserted rects; the chosen width minimises, lexicographically,
      ``(max(W, H), H, W)`` on the even-floored canvas;
    * nominal canvas dimensions are truncated to even (observed as right or
      bottom margins of 1px for odd totals, e.g. n2/n7 right margin 1).

    Returns (positions aligned with ``rects`` order, width, height).
    """
    n = len(rects)
    if not rects:
        return [], 0, 0
    order = sorted(
        range(n),
        key=lambda i: (-(rects[i][0] * rects[i][1]), -rects[i][0], -rects[i][1], -i),
    )
    pad = ATLAS_PADDING

    def pack_at(w_nom: int) -> tuple[list[tuple[int, int]], int]:
        # Guillotine-split free regions, topmost (then leftmost) first-fit.
        # Matches Apple hole-filling, e.g. probe5 c05: an 8x8 image nests at
        # (36,20) below the 16x16 rect instead of opening a new band.
        free: list[list[int]] = [[pad, pad, w_nom - 2 * pad, 1 << 60]]  # (x, y, w, h)
        pos = [(0, 0)] * n
        bottom = 0
        for i in order:
            w, h = rects[i]
            pick = None
            for fi, (fx, fy, fw, fh) in enumerate(free):
                if w <= fw and h <= fh:
                    if pick is None or (fy, fx) < (free[pick][1], free[pick][0]):
                        pick = fi
            if pick is None:  # never happens: the initial band is unbounded
                raise AssertionError("atlas free-region exhaustion")
            fx, fy, fw, fh = free.pop(pick)
            pos[i] = (fx, fy)
            bottom = max(bottom, fy + h)
            if fw - w - pad > 0:
                free.append([fx + w + pad, fy, fw - w - pad, h])
            if fh - h - pad > 0:
                free.append([fx, fy + h + pad, fw, fh - h - pad])
        return pos, bottom + pad

    best: tuple[tuple[int, int, int], int, int, list[tuple[int, int]]] | None = None
    acc = pad
    for k, i in enumerate(order):
        acc += rects[i][0] + pad
        pos, h_nom = pack_at(acc)
        width = acc - (acc & 1)
        height = h_nom - (h_nom & 1)
        key = (max(width, height), height, width)
        if best is None or key < best[0]:
            best = (key, width, height, pos)
    assert best is not None
    _, width, height, positions = best
    return positions, width, height


def _atlas_palette(width: int, height: int, bgra: bytes) -> tuple[list[bytes], bytes] | None:
    """Swatch table + 8-bit index plane, or None when >255 colors.

    Swatch 0 is always the transparent padding color; other colors follow in
    first-occurrence (row-major) order.
    """
    index_of: dict[bytes, int] = {}
    plane = bytearray(width * height)
    for i in range(width * height):
        px = bytes(bgra[4 * i:4 * i + 4])
        if px == bytes(4):
            plane[i] = 0
            continue
        idx = index_of.get(px)
        if idx is None:
            if len(index_of) >= _MAX_V4_COLORS:
                return None
            idx = len(index_of) + 1
            index_of[px] = idx
        plane[i] = idx
    swatches = [bytes(4)] + [c for c, _ in sorted(index_of.items(), key=lambda kv: kv[1])]
    return swatches, bytes(plane)


def _atlas_dmp2(width: int, height: int, bgra: bytes, gray: bool) -> bytes:
    """Atlas payload grammar by class (observed in oracles).

    - grayscale atlases: v2 raw LZFSE over premultiplied (v, a) bytes
      (multi-value classes; single-value gray classes use Apple's v3 "mini"
      codec, which is still being decoded — v2 remains a valid readable
      stream; documented cosmetic difference).
    - color atlases: v4 palette when <=255 colors else v2 raw BGRA LZFSE.
    """
    if gray:
        pixels = bytearray(width * height * 2)
        for i in range(width * height):
            pixels[2 * i] = bgra[4 * i]
            pixels[2 * i + 1] = bgra[4 * i + 3]
        return _dmp2_lzfse_stream(width, height, bytes(pixels), 2, 2)
    paletted = _atlas_palette(width, height, bgra)
    if paletted is not None:
        swatches, plane = paletted
        stream = lzfse_compat.compress(plane)
        return (b"dmp2" + bytes((4, 1, 10, 4)) + struct.pack("<HHHH", width, height, len(swatches), 4)
                + b"".join(swatches) + struct.pack("<I", len(stream)) + stream)
    return _dmp2_lzfse_stream(width, height, bgra, 4, 2)


def _csi_atlas(name: str, width: int, height: int, bgra: bytes, *, gray: bool, opaque: bool) -> bytes:
    bpp = 2 if gray else 4
    dmp2 = _atlas_dmp2(width, height, bgra, gray)
    mode = 2 if opaque else 0
    payload = b"MLEC" + struct.pack("<7I", mode, 11, 16 + len(dmp2), 1, bpp, len(dmp2), 0) + dmp2
    stride = (width * bpp + 15) // 16 * 16
    tlvs = b"".join((
        struct.pack("<2I5I", 1001, 20, 1, 0, 0, 0, 0),
        struct.pack("<2I8s", 1004, 8, b"\0\0\0\0\0\0\x80?"),
        struct.pack("<2II", 1006, 4, 1),
        struct.pack("<2II", 1007, 4, stride),
    ))
    header = bytearray(184)
    header[:4] = b"ISTC"
    struct.pack_into("<5I", header, 4, 1, 0, width, height, 100)
    header[24:28] = b" 8AG" if gray else b"BGRA"
    struct.pack_into("<I", header, 28, 2 if gray else 1)
    struct.pack_into("<I2H", header, 32, 0, 1004, 0)
    header[40:168] = _fixed(name, 128)
    struct.pack_into("<4I", header, 168, len(tlvs), 1, 0, len(payload))
    return bytes(header) + tlvs + payload


def _link_tail(appearance: int, page: int) -> bytes:
    """TLV-1010 key stream: (1,9)(2,181)[(8,page)](12,1)[(7,appearance)](0,0)."""
    pairs = [(1, 9), (2, 181)]
    if page:
        pairs.append((8, page))
    pairs.append((12, 1))
    if appearance:
        pairs.append((7, appearance))
    pairs.append((0, 0))
    body = b"".join(struct.pack("<2H", a, v) for a, v in pairs)
    return struct.pack("<3H", 12, 4 * len(pairs), 0) + body


def _csi_link(source_csi: bytes, x: int, y: int, width: int, height: int, appearance: int, page: int) -> bytes:
    tlv_length, one, zero, payload_length = struct.unpack_from("<4I", source_csi, 168)
    out = bytearray(source_csi[:184])
    struct.pack_into("<H", out, 36, 1003)
    link = (_LINK_MAGIC + struct.pack("<5I", 0, x, y, width, height) + _link_tail(appearance, page))
    # Rebuild the TLV section in the observed order: keep 1001 and 1003,
    # insert 1010 right after 1003, then 1004/1006; drop 1007 (row bytes).
    head_tlvs = source_csi[184:184 + tlv_length]
    rebuilt = bytearray()
    cursor = 0
    while cursor + 8 <= len(head_tlvs):
        tag, length = struct.unpack_from("<2I", head_tlvs, cursor)
        if tag == 1007:
            cursor += 8 + length
            continue
        rebuilt += head_tlvs[cursor:cursor + 8 + length]
        cursor += 8 + length
        if tag == 1003:
            rebuilt += struct.pack("<2I", 1010, len(link)) + link
    struct.pack_into("<4I", out, 168, len(rebuilt), 1, 0, 0)
    return bytes(out) + bytes(rebuilt)


def composite_atlas(decoded: list[tuple[int, int, bytes, bytes]],
                    positions: list[tuple[int, int]], atlas_w: int, atlas_h: int) -> bytes:
    canvas = bytearray(atlas_w * atlas_h * 4)
    for (x, y), (w, h, pixels, _ga) in zip(positions, decoded):
        for row in range(h):
            src = row * w * 4
            dst = ((y + row) * atlas_w + x) * 4
            canvas[dst:dst + w * 4] = pixels[src:src + w * 4]
    return bytes(canvas)


def pack_renditions(assets: list[AssetRendition]) -> list[AssetRendition]:
    """Replace packable rendition pixels with LINK references + atlases.

    Observed rule: candidates are scale-1, universal, non-localized image
    renditions; a class ``(appearance, alpha-class, color-class)`` packs when
    it has >= 2 candidates. No appearance/localization registry is required.
    """
    candidates = [a for a in assets if is_pack_candidate(a)]
    if len(candidates) < 2:
        return list(assets)

    decoded_cache: dict[int, tuple[int, int, bytes, bytes]] = {}
    groups: dict[tuple[int, str], list[AssetRendition]] = {}
    class_of: dict[str, tuple[bool, bool]] = {}
    for asset in candidates:
        decoded = _decode_deepmap_pixels(asset.csi)
        assert decoded is not None  # guaranteed by is_pack_candidate
        decoded_cache[id(asset)] = decoded
        gray, alpha = _classify(asset, decoded)
        class_name = atlas_name(opaque=not alpha, gray=gray)
        class_of[class_name] = (gray, not alpha)
        groups.setdefault((asset.appearance, class_name), []).append(asset)

    packable = {key: group for key, group in groups.items() if len(group) >= 2}
    if not packable:
        return list(assets)

    result = list(assets)
    index_of = {id(a): i for i, a in enumerate(result)}
    atlases: list[AssetRendition] = []
    # Per appearance, pages are numbered in class-name order. This writer
    # emits exactly one page per class (Apple's multi-page pagination
    # heuristic is a documented cosmetic divergence).
    pages_by_appearance: dict[int, list[str]] = {}
    for appearance, class_name in sorted(packable, key=lambda k: (k[0], k[1])):
        group = packable[(appearance, class_name)]
        gray, opaque = class_of[class_name]
        decoded = [decoded_cache[id(a)] for a in group]
        rects = [(d[0], d[1]) for d in decoded]
        positions, atlas_w, atlas_h = _shelf_pack(rects)
        canvas = composite_atlas(decoded, positions, atlas_w, atlas_h)
        atlas_csi = _csi_atlas(class_name, atlas_w, atlas_h, canvas, gray=gray, opaque=opaque)
        page = len(pages_by_appearance.setdefault(appearance, []))
        pages_by_appearance[appearance].append(class_name)
        atlases.append(AssetRendition(
            class_name, atlas_csi, 181, 181, scale=1, idiom=0,
            appearance=appearance, element=9, identifier_override=0,
            dimension1=page, skip_facet=True,
        ))
        for asset, (x, y), (w, h, _px, _ga) in zip(group, positions, decoded):
            link_csi = _csi_link(asset.csi, x, y, w, h, appearance, page)
            result[index_of[id(asset)]] = replace(asset, csi=link_csi)
    return result + atlases
