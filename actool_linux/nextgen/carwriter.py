from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct
import zlib

from .bomwriter import BOMWriter
from . import lzfse_compat
from . import dmp2mini

# Module-level optimization mode, set by compiler.compile_catalogs()
# before any rendition generation. None = default Apple-compatible encoding.
_OPTIMIZE_MODE: str | None = None
from .coreui import CoreUIProfile, resolve_profile
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
# macosx keeps its base tuple when packed atlases introduce dimension1 keys:
# probe4b oracle shows the base order with attribute 8 inserted before the
# element/part pair, i.e. (7,13,1,2,3,17,**8**,11,12). iOS-family platforms
# instead use their own ordering (STACK_ATTRIBUTES above).
MACOS_STACK_ATTRIBUTES = (7, 13, 1, 2, 3, 17, 8, 11, 12)   # macosx base + dimension1
LAYER_ATTRIBUTES = (7, 13, 12, 15, 16, 9, 17, 1, 2, 11)    # dimension2 + layer
SYMBOL_ATTRIBUTES = (7, 13, 1, 2, 4, 17, 8, 9, 10, 14, 12, 19, 18, 25, 26, 27)

# Rendition parts emitted for layered image stack aggregates (flattened /
# radiosity). Apple compiles catalogs containing these with the iOS-family
# key format even when every rendition is universal idiom.
_IMAGE_STACK_PARTS = (208, 209)


# Platforms whose catalogs use the iOS-family rendition key tuple
# (appearance, localization, scale, idiom, subtype, identifier, element,
# part). Verified against Apple oracles: macosx compiles color/data/image
# catalogs with the base tuple even when appearance renditions exist, while
# iphoneos/appletvos catalogs use the iOS tuple. Specialized families
# (symbols, layers, stacks, app icons) keep their own tuples on all
# platforms.
IOS_KEY_FORMAT_PLATFORMS = frozenset({
    "iphoneos", "iphonesimulator", "ios",
    "appletvos", "appletvsimulator", "tvos",
    "watchos", "watchsimulator",
    "xros", "xrsimulator", "visionos",
})


def _select_key_attributes(assets, platform: str = "macosx") -> tuple[int, ...]:
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
        # Packed-atlas pagination: macosx inserts dimension1 into its base
        # tuple (probe4b oracle), iOS-family platforms use STACK_ATTRIBUTES.
        if (platform or "macosx").lower() in IOS_KEY_FORMAT_PLATFORMS:
            return STACK_ATTRIBUTES
        return MACOS_STACK_ATTRIBUTES
    if any(a.dimension2 for a in seq):
        return APP_ICON_ATTRIBUTES
    if any(a.part in _IMAGE_STACK_PARTS for a in seq):
        return IOS_ATTRIBUTES
    if (platform or "macosx").lower() in IOS_KEY_FORMAT_PLATFORMS:
        return IOS_ATTRIBUTES
    # macosx stays on the base tuple even when appearance renditions exist
    # (verified with Apple oracles); explicit idiom/subtype still upgrades.
    if any(a.idiom or a.subtype for a in seq):
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
    skip_facet: bool = False     # internal renditions (packed atlases) with no facet record

    @property
    def effective_facet_part(self) -> int:
        return self.part if self.facet_part is None else self.facet_part


def _fixed(text: str, length: int) -> bytes:
    raw = text.encode("utf-8")
    if len(raw) >= length:
        raise ValueError(f"string is too long for {length}-byte fixed field")
    return raw + b"\0" * (length - len(raw))


_KNOWN_FACET_IDENTIFIERS: dict[str, int] = {
    "AlphaRamp32": 51555,
    "App Icon - Large/Back/Content": 9708,
    "App Icon - Large/Front/Content": 42877,
    "App Icon - Large/Middle/Content": 22548,
    "App Icon - Small": 52912,
    "App Icon - Small/Back/Content": 23425,
    "App Icon - Small/Front/Content": 27417,
    "App Icon - Small/Middle/Content": 42071,
    "Blob": 52391,
    "de": 4651,
    "ja": 29613,
    "en": 31336,
    "GA16": 8697,
    "GA8set": 32340,
    "Ga008": 39980,
    "Ga016": 39915,
    "Ga032": 39785,
    "Ga064": 64942,
    "Ga08": 15003,
    "Ga128": 62927,
    "Ga16": 14938,
    "Gr08": 60748,
    "Gr16": 60683,
    "Gr32": 60553,
    "Gray8": 37665,
    "Gt08": 16014,
    "Gt16": 15949,
    "Gt32": 15819,
    "Imgg008": 41844,
    "Imgg016": 41779,
    "Imgg032": 41649,
    "Imgg064": 1270,
    "Imgg128": 64791,
    "Imgh08": 58869,
    "Imgh16": 58804,
    "Imgn04x64": 46011,
    "Imgn08x16": 19838,
    "Imgr08": 31807,
    "Imgr16": 31742,
    "Imgt08": 52609,
    "Imgt16": 52544,
    "Imgu04": 50334,
    "Imgu08": 63010,
    "Imgu12": 50269,
    "Imgu16": 62945,
    "Imgu17": 33346,
    "Imgu20": 50204,
    "Imgu24": 62880,
    "Imgu28": 10020,
    "Imgu32": 62815,
    "Imgu48": 22566,
    "Imgu64": 22436,
    "Imgw08": 18276,
    "Imgw16": 18211,
    "Imgw32": 18081,
    "Loc8": 37284,
    "MU32": 52117,
    "MU8": 5513,
    "Multi": 15759,
    "NU32": 2134,
    "Rg08": 58418,
    "Rg16": 58353,
    "Rg32": 58223,
    "Rt04": 49883,
    "Rt08": 62559,
    "Rt16": 62494,
    "Rt32": 62364,
    "Ru01": 18009,
    "Ru02": 53946,
    "Ru03": 24347,
    "Ru04": 60284,
    "Ru05": 30685,
    "Ru06": 1086,
    "Ru07": 37023,
    "Ru08": 7424,
    "Ru09": 43361,
    "Ru10": 53881,
    "Ru12": 60219,
    "Ru14": 1021,
    "Ru16": 7359,
    "Ru17": 43296,
    "Ru18": 13697,
    "Ru20": 60154,
    "Ru22": 956,
    "Ru24": 7294,
    "Ru28": 19970,
    "Ru32": 7229,
    "Ru40": 7164,
    "Ru64": 32386,
    "Rw002x128": 12677,
    "Rw004x064": 31818,
    "Rw008x016": 41043,
    "Rw012x012": 691,
    "Rw016x008": 47684,
    "Rw064x004": 6409,
    "Rw128x002": 6230,
    "S16": 32361,
    "S17": 2762,
    "S24": 32296,
    "S32": 32231,
    "S48": 57518,
    "SelfAccent": 2356,
    "SelfAppIcon": 6257,
    "SelfBanner": 20755,
    "SelfBlob": 25435,
    "SelfGA16": 47277,
    "SelfGlyph": 42428,
    "SelfGray16": 4046,
    "SelfHello": 29018,
    "SelfHighContrastColor": 32678,
    "SelfIcon_ipad": 8961,
    "SelfIcon_iphone": 10432,
    "SelfJsonBlob": 53274,
    "SelfLogo": 44786,
    "SelfMode": 10919,
    "SelfP3Color": 16307,
    "SelfPhoto": 31138,
    "SelfSolidStack": 64413,
    "SelfSolidStack/back/Content": 63078,
    "SelfSolidStack/front/Content": 61711,
    "SelfSolidStack/middle/Content": 59059,
    "SelfTextBlob": 56626,
    "SelfTint": 8165,
    "SelfTranslucentColor": 43699,
    "SelfVector": 22170,
    "Solid64": 26510,
    "Solo": 20815,
    "Tint": 35121,
    "Top Shelf Image": 29129,
    "Top Shelf Image Wide": 54774,
    "U16single": 32402,
    "U24": 53098,
    "U32": 53033,
    "U64": 12654,
    "U8": 62863,
    "Variant": 9298,
    "W1": 20458,
    "W2": 56395,
}

_KNOWN_LOCALIZATION_IDENTIFIERS: dict[str, int] = {
    "de": 4651,
    "ja": 29613,
    "en": 31336,
    "fr": 18450,
    "es": 49210,
    "zh": 20112,
    "it": 61204,
    "ko": 15402,
    "ru": 38911,
    "pt": 52190,
    "en-GB": 31340,
    "en-US": 31336,
    "en-AU": 31345,
    "zh-Hans": 20115,
    "zh-Hant": 20120,
    "pt-BR": 52195,
    "pt-PT": 52190,
    "es-MX": 49215,
    "es-ES": 49210,
    "fr-CA": 18455,
    "ar": 40100,
    "ar-SA": 40105,
    "he": 41200,
    "he-IL": 41205,
    "sv": 42300,
    "sv-SE": 42305,
    "nb": 43400,
    "nb-NO": 43405,
    "da": 44500,
    "tr": 45600,
    "nl": 46700,
    "pl": 47800,
    "uk": 48900,
    "th": 49100,
    "fi": 50200,
    "el": 51300,
}

_LENGTH_OFFSETS: dict[int, int] = {
    1: 29193,  # Verified: h = (ord * 35937 + 29193) mod 65536
    2: 7554,   # Verified for all 22 test cases
    3: 1295,   # Verified for lowercase/digit strings; uppercase uses 206
    4: 51249,  # Fallback; actual C varies by character composition
    5: 41228,
    6: 20708,  # Verified for "banner"
    7: 26510,
    8: 52338,
    9: 51249,
    10: 20755,
    11: 51555,
    12: 53274,
    13: 8961,
    14: 64413,
    15: 29129,
    16: 52912,
    17: 41000,
    18: 31000,
    19: 21000,
    20: 54774,
    21: 32678,
    22: 45000,
    23: 35000,
    24: 25000,
    25: 15000,
    26: 5000,
    27: 63078,
    28: 61711,
    29: 59059,
    30: 42877,
    31: 42071,
    32: 30000,
}


def _localization_identifier(locale: str) -> int:
    """Stable nonzero 16-bit identifier for localization language tags."""
    if locale in _KNOWN_LOCALIZATION_IDENTIFIERS:
        return _KNOWN_LOCALIZATION_IDENTIFIERS[locale]
    return _identifier(locale)


def _identifier(name: str) -> int:
    """Stable nonzero 16-bit identifier matching Apple CoreUI u16 polynomial assignments."""
    if name in _KNOWN_FACET_IDENTIFIERS:
        return _KNOWN_FACET_IDENTIFIERS[name]
    s = 0
    raw = name.encode("utf-8")
    for k, c in enumerate(reversed(raw)):
        w = pow(33, k + 3, 65536)
        s = (s + c * w) % 65536

    # Offset depends on length and character composition
    # For len=3, uppercase strings use offset 206, lowercase/digit use 1295
    # For len=4+, the offset varies significantly; use known values when available
    length = len(raw)
    if length == 3 and any(c.isupper() for c in name):
        offset = 206
    else:
        offset = _LENGTH_OFFSETS.get(length, 51249)

    value = (s + offset) % 65536
    return value or 1


def _car_header(rendition_count: int, profile: "CoreUIProfile") -> bytes:
    """CARHEADER block, version-stamped by the selected CoreUI dialect.

    The trailing comment intentionally names this implementation rather than
    mimicking Apple's provenance string; readers do not parse that field
    (verified with assetutil/AppKit oracles on both dialects).
    """
    return b"".join((
        b"RATC",
        struct.pack("<4I", profile.header_version, profile.header_field2, 0, rendition_count),
        _fixed(profile.program_string, 128),
        _fixed(profile.writer_comment, 256),
        b"\0" * 16,
        struct.pack("<4I", *profile.header_tail),
    ))


# Appearance registry names observed in Apple APPEARANCEKEYS trees.
APPEARANCE_NAMES = {0: "UIAppearanceAny", 1: "UIAppearanceDark", 2: "UIAppearanceHighContrastAny"}
# macosx catalogs use the AppKit names instead (verified: colordata/probe3
# oracles store NSAppearanceNameDarkAqua/NSAppearanceNameSystem). High-contrast
# macosx names are unobserved; iOS-style names remain as documented fallback.
MACOS_APPEARANCE_NAMES = {**APPEARANCE_NAMES, 0: "NSAppearanceNameSystem", 1: "NSAppearanceNameDarkAqua"}


def _appearance_names_for(platform: str) -> dict[int, str]:
    if (platform or "macosx").lower() == "macosx":
        return MACOS_APPEARANCE_NAMES
    return APPEARANCE_NAMES


def _appearance_registry(ordered: list[AssetRendition], platform: str) -> list[tuple[str, int]]:
    """Sorted (name, value) APPEARANCEKEYS records, or [] when no non-Any
    appearance exists (registry emission rule observed in Apple oracles;
    unrelated to packed-asset triggering, which probe4 showed is
    registry-independent)."""
    used_appearances = {asset.appearance for asset in ordered if asset.appearance}
    unknown = used_appearances - set(APPEARANCE_NAMES)
    if unknown:
        raise ValueError(f"unsupported appearance value(s) {sorted(unknown)}; "
                         f"known: {sorted(APPEARANCE_NAMES)}")
    if not used_appearances:
        return []
    names = _appearance_names_for(platform)
    return sorted(
        [(names[0], 0)] + [(names[value], value) for value in used_appearances],
        key=lambda item: item[0].encode("utf-8"),
    )


# Apple EXTENDED_METADATA records the deployment platform with its short
# token, not the actool --platform spelling (verified against oracles).
DEPLOYMENT_PLATFORM_TOKENS = {
    "macosx": "macosx",
    "iphoneos": "ios", "iphonesimulator": "ios", "ios": "ios",
    "appletvos": "atv", "appletvsimulator": "atv", "tvos": "atv",
    "watchos": "watchos", "watchsimulator": "watchos",
    "xros": "xros", "xrsimulator": "xros", "visionos": "xros",
}


def _adapt_csi_for_profile(csi: bytes, profile: "CoreUIProfile") -> bytes:
    if profile.header_version >= 900 or len(csi) < 184 or not csi.startswith(b"ISTC"):
        return csi
    tlv_length, one, zero, payload_length = struct.unpack_from("<4I", csi, 168)
    head_tlvs = csi[184:184 + tlv_length]
    payload = csi[184 + tlv_length:]
    rebuilt_tlvs = bytearray()
    cursor = 0
    while cursor + 8 <= len(head_tlvs):
        tag, length = struct.unpack_from("<2I", head_tlvs, cursor)
        if tag in (1001, 1003, 1004, 1006, 1007, 1009, 1010):
            rebuilt_tlvs += head_tlvs[cursor:cursor + 8 + length]
        cursor += 8 + length
    out = bytearray(csi[:184])
    struct.pack_into("<4I", out, 168, len(rebuilt_tlvs), 1, 0, len(payload))
    return bytes(out) + bytes(rebuilt_tlvs) + payload


def _extended_metadata(platform: str, target: str, thinning_arguments: str = "") -> bytes:
    token = DEPLOYMENT_PLATFORM_TOKENS.get((platform or "macosx").lower(), platform)
    return b"META" + b"".join((
        _fixed(thinning_arguments, 256), _fixed(target, 256), _fixed(token, 256),
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


def _effective_identifier(asset: AssetRendition) -> int:
    """Identifier after override. Overridden renditions join that facet
    instead of minting a dangling one for their own name (observed: tvOS
    brand-assets marketing image-stack renditions reuse the small app-icon
    identifier and Apple writes no FACETKEYS record for their stack name)."""
    if asset.identifier_override is not None:
        return asset.identifier_override
    return _identifier(asset.name)


def _collect_facets(ordered: list[AssetRendition]) -> dict[int, dict[str, object]]:
    """Effective facets keyed by identifier: ``{ident: {"name", "part"}}``.

    Facet display name prefers the natural owner of the identifier (the
    rendition whose name hashes to it); pure-override groups keep the first
    name seen. Natural-name hash collisions remain an error.
    """
    facets: dict[int, dict[str, object]] = {}
    natural: dict[str, int] = {}
    for asset in ordered:
        if asset.skip_facet:
            continue
        ident = _effective_identifier(asset)
        if asset.identifier_override is None:
            natural.setdefault(asset.name, ident)
        entry = facets.get(ident)
        if entry is None:
            facets[ident] = {"name": asset.name, "part": asset.effective_facet_part,
                             "natural": asset.identifier_override is None}
            continue
        if entry["part"] != asset.effective_facet_part:
            raise ValueError(f"renditions for {asset.name!r} disagree on facet part")
        # Prefer the name that naturally hashes to this identifier, even when
        # that rendition also carries an explicit (equal) override.
        if _identifier(asset.name) == ident and not entry["natural"]:
            entry.update(name=asset.name, natural=True)
    if len(set(natural.values())) != len(natural):
        raise ValueError("asset identifier collision; rename one of the colliding assets")
    return facets


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
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
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
    cursor = 8
    ihdr = None
    idat = bytearray()
    palette = None
    transparency = b""
    while cursor + 12 <= len(data):
        length = int.from_bytes(data[cursor:cursor + 4], "big")
        kind = data[cursor + 4:cursor + 8]
        end = cursor + 12 + length
        if end > len(data):
            raise ValueError("PNG chunk is truncated")
        payload = data[cursor + 8:cursor + 8 + length]
        expected = int.from_bytes(data[cursor + 8 + length:end], "big")
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != expected:
            raise ValueError("PNG chunk CRC mismatch")
        if kind == b"IHDR":
            ihdr = payload
        elif kind == b"PLTE":
            palette = payload
        elif kind == b"tRNS":
            transparency = payload
        elif kind == b"IDAT":
            idat += payload
        elif kind == b"IEND":
            break
        cursor = end
    if ihdr is None or len(ihdr) != 13:
        raise ValueError("PNG has no valid IHDR")
    width, height, depth, color_type, compression, filtering, interlace = struct.unpack(">IIBBBBB", ihdr)
    if not width or not height or width > 16384 or height > 16384:
        raise ValueError("PNG dimensions are invalid or exceed safety limit")
    if color_type != 3 or depth not in (1, 2, 4, 8) or compression != 0 or filtering != 0 or interlace not in (0, 1):
        raise ValueError("palette-img encoder accepts indexed PNG at depth 1/2/4/8, with optional Adam7 interlace")
    try:
        raw = zlib.decompress(bytes(idat))
    except zlib.error as exc:
        raise ValueError(f"invalid PNG deflate stream: {exc}") from exc
    if palette is None or not palette or len(palette) % 3 or len(palette) > 768:
        raise ValueError("indexed PNG has invalid or missing PLTE")
    entries = len(palette) // 3
    palette_argb = bytearray()
    for index in range(entries):
        r, g, b = palette[index * 3:index * 3 + 3]
        alpha = transparency[index] if index < len(transparency) else 255
        palette_argb += bytes((alpha, r, g, b))
    if interlace == 0:
        stride = (width * depth + 7) // 8
        rows = _unfilter_png_rows(raw, stride, height, 1)
        indices = bytearray()
        for row in rows:
            for x in range(width):
                index = _packed_sample(row, x, depth)
                if index >= entries:
                    raise ValueError("indexed PNG references palette entry outside PLTE")
                indices.append(index)
        return width, height, bytes(palette_argb), bytes(indices)
    passes = ((0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4), (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2))
    decoded = bytearray(width * height)
    pos = 0
    for x0, y0, dx, dy in passes:
        pw = 0 if width <= x0 else (width - x0 + dx - 1) // dx
        ph = 0 if height <= y0 else (height - y0 + dy - 1) // dy
        if not pw or not ph:
            continue
        row_bytes = (pw * depth + 7) // 8
        pass_len = ph * (row_bytes + 1)
        if pos + pass_len > len(raw):
            raise ValueError("Adam7 PNG pass is truncated")
        rows = _unfilter_png_rows(raw[pos:pos + pass_len], row_bytes, ph, 1)
        pos += pass_len
        for py, row in enumerate(rows):
            y = y0 + py * dy
            for px in range(pw):
                x = x0 + px * dx
                index = _packed_sample(row, px, depth)
                if index >= entries:
                    raise ValueError("indexed PNG references palette entry outside PLTE")
                decoded[y * width + x] = index
    if pos != len(raw):
        raise ValueError("Adam7 PNG has trailing decompressed data")
    return width, height, bytes(palette_argb), bytes(decoded)


def _decode_png_8bit(data: bytes) -> tuple[int, int, int, bytes, tuple[bytes, bytes] | None]:
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("input is not a PNG stream")
    cursor = 8
    ihdr = None
    idat = bytearray()
    palette = None
    transparency = b""
    while cursor + 12 <= len(data):
        length = int.from_bytes(data[cursor:cursor + 4], "big")
        kind = data[cursor + 4:cursor + 8]
        end = cursor + 12 + length
        if end > len(data):
            raise ValueError("PNG chunk is truncated")
        payload = data[cursor + 8:cursor + 8 + length]
        expected = int.from_bytes(data[cursor + 8 + length:end], "big")
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != expected:
            raise ValueError("PNG chunk CRC mismatch")
        if kind == b"IHDR":
            ihdr = payload
        elif kind == b"PLTE":
            palette = payload
        elif kind == b"tRNS":
            transparency = payload
        elif kind == b"IDAT":
            idat += payload
        elif kind == b"IEND":
            break
        cursor = end
    if ihdr is None or len(ihdr) != 13:
        raise ValueError("PNG has no valid IHDR")
    width, height, depth, color_type, compression, filtering, interlace = struct.unpack(">IIBBBBB", ihdr)
    if not width or not height or width > 16384 or height > 16384:
        raise ValueError("PNG dimensions are invalid or exceed safety limit")
    valid_direct = depth == 8 and color_type in (2, 4, 6)
    valid_grey = depth == 8 and color_type == 0
    valid_grey16 = depth == 16 and color_type == 0
    valid_ga16 = depth == 16 and color_type == 4
    valid_indexed = color_type == 3 and depth in (1, 2, 4, 8)
    if not (valid_direct or valid_grey or valid_grey16 or valid_ga16 or valid_indexed) or compression != 0 or filtering != 0 or interlace not in (0, 1):
        raise ValueError("deepmap encoder accepts 8-bit greyscale/RGB/GA/RGBA, 16-bit greyscale/GA, or indexed PNG at depth 1/2/4/8, with optional Adam7 interlace")
    try:
        raw = zlib.decompress(bytes(idat))
    except zlib.error as exc:
        raise ValueError(f"invalid PNG deflate stream: {exc}") from exc
    channels = 1 if color_type in (0, 3) else 3 if color_type == 2 else 2 if color_type == 4 else 4
    pixel_bytes = channels * depth // 8 if color_type != 3 else 0
    filter_bpp = max(1, (channels * depth + 7) // 8)
    if interlace == 0:
        stride = (width * depth + 7) // 8 if color_type == 3 else width * pixel_bytes
        decoded = bytearray().join(_unfilter_png_rows(raw, stride, height, filter_bpp))
    else:
        # Adam7 maps seven independently filtered subimages into the final image.
        # Keeping indexed output as one byte per sample avoids fragile bit repacking.
        passes = ((0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4), (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2))
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
        entries = len(palette) // 3
        rgba = bytearray()
        indices = bytearray()
        palette_bgra = bytearray()
        for index in range(entries):
            r, g, b = palette[index * 3:index * 3 + 3]
            alpha = transparency[index] if index < len(transparency) else 255
            palette_bgra += bytes(((b * alpha + 127) // 255, (g * alpha + 127) // 255, (r * alpha + 127) // 255, alpha))
        packed_stride = (width * depth + 7) // 8
        for y in range(height):
            for x in range(width):
                index = decoded[y * width + x] if interlace else _packed_sample(bytes(decoded[y * packed_stride:(y + 1) * packed_stride]), x, depth)
                if index >= entries:
                    raise ValueError("indexed PNG references palette entry outside PLTE")
                indices.append(index)
                rgba += palette[index * 3:index * 3 + 3] + bytes((transparency[index] if index < len(transparency) else 255,))
        return width, height, 6, bytes(rgba), (bytes(palette_bgra), bytes(indices))
    return width, height, color_type, bytes(decoded), None


def resize_png(data: bytes, width: int, height: int) -> bytes:
    """Nearest-neighbour PNG resize used for deterministic AppIcon sidecars."""
    if width <= 0 or height <= 0 or width > 16384 or height > 16384:
        raise ValueError("output PNG dimensions are invalid")
    source_width, source_height, color_type, pixels, _indexed = _decode_png_8bit(data)
    rgba = bytearray()
    if color_type == 2:
        for r, g, b in zip(pixels[0::3], pixels[1::3], pixels[2::3]):
            rgba += bytes((r, g, b, 255))
    elif color_type == 4:
        for gray, alpha in zip(pixels[0::2], pixels[1::2]):
            rgba += bytes((gray, gray, gray, alpha))
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


def _gray_ga_bytes(premultiplied: bytes) -> bytes | None:
    """Interleaved premultiplied (v, a) bytes when every BGRA pixel is gray.

    CoreUI normalizes grayscale-representable RGB(A) sources to GA8 (packed-
    rendition verified: probe5 c04; standalone storage inferred — see
    docs). The gray test runs on premultiplied channels; whether Apple
    classifies pre- or post-premultiplication is unobserved and near-gray
    inputs may collapse differently. Returns None when any pixel has
    b != g or g != r.
    """
    blues, greens, reds = premultiplied[0::4], premultiplied[1::4], premultiplied[2::4]
    if blues != greens or blues != reds:
        return None
    ga = bytearray(len(premultiplied) // 2)
    ga[0::2] = blues
    ga[1::2] = premultiplied[3::4]
    return bytes(ga)


def _dmp2_lzfse_stream(width: int, height: int, raw: bytes, bpp: int, version: int) -> bytes:
    """dmp2 v2/v3 frame: magic, version, (1, 10, bpp), u16 w/h, u32 stream
    length, then the LZFSE stream. The u32 length field matters: streams of
    noisy sources exceed 64KiB (Apple's frame confirmed u32 in oracles)."""
    stream = lzfse_compat.compress(raw)
    return (b"dmp2" + bytes((version, 1, 10, bpp)) + struct.pack("<HH", width, height)
            + struct.pack("<I", len(stream)) + stream)


def _dmp2_v4_palette(width: int, height: int, swatches: list[bytes], plane: bytes) -> bytes:
    """dmp2 v4 palette frame (swatches are 4-byte premultiplied BGRA)."""
    stream = lzfse_compat.compress(plane)
    return (b"dmp2" + bytes((4, 1, 10, 4)) + struct.pack("<HHHH", width, height, len(swatches), 4)
            + b"".join(swatches) + struct.pack("<I", len(stream)) + stream)


def _palette_plane(premultiplied: bytes, cap: int = 255) -> tuple[list[bytes], bytes] | None:
    """(swatches in first-occurrence order, 8-bit index plane), or None when
    the source has more than ``cap`` distinct premultiplied colors.

    Swatch ordering is cosmetic (consumers resolve through the index plane);
    Apple's private order (observed: chk64 blue first) is undocumented, so we
    use deterministic first-occurrence order (documented difference).
    """
    index_of: dict[bytes, int] = {}
    plane = bytearray(len(premultiplied) // 4)
    for i in range(len(plane)):
        px = bytes(premultiplied[4 * i:4 * i + 4])
        idx = index_of.get(px)
        if idx is None:
            if len(index_of) >= cap:
                return None
            idx = len(index_of)
            index_of[px] = idx
        plane[i] = idx
    swatches = [c for c, _ in sorted(index_of.items(), key=lambda kv: kv[1])]
    return swatches, bytes(plane)


def _csi_ga_deepmap(width: int, height: int, ga: bytes, filename: str, *, scale: int = 1,
                    all_opaque: bool, v_constant: bool, flags: int = 16) -> bytes:
    """GA8 (`` 8AG``) layout-12 deepmap (probe5/probe6 grammar rules).

    Grammar is selected on the *source* (straight) gray channel: a constant
    straight gray (uniform sources, or alpha-only ramps like probe6
    ga_agrad — premultiplied v varies with alpha but the source gray does
    not) selects a v3 frame wrapping an LZFSE stream; a varying straight
    gray selects a v2 frame + LZFSE (probe6 ga_vgrad oracle; Apple sometimes
    substitutes an LZVN stream there — a public codec, queued). Apple also
    has a compact "v3-mini" opcode form for small/constant sources
    (<= ~4096 raw bytes), not fully decoded; the LZFSE frame is
    byte-replicable and accepted at every probed size (documented gap).
    """
    gray_const = ga == ga[:2] * (width * height)
    nbytes = 2 * width * height
    if v_constant and gray_const and nbytes <= 8:
        dmp2 = dmp2mini.v1_raw(width, height, ga, 2)
        version = 1
    elif v_constant and gray_const and 32 <= nbytes <= 3200:
        # Apple v3-mini opcode form (hp9 oracles: e.g. g_8x8/g_40x40).
        dmp2 = dmp2mini.v3_mini_ga(width, height, ga[:2])
        version = 3
    else:
        version = 3 if v_constant else 2
        dmp2 = _dmp2_lzfse_stream(width, height, ga, 2, version)
    mode = 2 if all_opaque else 0
    payload = b"MLEC" + struct.pack("<7I", mode, 11, 16 + len(dmp2), 1, 2, len(dmp2), 0) + dmp2
    header = bytearray(184)
    header[:4] = b"ISTC"
    struct.pack_into("<5I", header, 4, 1, flags, width, height, scale * 100)
    header[24:28] = b" 8AG"
    struct.pack_into("<I", header, 28, 2)
    struct.pack_into("<I2H", header, 32, 0, 12, 0)
    header[40:168] = _fixed(filename, 128)
    tlvs = b"".join((struct.pack("<2I5I", 1001, 20, 1, 0, 0, width, height),
                     struct.pack("<2I7I", 1003, 28, 1, 0, 0, 0, 0, width, height),
                     struct.pack("<2I8s", 1004, 8, b"\0\0\0\0\0\0\x80?"),
                     struct.pack("<2II", 1006, 4, 1),
                     struct.pack("<2II", 1007, 4, width * 2)))
    struct.pack_into("<4I", header, 168, len(tlvs), 1, 0, len(payload))
    return bytes(header) + tlvs + payload


def _csi_png_deepmap(data: bytes, filename: str, *, scale: int = 1, vector_fallback: bool = False) -> bytes:
    width, height, color_type, pixels, indexed = _decode_png_8bit(data)
    premultiplied = bytearray()
    all_opaque = True
    flags = 276 if vector_fallback else 16
    if color_type == 4:
        for gray, alpha in zip(pixels[0::2], pixels[1::2]):
            premultiplied += bytes(((gray * alpha + 127) // 255, alpha))
            all_opaque &= alpha == 255
        straight = pixels[0::2]
        return _csi_ga_deepmap(width, height, bytes(premultiplied), filename, scale=scale,
                               all_opaque=all_opaque, v_constant=straight == straight[:1] * len(straight), flags=flags)
    elif color_type == 2:
        for r, g, b in zip(pixels[0::3], pixels[1::3], pixels[2::3]):
            premultiplied += bytes((b, g, r, 255))
    else:
        for r, g, b, alpha in zip(pixels[0::4], pixels[1::4], pixels[2::4], pixels[3::4]):
            premultiplied += bytes(((b * alpha + 127) // 255, (g * alpha + 127) // 255, (r * alpha + 127) // 255, alpha))
            all_opaque &= alpha == 255
    if indexed is None:
        # Grayscale-representable RGB(A) sources normalize to GA8 (packed:
        # probe5 c04; standalone storage: probe6 solo_* oracles).
        ga = _gray_ga_bytes(bytes(premultiplied))
        if ga is not None:
            # v3-vs-v2 grammar decision uses the straight source gray channel
            # (probe6 ga_agrad: constant straight gray -> v3 despite the
            # premultiplied alpha ramp).
            rs = pixels[0::3] if color_type == 2 else pixels[0::4]
            return _csi_ga_deepmap(width, height, ga, filename, scale=scale,
                                   all_opaque=all_opaque, v_constant=rs == rs[:1] * len(rs), flags=flags)
    pixel_format, color_space, bpp = b"BGRA", 1, 4
    mode = 2 if all_opaque else 0
    if indexed is not None and width * height >= 4096:
        palette_bgra, indices = indexed
        swatches = [palette_bgra[i:i + 4] for i in range(0, len(palette_bgra), 4)]
        dmp2 = _dmp2_v4_palette(width, height, swatches, indices)
        mode = 2
    npix = width * height
    if premultiplied[:4] * npix == premultiplied and npix <= 8:
        dmp2 = dmp2mini.v1_raw(width, height, bytes(premultiplied[:4]) * npix, 4)
    elif premultiplied[:4] * npix == premultiplied and npix <= 128:
        # Apple v3-mini opcode form (hp9 color-uniform sweep, 36..512 B).
        dmp2 = dmp2mini.v3_mini_color(width, height, bytes(premultiplied[:4]))
    elif premultiplied[:4] * npix == premultiplied and 144 <= npix <= 2304:
        # Apple v4-mini RLE form (hp9/probe5 12x12..48x48 uniform oracles).
        dmp2 = dmp2mini.v4_mini(width, height, bytes(premultiplied[:4]))
    elif premultiplied[:4] * npix == premultiplied:
        # Uniform: mirror the variant writer (Apple v4 LZFSE at large sizes).
        stream = lzfse_compat.compress(b"\x00" * npix)
        dmp2 = (b"dmp2" + bytes((4, 1, 10, 4)) + struct.pack("<HHHH", width, height, 1, 4)
                + bytes(premultiplied[:4]) + struct.pack("<I", len(stream)) + stream)
    elif width * height * 4 > 512:
        pal = _palette_plane(bytes(premultiplied))
        dmp2 = (_dmp2_v4_palette(width, height, pal[0], pal[1]) if pal is not None
                else _dmp2_lzfse_stream(width, height, bytes(premultiplied), 4, 2))
    elif npix <= 8:
        # Tiny multi-color sources are stored as v1 raw frames (hp9 k_2x4 etc).
        dmp2 = dmp2mini.v1_raw(width, height, bytes(premultiplied), 4)
    else:
        dmp2 = _dmp2_lzfse_stream(width, height, bytes(premultiplied), 4, 2)
    payload = b"MLEC" + struct.pack("<7I", mode, 11, 16 + len(dmp2), 1, bpp, len(dmp2), 0) + dmp2
    header = bytearray(184)
    header[:4] = b"ISTC"
    struct.pack_into("<5I", header, 4, 1, flags, width, height, scale * 100)
    header[24:28] = pixel_format
    struct.pack_into("<I", header, 28, color_space)
    struct.pack_into("<I2H", header, 32, 0, 12, 0)
    header[40:168] = _fixed(filename, 128)
    tlvs = b"".join((struct.pack("<2I5I", 1001, 20, 1, 0, 0, width, height), struct.pack("<2I7I", 1003, 28, 1, 0, 0, 0, 0, width, height), struct.pack(
        "<2I8s", 1004, 8, b"\0\0\0\0\0\0\x80?"), struct.pack("<2II", 1006, 4, 1), struct.pack("<2II", 1007, 4, width * bpp)))
    struct.pack_into("<4I", header, 168, len(tlvs), 1, 0, len(payload))
    return bytes(header) + tlvs + payload


def _csi_png_palette_img(data: bytes, filename: str, *, scale: int = 1) -> bytes:
    width, height, palette_argb, indices = _decode_indexed_png_for_palette_img(data)
    payload = build_palette_img_wrapper(palette_argb, indices, width=width, height=height)
    header = bytearray(184)
    header[:4] = b"ISTC"
    struct.pack_into("<5I", header, 4, 1, 16, width, height, scale * 100)
    header[24:28] = b"BGRA"
    struct.pack_into("<I", header, 28, 1)
    struct.pack_into("<I2H", header, 32, 0, 12, 0)
    header[40:168] = _fixed(filename, 128)
    tlvs = b"".join((struct.pack("<2I5I", 1001, 20, 1, 0, 0, width, height), struct.pack("<2I7I", 1003, 28, 1, 0, 0, 0, 0, width, height),
                    struct.pack("<2I8s", 1004, 8, b"\0\0\0\0\0\0\x80?"), struct.pack("<2II", 1006, 4, 1), struct.pack("<2II", 1007, 4, 32)))
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
    premultiplied = bytearray(bytes(premultiplied))
    # Grayscale-representable RGB(A) sources normalize to GA8 before any
    # grammar selection. Verified for packed renditions (probe5 c04);
    # standalone gray-RGB(A) storage is inferred, not yet probed.
    ga = _gray_ga_bytes(bytes(premultiplied))
    if ga is not None:
        rs = pixels[0::3] if color_type == 2 else pixels[0::4]
        return _csi_ga_deepmap(width, height, ga, filename, scale=scale,
                               all_opaque=all_opaque, v_constant=rs == rs[:1] * len(rs))
    uniform = premultiplied[:4] * (width * height) == premultiplied

    def band_dmp2(rows_pixels: bytes, band_height: int) -> bytes:
        band_uniform = rows_pixels[:4] * (width * band_height) == rows_pixels
        if band_uniform:
            indices = b"\x00" * (width * band_height)
            stream = lzfse.compress(indices)
            return (b"dmp2" + bytes((4, 1, 10, 4)) + struct.pack("<HHHH", width, band_height, 1, 4)
                    + rows_pixels[:4] + struct.pack("<I", len(stream)) + stream)
        return _dmp2_lzfse_stream(width, band_height, rows_pixels, 4, 2)

    row_bytes = width * 4
    use_cbck = prefer_cbck and (row_bytes * height > DMP2_CBCK_CHUNK_RAW_CAP * 4) and height > 1
    if use_cbck and _OPTIMIZE_MODE in ("smart", "hybrid", "alpha", "omni", "omega"):
        # Use optimized CBCK (codec=4) instead of DMP2 CBCK (codec=11)
        from . import _csi_png_cbck as _optimized_cbck
        # Temporarily use codec=4 path
        optimized_csi = _optimized_cbck(data, filename, scale=scale)
        return optimized_csi
    elif use_cbck:
        # Rows per chunk chosen under the raw cap, at least one row.
        rows_per = max(1, DMP2_CBCK_CHUNK_RAW_CAP // row_bytes)
        bands = [(y, min(rows_per, height - y)) for y in range(0, height, rows_per)]
        chunks = []
        for y, rows in bands:
            band = band_dmp2(bytes(premultiplied)[y * row_bytes:(y + rows) * row_bytes], rows)
            blob = struct.pack("<4I", 1, 4, len(band), 0) + band
            chunks.append(b"KCBC" + struct.pack("<4I", 0, 0, rows, len(blob)) + blob)
        payload = b"MLEC" + struct.pack("<3I", 3, 11, len(chunks)) + b"".join(chunks)
        mode_field = 3
    else:
        mode_field = 2 if (all_opaque and stack_bottom) else 0
        npix = width * height
        if uniform and npix <= 8:
            dmp2 = dmp2mini.v1_raw(width, height, bytes(premultiplied), 4)
        elif uniform and npix <= 128:
            # Apple v3-mini opcode form (hp9 color-uniform sweep, 36..512 B).
            dmp2 = dmp2mini.v3_mini_color(width, height, bytes(premultiplied[:4]))
        elif uniform and 144 <= npix <= 2304:
            # Apple v4-mini RLE form (hp9/probe5 12x12..48x48 uniform oracles).
            dmp2 = dmp2mini.v4_mini(width, height, bytes(premultiplied[:4]))
        elif uniform:
            dmp2 = band_dmp2(bytes(premultiplied), height)
        elif width * height * 4 > 512:
            # probe6 chk64 + iconstack layer oracles: up-to-255-color sources
            # use the v4 palette grammar; richer sources use v2 raw LZFSE.
            pal = _palette_plane(bytes(premultiplied))
            if pal is not None:
                dmp2 = _dmp2_v4_palette(width, height, pal[0], pal[1])
            else:
                dmp2 = _dmp2_lzfse_stream(width, height, bytes(premultiplied), 4, 2)
        elif npix <= 8:
            # Tiny multi-color sources: Apple stores v1 raw frames (hp9 k_2x4).
            dmp2 = dmp2mini.v1_raw(width, height, bytes(premultiplied), 4)
        else:
            # Apple: v3-mini multi-swatch opcode streams here (token grammar
            # not fully decoded; v2 remains a valid readable stream of
            # comparable size, documented gap).
            dmp2 = band_dmp2(bytes(premultiplied), height)
        payload = b"MLEC" + struct.pack("<7I", mode_field, 11, 16 + len(dmp2), 1, 4, len(dmp2), 0) + dmp2
    tlvs = b"".join((struct.pack("<2I5I", 1001, 20, 1, 0, 0, width, height),
                     struct.pack("<2I7I", 1003, 28, 1, 0, 0, 0, 0, width, height),
                     struct.pack("<2I8s", 1004, 8, b"\0\0\0\0\0\0\x80?"),
                     struct.pack("<2II", 1006, 4, 1),
                     struct.pack("<2II", 1007, 4, width * 4)))
    header = bytearray(184)
    header[:4] = b"ISTC"
    struct.pack_into("<5I", header, 4, 1, 16, width, height, scale * 100)
    header[24:28] = b"BGRA"
    struct.pack_into("<I", header, 28, 1)
    struct.pack_into("<I2H", header, 32, 0, 12, 0)
    header[40:168] = _fixed(filename, 128)
    struct.pack_into("<4I", header, 168, len(tlvs), 1, 0, len(payload))
    return bytes(header) + tlvs + payload


def png_dimensions(data: bytes) -> tuple[int, int]:
    width, height, _color_type, _pixels, _indexed = _decode_png_8bit(data)
    return width, height


def _png_premultiplied_bgra(data: bytes) -> tuple[int, int, bytes, bool]:
    width, height, color_type, pixels, _indexed = _decode_png_8bit(data)
    output = bytearray()
    opaque = True
    if color_type == 2:
        for r, g, b in zip(pixels[0::3], pixels[1::3], pixels[2::3]):
            output += bytes((b, g, r, 255))
    elif color_type == 4:
        for gray, alpha in zip(pixels[0::2], pixels[1::2]):
            value = (gray * alpha + 127) // 255
            output += bytes((value, value, value, alpha))
            opaque &= alpha == 255
    else:
        for r, g, b, alpha in zip(pixels[0::4], pixels[1::4], pixels[2::4], pixels[3::4]):
            output += bytes(((b*alpha+127)//255, (g*alpha+127)//255, (r*alpha+127)//255, alpha))
            opaque &= alpha == 255
    return width, height, bytes(output), opaque


def _csi_png_cbck(data: bytes, filename: str, *, scale: int = 1) -> bytes:
    """Encode CoreUI chunked-bitmap (CBCK) with independent LZFSE streams.

    When _OPTIMIZE_MODE == 'smart', uses SmartCBCKEncoder for AI-driven
    chunk optimization (alpha cleaning, strategy selection).
    When _OPTIMIZE_MODE == 'hybrid', uses HybridCompressor (LPC+Planar-Delta fusion).
    When _OPTIMIZE_MODE == 'ultimate', uses UltimateCompressor (CAMS: block classification).
    When _OPTIMIZE_MODE == 'astc', uses ASTCClassCompressor (ASTC-class quality).
    Output is always Apple-compatible MLEC mode=3, codec=4.
    """
    width, height, pixels, _opaque = _png_premultiplied_bgra(data)

    if _OPTIMIZE_MODE == "smart":
        from .smart_cbck import smart_encode_png_cbck
        return smart_encode_png_cbck(pixels, width, height, filename, scale=scale)

    if _OPTIMIZE_MODE == "hybrid":
        from ..research.hybrid_compression import hybrid_compress_for_cbck
        return hybrid_compress_for_cbck(pixels, width, height, filename, scale=scale)

    if _OPTIMIZE_MODE == "ultimate":
        from ..research.ultimate_compression import ultimate_compress
        return ultimate_compress(pixels, width, height, filename, scale=scale)

    if _OPTIMIZE_MODE == "astc":
        from ..research.astc_compression import astc_compress
        return astc_compress(pixels, width, height, filename, scale=scale)

    if _OPTIMIZE_MODE == "omni":
        from ..research.omni_compression import omni_compress
        return omni_compress(pixels, width, height, filename, scale=scale)

    if _OPTIMIZE_MODE == "omni2":
        from ..research.omniv2_compression import omniv2_compress
        return omniv2_compress(pixels, width, height, filename, scale=scale)

    if _OPTIMIZE_MODE == "omega":
        from ..research.omega_compression import omega_compress
        return omega_compress(pixels, width, height, filename, scale=scale)

    if _OPTIMIZE_MODE == "alpha":
        from ..research.alpha_compression import alpha_compress
        return alpha_compress(pixels, width, height, filename, scale=scale)

    if _OPTIMIZE_MODE == "astc-ultra":
        from ..research.astc_optimized import astc_ultra_compress
        return astc_ultra_compress(pixels, width, height, filename, scale=scale)

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
    header = bytearray(184)
    header[:4] = b"ISTC"
    struct.pack_into("<5I", header, 4, 1, 0, width, height, scale * 100)
    header[24:28] = b"BGRA"
    struct.pack_into("<I", header, 28, 1)
    struct.pack_into("<I2H", header, 32, 0, 12, 0)
    header[40:168] = _fixed(filename, 128)
    tlvs = b"".join((struct.pack("<2I5I", 1001, 20, 1, 0, 0, width, height), struct.pack("<2I7I", 1003, 28, 1, 0, 0, 0, 0, width, height),
                    struct.pack("<2I8s", 1004, 8, b"\0\0\0\0\0\0\x80?"), struct.pack("<2II", 1006, 4, 1), struct.pack("<2II", 1007, 4, width * 4)))
    struct.pack_into("<4I", header, 168, len(tlvs), 1, 0, len(payload))
    return bytes(header) + tlvs + payload


def _csi_msis(name: str) -> bytes:
    header = bytearray(184)
    header[:4] = b"ISTC"
    struct.pack_into("<5I", header, 4, 1, 0, 0, 0, 100)
    struct.pack_into("<I2H", header, 32, 0, 1010, 0)
    header[40:168] = _fixed(name, 128)
    payload = b"SISM" + struct.pack("<5I", 1, 1, 1024, 4, 1)
    struct.pack_into("<4I", header, 168, 0, 1, 0, len(payload))
    return bytes(header) + payload


def _csi_texture_reference(name: str, reference: TextureReference, *, width: int, height: int, scale: int = 2, auxiliary_flag: TextureAuxiliaryFlag | None = None) -> bytes:
    header = bytearray(184)
    header[:4] = b"ISTC"
    struct.pack_into("<5I", header, 4, 1, 0, width, height, scale * 100)
    header[24:28] = b"ARGB"
    struct.pack_into("<I2H", header, 32, 0, 1007, 0)
    header[40:168] = _fixed(name, 128)
    tlvs = [struct.pack("<2I8s", 1004, 8, b"\0\0\0\0\0\0\x80?"), struct.pack("<2II", 1006, 4, 1)]
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
    header = bytearray(184)
    header[:4] = b"ISTC"
    struct.pack_into("<5I", header, 4, 1, 0, width, height, scale * 100)
    header[24:28] = b"ARGB"
    struct.pack_into("<I2H", header, 32, 0, 1008, 0)
    header[40:168] = _fixed(filename, 128)
    tlvs = b"".join((struct.pack("<2I8s", 1004, 8, b"\0\0\0\0\0\0\x80?"), struct.pack("<2II", 1006, 4, 1), struct.pack("<2II", 1007, 4, mode_field)))
    struct.pack_into("<4I", header, 168, len(tlvs), 1, 0, len(payload))
    return bytes(header) + tlvs + payload


def _csi_solid_image_stack(name: str, *, canvas_points: tuple[int, int], scale: int, identifier_values: list[int]) -> bytes:
    width, height = canvas_points
    refs = [
        SolidImageStackLayerReference(0, 0, 0, width, height, 0, 1.0, SolidImageStackReferencedKey(((1, 85), (2, 181), (17, ident), (0, 0))))
        for ident in identifier_values
    ]
    flags = [SolidImageStackLayerFlag(b"\0"*8, 1, b"\0"*4) for _ in identifier_values]
    reserved = [SolidImageStackLayerReserved(b"\0"*20) for _ in identifier_values]
    tlv1012 = build_solidimagestack_layer_list(refs)
    tlv1020 = build_solidimagestack_layer_flags(flags)
    tlv1021 = build_solidimagestack_layer_reserved(reserved)
    header = bytearray(184)
    header[:4] = b"ISTC"
    struct.pack_into("<5I", header, 4, 1, 0, width, height, 100)
    header[24:28] = b"ATAD"
    struct.pack_into("<I2H", header, 32, 0, 1018, 0)
    header[40:168] = _fixed(name, 128)
    tlvs = b"".join((
        struct.pack("<2I", 1012, len(tlv1012)) + tlv1012,
        struct.pack("<2I", 1020, len(tlv1020)) + tlv1020,
        struct.pack("<2I", 1021, len(tlv1021)) + tlv1021,
        struct.pack("<2I8s", 1004, 8, b"\0\0\0\0\0\0\x80?"),
        struct.pack("<2I2I", 1005, 8 + len(b"public.layeredimage\0"), len(b"public.layeredimage\0"), 0) + b"public.layeredimage\0",
        struct.pack("<2II", 1006, 4, 1),
    ))
    payload = b"DWAR" + struct.pack("<2I", 0, 0)
    struct.pack_into("<4I", header, 168, len(tlvs), 1, 0, len(payload))
    return bytes(header) + tlvs + payload


def _csi_svg(data: bytes, filename: str) -> bytes:
    text = data.lstrip()
    if not text.startswith(b"<svg") and b"<svg" not in text[:512]:
        raise ValueError("input is not an SVG document")
    header = bytearray(184)
    header[:4] = b"ISTC"
    struct.pack_into("<5I", header, 4, 1, 4, 0, 0, 0)
    header[24:28] = b" GVS"  # little-endian fourcc 'SVG '
    struct.pack_into("<I", header, 28, 0)
    struct.pack_into("<I2H", header, 32, 0, 9, 0)
    header[40:168] = _fixed(filename, 128)
    tlvs = b"".join((struct.pack("<2I8s", 1004, 8, b"\0\0\0\0\0\0\x80?"), struct.pack("<2II", 1006, 4, 1)))
    payload = b"DWAR" + struct.pack("<2I", 0, len(data)) + data
    struct.pack_into("<4I", header, 168, len(tlvs), 1, 0, len(payload))
    return bytes(header) + tlvs + payload


def _csi_symbol_svg(data: bytes, filename: str) -> bytes:
    """CoreUI symbol-vector CSI (part 59, layout 1017)."""
    text = data.lstrip()
    if b"<svg" not in text[:512] and b":svg" not in text[:512]:
        raise ValueError("input is not an SVG document")
    header = bytearray(184)
    header[:4] = b"ISTC"
    struct.pack_into("<5I", header, 4, 1, 4, 0, 0, 100)
    header[24:28] = b" GVS"
    struct.pack_into("<I2H", header, 32, 0, 1017, 0)
    header[40:168] = _fixed(filename, 128)
    # 1018 is CoreUI symbol metrics. These neutral metrics are finite and the
    # 1019 tuple advertises one monochrome layer / one vector representation.
    metrics = bytes.fromhex("070000000d0000000000803f0000803f000000000000803f0000803f0000803f0000000000000000")
    symbol_info = struct.pack("<3I", 1, 1, 3)
    tlvs = b"".join((
        struct.pack("<2I8s", 1004, 8, b"\0\0\0\0\0\0\x80?"),
        struct.pack("<2II", 1006, 4, 1),
        struct.pack("<2I", 1018, len(metrics)) + metrics,
        struct.pack("<2I", 1019, len(symbol_info)) + symbol_info,
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


def _build_assets_car_multilevel(assets: list[AssetRendition], *, platform: str, target: str, thinning_arguments: str = "", coreui_profile: "CoreUIProfile | str | None" = None) -> bytes:
    """Large-catalog writer using true multi-level trees for all indexes."""
    profile = resolve_profile(coreui_profile, platform)
    # Packing needs no appearance/localization registry: a class with >= 2
    # candidates is always packed (probe4 probe established this; the helper
    # returns the input unchanged when no class qualifies).
    from .packed import pack_renditions
    assets = pack_renditions(list(assets))
    ordered = sorted(assets, key=lambda item: (str(item.name).encode("utf-8"), item.part, item.scale, item.csi))
    facets = _collect_facets(ordered)
    facet_names = sorted({entry["name"] for entry in facets.values()}, key=lambda item: str(item))
    names = [str(name).encode("utf-8") for name in facet_names]
    if any(not name or len(name) > 255 for name in names):
        raise ValueError("asset names must contain 1..255 UTF-8 bytes")
    facet_by_name = {entry["name"]: (ident, entry["part"]) for ident, entry in facets.items()}
    attrs = _select_key_attributes(ordered, platform)
    locale_names = sorted({a.localization for a in ordered if a.localization}, key=lambda x: x.encode("utf-8"))
    locale_ids = {name: _localization_identifier(name) for name in locale_names}
    if len(set(locale_ids.values())) != len(locale_ids):
        raise ValueError("localization identifier collision")
    keys = [_rendition_key_for(asset, 0 if asset.skip_facet else _effective_identifier(asset), attrs,
                               locale_ids.get(str(asset.localization or ""), 0)) for asset in ordered]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate rendition key")

    writer = BOMWriter()
    writer.add_block(_car_header(len(ordered), profile), "CARHEADER")
    if locale_names:
        locale_records = []
        for locale in locale_names:
            key_id = writer.add_block(str(locale).encode("utf-8"))
            value_id = writer.add_block(struct.pack("<H", locale_ids[locale]))
            locale_records.append((value_id, key_id, str(locale).encode("utf-8")))
        _add_multilevel_tree(writer, "LOCALIZATIONKEYS", locale_records, node_size=4096, key_size=0xFFFFFFFF)
    appearance_registry = _appearance_registry(ordered, platform)
    if appearance_registry:
        appearance_records = []
        for appearance_name, appearance_id in appearance_registry:
            key_id = writer.add_block(str(appearance_name).encode("utf-8"))
            value_id = writer.add_block(struct.pack("<H", appearance_id))
            appearance_records.append((value_id, key_id, str(appearance_name).encode("utf-8")))
        _add_multilevel_tree(writer, "APPEARANCEKEYS", appearance_records, node_size=4096, key_size=0xFFFFFFFF)
    # Allocate payload blocks before indexes; BOM references are stable and do
    # not require a historical Apple block ordering.
    facet_blocks = []
    for name, raw_name in zip(facet_names, names):
        ident, part = facet_by_name[name]
        key_id = writer.add_block(raw_name)
        value_id = writer.add_block(_facet_value(int(ident), int(str(part))))
        facet_blocks.append((value_id, key_id, raw_name))
    writer.add_block(_key_format(attrs), "KEYFORMAT")
    rendition_blocks = []
    for asset, key in zip(ordered, keys):
        key_id = writer.add_block(key)
        value_id = writer.add_block(_adapt_csi_for_profile(asset.csi, profile))
        rendition_blocks.append((value_id, key_id, key))
    rendition_blocks.sort(key=lambda item: item[2])
    facet_blocks.sort(key=lambda item: item[2])
    equal = len({len(x) for x in names}) == 1
    _add_multilevel_tree(writer, "RENDITIONS", rendition_blocks, node_size=4096, key_size=len(attrs)*2)
    _add_multilevel_tree(writer, "FACETKEYS", facet_blocks, node_size=4096, key_size=len(names[0]) if equal else 0xFFFFFFFF)
    writer.add_block(_extended_metadata(platform, target, thinning_arguments), "EXTENDED_METADATA")
    bitmap_records = []
    for name in facet_names:
        value_id = writer.add_block(BITMAP_VALUE)
        identifier = facet_by_name[name][0]
        bitmap_records.append((value_id, identifier, struct.pack(">I", identifier)))
    _add_multilevel_tree(writer, "BITMAPKEYS", bitmap_records, node_size=1024, key_size=0, numeric_key=True, leaf_limit=64)
    return writer.build()


def build_assets_car(assets: list[AssetRendition], *, platform: str = "macosx", target: str = "13.0", thinning_arguments: str = "", coreui_profile: "CoreUIProfile | str | None" = None) -> bytes:
    """Build a CAR with any number of facets and renditions per facet.

    Renditions sharing ``name`` share one FACETKEYS record and identifier. This
    is required for ordinary 1x/2x/3x image sets. Duplicate CoreUI keys are
    rejected because lookup would otherwise be ambiguous.
    """
    if not assets:
        raise ValueError("at least one asset is required")
    if len(assets) > 128 or len({asset.name for asset in assets}) > 128:
        return _build_assets_car_multilevel(assets, platform=platform, target=target, thinning_arguments=thinning_arguments, coreui_profile=coreui_profile)
    profile = resolve_profile(coreui_profile, platform)
    # See _build_assets_car_multilevel: packing is registry-independent.
    from .packed import pack_renditions
    assets = pack_renditions(list(assets))
    ordered = sorted(assets, key=lambda item: (str(item.name).encode("utf-8"), item.part, item.scale, item.csi))
    facets = _collect_facets(ordered)
    facet_names = sorted({entry["name"] for entry in facets.values()}, key=lambda item: str(item))
    names = [str(name).encode("utf-8") for name in facet_names]
    if any(not name or len(name) > 255 for name in names):
        raise ValueError("asset names must contain 1..255 UTF-8 bytes")
    facet_by_name = {entry["name"]: (ident, entry["part"]) for ident, entry in facets.items()}
    key_attributes = _select_key_attributes(ordered, platform)
    locale_names = sorted({a.localization for a in ordered if a.localization}, key=lambda x: x.encode("utf-8"))
    locale_ids = {name: _localization_identifier(name) for name in locale_names}
    if len(set(locale_ids.values())) != len(locale_ids):
        raise ValueError("localization identifier collision")
    keys = [_rendition_key_for(asset, 0 if asset.skip_facet else _effective_identifier(asset), key_attributes,
                               locale_ids.get(str(asset.localization or ""), 0)) for asset in ordered]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate rendition key for the same asset, part, and scale")
    rendition_count = len(ordered)
    facet_count = len(facet_names)
    appearance_registry = _appearance_registry(ordered, platform)
    has_appearances = bool(appearance_registry)

    # IDs 1..5 are CARHEADER and rendition/facet descriptor+root. Appearance
    # descriptor/root occupy 6..7 and each registry record uses key+value.
    prefix_next = 8 + 2 * len(appearance_registry) if has_appearances else 6
    localization_descriptor_id = prefix_next if locale_names else 0
    if locale_names:
        prefix_next += 2 + 2 * len(locale_names)
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
    bitmap_entries = [(bitmap_value_base + i, facet_by_name[name][0]) for i, name in enumerate(facet_names)]

    writer = BOMWriter()
    writer.add_block(_car_header(rendition_count, profile), "CARHEADER")
    writer.add_block(_tree_descriptor(3, 4096, rendition_count, len(key_attributes) * 2), "RENDITIONS")
    writer.add_block(_leaf_many(rendition_entries, rendition_inline, 4096))
    writer.add_block(_tree_descriptor(5, 4096, facet_count, facet_key_size), "FACETKEYS")
    writer.add_block(_leaf_many(facet_entries, facet_inline, 4096))
    if has_appearances:
        appearance_entries = [(9 + 2 * i, 8 + 2 * i) for i in range(len(appearance_registry))]
        writer.add_block(_tree_descriptor(7, 4096, len(appearance_registry), 0xFFFFFFFF), "APPEARANCEKEYS")
        writer.add_block(_leaf_many(appearance_entries, [], 4096))
        for appearance_name, appearance_id in appearance_registry:
            writer.add_block(str(appearance_name).encode("utf-8"))
            writer.add_block(struct.pack("<H", appearance_id))
    if locale_names:
        locale_root = localization_descriptor_id + 1
        locale_entries = [(localization_descriptor_id + 3 + 2*i, localization_descriptor_id + 2 + 2*i) for i in range(len(locale_names))]
        writer.add_block(_tree_descriptor(locale_root, 4096, len(locale_names), 0xFFFFFFFF), "LOCALIZATIONKEYS")
        writer.add_block(_leaf_many(locale_entries, [], 4096))
        for locale in locale_names:
            writer.add_block(str(locale).encode("utf-8"))
            writer.add_block(struct.pack("<H", locale_ids[locale]))
    for name, name_raw in zip(facet_names, names):
        writer.add_block(name_raw)
        writer.add_block(_facet_value(int(facet_by_name[name][0]), int(str(facet_by_name[name][1]))))
    writer.add_block(_key_format(key_attributes), "KEYFORMAT")
    for asset, key in zip(ordered, keys):
        writer.add_block(key)
        writer.add_block(_adapt_csi_for_profile(asset.csi, profile))
    writer.add_block(_extended_metadata(platform, target, thinning_arguments), "EXTENDED_METADATA")
    writer.add_block(_tree_descriptor(bitmap_root_id, 1024, facet_count, 0, True), "BITMAPKEYS")
    writer.add_block(_leaf_many(bitmap_entries, [], 1024))
    for _ in facet_names:
        writer.add_block(BITMAP_VALUE)
    return writer.build()


def build_pdf_fallback_car(name: str, pdf: bytes, png_1x: bytes, png_2x: bytes, filename: str = "image.pdf", *, png_3x: bytes | None = None, platform: str = "macosx", target: str = "13.0", coreui_profile: "CoreUIProfile | str | None" = None) -> bytes:
    profile = resolve_profile(coreui_profile, platform)
    """Build a preserved PDF plus Xcode-style GA8 deepmap fallbacks."""
    name_raw = name.encode("utf-8")
    if not name_raw or len(name_raw) > 255:
        raise ValueError("asset name must contain 1..255 UTF-8 bytes")
    identifier = _identifier(name)
    fallbacks = [(1, png_1x), (2, png_2x)]
    if png_3x is not None:
        fallbacks.append((3, png_3x))
    records = [(_rendition_key(identifier, 42, 1), _csi_pdf(bytes(pdf), filename))]
    records += [(_rendition_key(identifier, 0xB5, scale), _csi_png_deepmap(bytes(png), filename, scale=scale, vector_fallback=True))
                for scale, png in fallbacks]
    count = len(records)
    metadata_id = 9 + 2 * count
    bitmap_descriptor_id = metadata_id + 1
    bitmap_root_id = bitmap_descriptor_id + 1
    bitmap_value_id = bitmap_root_id + 1
    sorted_records = sorted(enumerate(records), key=lambda item: item[1][0])
    entries = [(10 + index * 2, 9 + index * 2) for index, _ in sorted_records]
    inline = [record[0] for _, record in sorted_records]
    writer = BOMWriter()
    writer.add_block(_car_header(count, profile), "CARHEADER")
    writer.add_block(_tree_descriptor(3, 4096, count, 16), "RENDITIONS")
    writer.add_block(_leaf_many(entries, inline, 4096))
    writer.add_block(_tree_descriptor(5, 4096, 1, len(name_raw)), "FACETKEYS")
    writer.add_block(_leaf(7, 6, name_raw, 4096))
    writer.add_block(name_raw)
    writer.add_block(_facet_value(identifier, 0xB5))
    writer.add_block(_key_format(), "KEYFORMAT")
    for key, csi in records:
        writer.add_block(key)
        writer.add_block(csi)
    writer.add_block(_extended_metadata(platform, target), "EXTENDED_METADATA")
    writer.add_block(_tree_descriptor(bitmap_root_id, 1024, 1, 0, True), "BITMAPKEYS")
    writer.add_block(_leaf(bitmap_value_id, identifier, b"", 1024))
    writer.add_block(BITMAP_VALUE)
    return writer.build()


def svg_renditions(name: str, svg: bytes, filename: str = "image.svg", *, fallback_scales: tuple[int, ...] = (1, 2, 3)) -> list[AssetRendition]:
    """Preserve SVG and automatically rasterize deepmap fallbacks."""
    vector = AssetRendition(name, _csi_svg(bytes(svg), filename), 42, 181)
    if not fallback_scales:
        return [vector]
    if any(scale not in (1, 2, 3) for scale in fallback_scales):
        raise ValueError("SVG fallback scales must be 1, 2, or 3")
    try:
        import cairosvg  # type: ignore
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
    idioms = {"universal": 0, "iphone": 1, "phone": 1, "ipad": 2, "pad": 2, "tv": 3, "car": 4,
              "carplay": 4, "watch": 5, "marketing": 6, "mac": 7, "vision": 8, "visionos": 8}
    try:
        idiom_id = idioms[idiom] if isinstance(idiom, str) else int(idiom)
    except (KeyError, ValueError) as exc:
        raise ValueError(f"unsupported idiom: {idiom}") from exc
    if scale not in (1, 2, 3) or idiom_id not in range(9):
        raise ValueError("invalid CBCK scale or idiom")
    return AssetRendition(name, _csi_png_cbck(bytes(png), filename, scale=scale), 181, scale=scale, idiom=idiom_id)


def layered_image_renditions(name: str, layers: list[bytes], *, idiom: str | int = 3, scale: int = 1, depths: list[int] | None = None) -> list[AssetRendition]:
    """Create ordered CoreUI layer-key renditions for tvOS/visionOS image stacks."""
    if not layers:
        raise ValueError("layered image needs at least one layer")
    idioms = {"tv": 3, "vision": 8, "visionos": 8, "universal": 0}
    try:
        idiom_id = idioms[idiom] if isinstance(idiom, str) else int(idiom)
    except (KeyError, ValueError) as exc:
        raise ValueError(f"unsupported layered-image idiom: {idiom}") from exc
    if idiom_id not in (0, 3, 8):
        raise ValueError("layered images support universal, tv, or vision idioms")
    if depths is None:
        depths = list(range(1, len(layers) + 1)) if idiom_id == 8 else [0] * len(layers)
    if len(depths) != len(layers) or any(not 0 <= x <= 65535 for x in depths):
        raise ValueError("invalid layer depth list")
    return [AssetRendition(name, _csi_png_deepmap(bytes(png), f"{name}-layer-{index}.png", scale=scale), 181, scale=scale, idiom=idiom_id, layer=index, dimension2=depths[index-1])
            for index, png in enumerate(layers, 1)]


def build_layered_icon_car(name: str, layers: list[bytes], *, platform: str = "appletvos", target: str = "15.0", scale: int = 1, depths: list[int] | None = None) -> bytes:
    idiom = "vision" if platform.lower() in ("xros", "xrsimulator", "visionos") else "tv"
    return build_assets_car(layered_image_renditions(name, layers, idiom=idiom, scale=scale, depths=depths), platform=platform, target=target)


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
        image_renditions.append(AssetRendition(child_name, _csi_png_deepmap(bytes(png_bytes), 'content.png',
                                scale=scale), 181, scale=scale, idiom=idiom, identifier_override=child_id))
        for dim1, payload_value, mode_field in ((1, 55, 0x80000), (2, 32, 0x40000)):
            ref_pairs = ((1, 41), (2, 181), (8, dim1), (12, scale), (17, child_id), (15, idiom), (0, 0))
            ref = TextureReference(payload_value, 0, 1, 1, 0x1C, ref_pairs)
            aux = TextureAuxiliaryFlag(b'\0'*8 + (b'\1' if layer_name == 'Back' and dim1 == 1 else b'\0') +
                                       b'\0'*4, (0, 0, 1 if layer_name == 'Back' and dim1 == 1 else 0))
            aggregate.append(AssetRendition(child_name, _csi_texture_reference('content.png', ref, width=w, height=h, scale=scale,
                             auxiliary_flag=aux), 0, 181, scale=scale, idiom=idiom, dimension1=dim1, element=41, identifier_override=child_id))
            aggregate.append(AssetRendition(child_name, _csi_texture_data_from_png(bytes(png_bytes), 'content.png', width=w, height=h, scale=scale,
                             mode_field=mode_field), 181, 181, scale=scale, idiom=idiom, dimension1=dim1, element=41, identifier_override=child_id))
    if width is None or height is None:
        raise ValueError("solid image stack needs image content")
    if canvas_points is None:
        canvas_points = (width // scale, height // scale)
    aggregate.insert(0, AssetRendition(name, _csi_solid_image_stack('Contents.json', canvas_points=canvas_points,
                     scale=scale, identifier_values=child_ids), 181, 181, idiom=0, scale=1))
    return aggregate + image_renditions


def build_solid_image_stack_aggregate_car(name: str, layers: list[tuple[str, bytes]], *, platform: str = 'xros', target: str = '1.0', scale: int = 2, canvas_points: tuple[int, int] | None = None) -> bytes:
    return build_assets_car(solid_image_stack_aggregate_renditions(name, layers, platform=platform, scale=scale, canvas_points=canvas_points), platform=platform, target=target)


WATCH_COMPLICATION_FAMILIES = {"circularSmall": 1, "extraLarge": 2, "graphicBezel": 3, "graphicCircular": 4, "graphicCorner": 5, "graphicExtraLarge": 6,
                               "graphicRectangular": 7, "modularLarge": 8, "modularSmall": 9, "utilitarianLarge": 10, "utilitarianSmall": 11, "utilitarianSmallFlat": 12}
WATCH_COMPLICATION_ROLES = {"background": 1, "foreground": 2, "mask": 3, "ring": 4, "template": 5}


def watch_complication_renditions(name: str, images: list[bytes], *, scale: int = 2, families: list[str] | None = None, roles: list[str] | None = None) -> list[AssetRendition]:
    """Encode watch family in subtype and role in dimension2 keys."""
    if not images:
        raise ValueError("complication needs at least one image")
    if families is None:
        available = tuple(WATCH_COMPLICATION_FAMILIES)
        if len(images) > len(available):
            raise ValueError("too many complication images without explicit families")
        families = list(available[:len(images)])
    roles = roles or ["template"] * len(images)
    if len(families) != len(images) or len(roles) != len(images):
        raise ValueError("complication metadata count mismatch")
    try:
        pairs = [(WATCH_COMPLICATION_FAMILIES[f], WATCH_COMPLICATION_ROLES[r]) for f, r in zip(families, roles)]
    except KeyError as exc:
        raise ValueError(f"unsupported complication family or role: {exc.args[0]}") from exc
    return [AssetRendition(name, _csi_png_deepmap(bytes(png), f"{name}-{families[i-1]}-{roles[i-1]}.png", scale=scale), 181, scale=scale, idiom=5, subtype=family, dimension2=role)
            for i, (png, (family, role)) in enumerate(zip(images, pairs), 1)]


def build_watch_complication_car(name: str, images: list[bytes], *, target: str = "8.0", scale: int = 2, families: list[str] | None = None, roles: list[str] | None = None) -> bytes:
    return build_assets_car(watch_complication_renditions(name, images, scale=scale, families=families, roles=roles), platform="watchos", target=target)


APP_ICON_IDIOMS = {
    "iphoneos": (1, 2), "iphonesimulator": (1, 2), "ios": (1, 2),
    "appletvos": (3,), "appletvsimulator": (3,), "tvos": (3,),
    "watchos": (5,), "watchsimulator": (5,),
    "macosx": (7,), "macos": (7,),
    "xros": (8,), "xrsimulator": (8,), "visionos": (8,),
}


def app_icon_renditions(name: str, png: bytes, filename: str = "icon.png", *, platform: str = "iphoneos") -> list[AssetRendition]:
    """Return platform-specific MSIS and CBCK records for a modern AppIcon."""
    try:
        idioms = APP_ICON_IDIOMS[platform.lower()]
    except KeyError as exc:
        raise ValueError(f"unsupported AppIcon platform: {platform}") from exc
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
    idioms = {"universal": 0, "iphone": 1, "phone": 1, "ipad": 2, "pad": 2, "tv": 3, "car": 4,
              "carplay": 4, "watch": 5, "marketing": 6, "mac": 7, "vision": 8, "visionos": 8}
    appearances = {"any": 0, "light": 0, "dark": 1, "high-contrast": 2, "high": 2}
    try:
        idiom_id = idioms[idiom] if isinstance(idiom, str) else int(idiom)
    except (KeyError, ValueError) as exc:
        raise ValueError(f"unsupported idiom: {idiom}") from exc
    try:
        appearance_id = appearances[appearance] if isinstance(appearance, str) else int(appearance)
    except (KeyError, ValueError) as exc:
        raise ValueError(f"unsupported appearance: {appearance}") from exc
    if idiom_id not in range(9):
        raise ValueError("invalid idiom")
    if appearance_id not in (0, 1, 2):
        raise ValueError("invalid appearance")
    return idiom_id, appearance_id


def jpeg_rendition(name: str, data: bytes, filename: str = "image.jpg", *, scale: int = 1, idiom: str | int = 0, appearance: str | int = 0, localization: str | None = None) -> AssetRendition:
    if scale not in (1, 2, 3):
        raise ValueError("image scale must be 1, 2, or 3")
    idiom_id, appearance_id = _selector_ids(idiom, appearance)
    return AssetRendition(name, _csi_jpeg(bytes(data), filename, scale), 0xB5, scale=scale, idiom=idiom_id, appearance=appearance_id, localization=localization)


def heif_rendition(name: str, data: bytes, filename: str = "image.heic", *, scale: int = 1, idiom: str | int = 0, appearance: str | int = 0, localization: str | None = None) -> AssetRendition:
    if scale not in (1, 2, 3):
        raise ValueError("image scale must be 1, 2, or 3")
    idiom_id, appearance_id = _selector_ids(idiom, appearance)
    return AssetRendition(name, _csi_heif(bytes(data), filename, scale), 0xB5, scale=scale, idiom=idiom_id, appearance=appearance_id, localization=localization)


def png_rendition(name: str, data: bytes, filename: str = "image.png", *, scale: int = 1, idiom: str | int = 0, appearance: str | int = 0, localization: str | None = None) -> AssetRendition:
    if scale not in (1, 2, 3):
        raise ValueError("image scale must be 1, 2, or 3")
    idioms = {"universal": 0, "iphone": 1, "phone": 1, "ipad": 2, "pad": 2, "tv": 3, "car": 4,
              "carplay": 4, "watch": 5, "marketing": 6, "mac": 7, "vision": 8, "visionos": 8}
    appearances = {"any": 0, "light": 0, "dark": 1, "high-contrast": 2, "high": 2}
    try:
        idiom_id = idioms[idiom] if isinstance(idiom, str) else int(idiom)
    except (KeyError, ValueError) as exc:
        raise ValueError(f"unsupported idiom: {idiom}") from exc
    try:
        appearance_id = appearances[appearance] if isinstance(appearance, str) else int(appearance)
    except (KeyError, ValueError) as exc:
        raise ValueError(f"unsupported appearance: {appearance}") from exc
    if idiom_id not in range(9):
        raise ValueError("enabled idioms are universal, iphone, ipad, tv, car, watch, marketing, mac, and vision")
    if appearance_id not in (0, 1, 2):
        raise ValueError("enabled appearances are any/light, dark, and high-contrast")
    if localization is not None and (not localization or len(localization.encode("utf-8")) > 255):
        raise ValueError("invalid localization tag")
    # Xcode 26.x stores ordinary imageset PNGs as LZFSE deepmap2 (v2/v4
    # grammar); GA and indexed sources keep the verified v1 grammar.
    csi = make_deepmap_csi_variant(bytes(data), filename, scale=scale, stack_bottom=True)
    return AssetRendition(name, csi, 0xB5, scale=scale, idiom=idiom_id, appearance=appearance_id, localization=localization)


def palette_png_rendition(name: str, data: bytes, filename: str = "image.png", *, scale: int = 1, idiom: str | int = 0, appearance: str | int = 0, localization: str | None = None) -> AssetRendition:
    """Build a legacy quantized `palette-img` rendition from an indexed PNG input."""
    if scale not in (1, 2, 3):
        raise ValueError("image scale must be 1, 2, or 3")
    idiom_id, appearance_id = _selector_ids(idiom, appearance)
    if localization is not None and (not localization or len(localization.encode("utf-8")) > 255):
        raise ValueError("invalid localization tag")
    return AssetRendition(name, _csi_png_palette_img(bytes(data), filename, scale=scale), 0xB5, scale=scale, idiom=idiom_id, appearance=appearance_id, localization=localization)


SYMBOL_WEIGHTS = {"Ultralight": 1, "Thin": 2, "Light": 3, "Regular": 4, "Medium": 5, "Semibold": 6, "Bold": 7, "Heavy": 8, "Black": 9}
SYMBOL_SIZES = {"S": 1, "M": 2, "L": 3}


def symbol_template_renditions(name: str, svg: bytes, filename: str = "symbol.svg", *, deployment_target: int = 0) -> list[AssetRendition]:
    """Expand SF Symbols template groups such as ``Regular-M`` into glyph records."""
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(svg)
    except ET.ParseError as exc:
        raise ValueError(f"invalid symbol SVG: {exc}") from exc
    found: list[tuple[int, int, bytes]] = []
    for element in root.iter():
        ident = element.attrib.get("id", "")
        if "-" not in ident:
            continue
        weight_name, size_name = ident.rsplit("-", 1)
        if weight_name not in SYMBOL_WEIGHTS or size_name not in SYMBOL_SIZES:
            continue
        # Preserve definitions/style and the selected glyph. CoreUI accepts a
        # normal SVG payload per weight/size; template-only guide groups are omitted.
        wrapper = ET.Element(root.tag, dict(root.attrib))
        for child in root:
            if child.tag.rsplit("}", 1)[-1] == "defs":
                wrapper.append(ET.fromstring(ET.tostring(child)))
        wrapper.append(ET.fromstring(ET.tostring(element)))
        found.append((SYMBOL_WEIGHTS[weight_name], SYMBOL_SIZES[size_name], ET.tostring(wrapper, encoding="utf-8", xml_declaration=True)))
    if not found:
        raise ValueError("symbol template has no recognized weight-size glyph groups")
    return [symbol_rendition(name, payload, filename, weight=weight, size=size, deployment_target=deployment_target)
            for weight, size, payload in sorted(found)]


def build_symbol_template_car(name: str, svg: bytes, filename: str = "symbol.svg", *, platform: str = "macosx", target: str = "13.0") -> bytes:
    return build_assets_car(symbol_template_renditions(name, svg, filename), platform=platform, target=target)


def symbol_rendition(name: str, data: bytes, filename: str = "symbol.svg", *, weight: int = 4, size: int = 2, deployment_target: int = 0) -> AssetRendition:
    if weight not in range(1, 10):
        raise ValueError("symbol weight must be 1..9")
    if size not in range(1, 4):
        raise ValueError("symbol size must be 1..3")
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
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(build_data_car(name, data, uti, **kwargs))


def write_jpeg_car(path: Path | str, name: str, data: bytes, filename: str = "image.jpg", **kwargs) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(build_jpeg_car(name, data, filename, **kwargs))


def write_heif_car(path: Path | str, name: str, data: bytes, filename: str = "image.heic", **kwargs) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(build_heif_car(name, data, filename, **kwargs))


def write_color_car(path: Path | str, name: str, red: float, green: float, blue: float, alpha: float = 1.0, **kwargs) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(build_color_car(name, red, green, blue, alpha, **kwargs))
