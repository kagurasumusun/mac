from __future__ import annotations

from dataclasses import dataclass
import struct
import uuid

from .bom import BOMError, BOMStore
from .csi import CSIHeader, parse_csi
from .tree import read_leaf_entries


ATTRIBUTE_NAMES = {
    0: "kCRThemeLookName",
    1: "kCRThemeElementName",
    2: "kCRThemePartName",
    3: "kCRThemeSizeName",
    4: "kCRThemeDirectionName",
    5: "kCRThemePlaceholderName",
    6: "kCRThemeValueName",
    7: "kCRThemeAppearanceName",
    8: "kCRThemeDimension1Name",
    9: "kCRThemeDimension2Name",
    10: "kCRThemeStateName",
    11: "kCRThemeLayerName",
    12: "kCRThemeScaleName",
    13: "kCRThemeLocalizationName",
    14: "kCRThemePresentationStateName",
    15: "kCRThemeIdiomName",
    16: "kCRThemeSubtypeName",
    17: "kCRThemeIdentifierName",
    18: "kCRThemePreviousValueName",
    19: "kCRThemePreviousStateName",
    20: "kCRThemeSizeClassHorizontalName",
    21: "kCRThemeSizeClassVerticalName",
    22: "kCRThemeMemoryClassName",
    23: "kCRThemeGraphicsClassName",
    24: "kCRThemeDisplayGamutName",
    25: "kCRThemeDeploymentTargetName",
    26: "kCRThemeGlyphWeightName",
    27: "kCRThemeGlyphSizeName",
}


@dataclass(frozen=True)
class CARHeader:
    byte_order: str
    core_ui_version: int
    storage_version: int
    storage_timestamp: int
    rendition_count: int
    schema_version: int
    main_version: str
    version_string: str
    identifier: str
    associated_checksum: int
    color_space_id: int
    key_semantics: int


@dataclass(frozen=True)
class ExtendedMetadata:
    thinning_arguments: str
    deployment_platform_version: str
    deployment_platform: str
    authoring_tool: str


@dataclass(frozen=True)
class Facet:
    name: str
    cursor_hotspot: tuple[int, int]
    attributes: tuple[tuple[int, int], ...]

    @property
    def named_attributes(self) -> dict[str, int]:
        return {ATTRIBUTE_NAMES.get(key, f"UNKNOWN({key})"): value for key, value in self.attributes}


@dataclass(frozen=True)
class Rendition:
    key_values: tuple[int, ...]
    key: dict[str, int]
    csi: CSIHeader


@dataclass(frozen=True)
class NamedValueRegistryEntry:
    name: str
    value: int


@dataclass(frozen=True)
class KeyFormat:
    byte_order: str
    attributes: tuple[int, ...]

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(ATTRIBUTE_NAMES.get(value, f"UNKNOWN({value})") for value in self.attributes)


def _cstring(raw: bytes) -> str:
    return raw.split(b"\0", 1)[0].decode("utf-8", "replace")


def parse_car_header(raw: bytes | memoryview) -> CARHeader:
    data = bytes(raw)
    if len(data) < 436:
        raise BOMError(f"CARHEADER block is truncated: expected 436 bytes, got {len(data)}")
    if data[:4] == b"RATC":
        order, label = "<", "little"
    elif data[:4] == b"CTAR":
        order, label = ">", "big"
    else:
        raise BOMError(f"invalid CARHEADER magic: {data[:4]!r}")
    core_ui, storage, timestamp, rendition_count = struct.unpack_from(order + "4I", data, 4)
    main_version = _cstring(data[20:148])
    version_string = _cstring(data[148:404])
    identifier = str(uuid.UUID(bytes=bytes(data[404:420])))
    checksum, schema, color_space, key_semantics = struct.unpack_from(order + "4I", data, 420)
    return CARHeader(
        label, core_ui, storage, timestamp, rendition_count, schema,
        main_version, version_string, identifier, checksum, color_space,
        key_semantics,
    )


def parse_extended_metadata(raw: bytes | memoryview) -> ExtendedMetadata:
    data = bytes(raw)
    if len(data) < 1028:
        raise BOMError(f"EXTENDED_METADATA block is truncated: expected 1028 bytes, got {len(data)}")
    if data[:4] not in (b"META", b"ATEM"):
        raise BOMError(f"invalid EXTENDED_METADATA magic: {data[:4]!r}")
    return ExtendedMetadata(
        _cstring(data[4:260]),
        _cstring(data[260:516]),
        _cstring(data[516:772]),
        _cstring(data[772:1028]),
    )


def parse_facet(name_raw: bytes, value_raw: bytes) -> Facet:
    try:
        name = name_raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BOMError("facet name is not UTF-8") from exc
    if len(value_raw) < 6:
        raise BOMError(f"facet {name!r} value is truncated")
    hotspot_x, hotspot_y, count = struct.unpack_from("<3H", value_raw)
    if count > 1024 or 6 + count * 4 > len(value_raw):
        raise BOMError(f"facet {name!r} has an invalid attribute count: {count}")
    attributes = tuple(
        struct.unpack_from("<2H", value_raw, 6 + index * 4)
        for index in range(count)
    )
    return Facet(name, (hotspot_x, hotspot_y), attributes)


def parse_key_format(raw: bytes | memoryview) -> KeyFormat:
    data = bytes(raw)
    if len(data) < 12:
        raise BOMError("KEYFORMAT block is truncated")
    if data[:4] == b"tmfk":
        order, label = "<", "little"
    elif data[:4] == b"kfmt":
        order, label = ">", "big"
    else:
        raise BOMError(f"invalid KEYFORMAT magic: {data[:4]!r}")
    _reserved, count = struct.unpack_from(order + "2I", data, 4)
    if count > 1024 or 12 + count * 4 > len(data):
        raise BOMError(f"invalid KEYFORMAT attribute count: {count}")
    attributes = struct.unpack_from(order + f"{count}I", data, 12) if count else ()
    return KeyFormat(label, tuple(attributes))


def parse_rendition(key_raw: bytes, value_raw: bytes, key_format: KeyFormat) -> Rendition:
    count = len(key_format.attributes)
    if len(key_raw) != count * 2:
        raise BOMError(
            f"rendition key length mismatch: expected {count * 2}, got {len(key_raw)}"
        )
    order = "<" if key_format.byte_order == "little" else ">"
    values = struct.unpack(order + f"{count}H", key_raw) if count else ()
    named = {
        ATTRIBUTE_NAMES.get(attribute, f"UNKNOWN({attribute})"): value
        for attribute, value in zip(key_format.attributes, values)
    }
    return Rendition(tuple(values), named, parse_csi(value_raw))


def parse_named_value_registry_entry(key_raw: bytes, value_raw: bytes) -> NamedValueRegistryEntry:
    try:
        name = key_raw.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise BOMError('registry key is not UTF-8') from exc
    if len(value_raw) < 2:
        raise BOMError(f'registry value for {name!r} is truncated')
    return NamedValueRegistryEntry(name, int.from_bytes(value_raw[:2], 'little'))


class CARFile:
    def __init__(self, store: BOMStore):
        self.store = store
        self.header = parse_car_header(store.named_block("CARHEADER"))
        self.key_format = parse_key_format(store.named_block("KEYFORMAT"))
        self.extended_metadata = (
            parse_extended_metadata(store.named_block("EXTENDED_METADATA"))
            if "EXTENDED_METADATA" in store.variables else None
        )
        self.appearances = tuple(
            parse_named_value_registry_entry(entry.key, entry.value)
            for entry in read_leaf_entries(store, 'APPEARANCEKEYS')
        ) if 'APPEARANCEKEYS' in store.variables else ()
        self.localizations = tuple(
            parse_named_value_registry_entry(entry.key, entry.value)
            for entry in read_leaf_entries(store, 'LOCALIZATIONKEYS')
        ) if 'LOCALIZATIONKEYS' in store.variables else ()
        self.facets = tuple(
            parse_facet(entry.key, entry.value)
            for entry in read_leaf_entries(store, "FACETKEYS")
        ) if "FACETKEYS" in store.variables else ()
        self.renditions = tuple(
            parse_rendition(entry.key, entry.value, self.key_format)
            for entry in read_leaf_entries(store, "RENDITIONS")
        ) if "RENDITIONS" in store.variables else ()
        if len(self.renditions) != self.header.rendition_count:
            raise BOMError(
                "CARHEADER rendition count does not match the RENDITIONS tree: "
                f"{self.header.rendition_count} != {len(self.renditions)}"
            )

    @classmethod
    def from_path(cls, path: str) -> "CARFile":
        return cls(BOMStore.from_path(path))
