from __future__ import annotations

from dataclasses import dataclass
import struct


class SolidImageStackError(ValueError):
    pass


def build_solidimagestack_layer_list(references: list['SolidImageStackLayerReference']) -> bytes:
    out = bytearray(struct.pack('<2I', len(references), 0))
    for ref in references:
        pairs = bytes().join(struct.pack('<2H', attribute, value) for attribute, value in ref.referenced_key.attribute_value_pairs)
        out += struct.pack('<6IfI', ref.origin_x, ref.origin_y, ref.reserved0, ref.width, ref.height, ref.reserved1, ref.opacity, len(pairs))
        out += pairs
    return bytes(out)


def build_solidimagestack_layer_flags(flags: list['SolidImageStackLayerFlag']) -> bytes:
    out = bytearray(struct.pack('<2I', len(flags), 0))
    for flag in flags:
        if len(flag.reserved0) != 8 or len(flag.reserved1) != 4:
            raise SolidImageStackError('solid image stack flag block has invalid reserved lengths')
        out += flag.reserved0 + bytes((flag.enabled,)) + flag.reserved1
    return bytes(out)


def build_solidimagestack_layer_reserved(entries: list['SolidImageStackLayerReserved']) -> bytes:
    out = bytearray(struct.pack('<2I', len(entries), 0))
    for entry in entries:
        if len(entry.raw) != 20:
            raise SolidImageStackError('solid image stack reserved block has invalid length')
        out += entry.raw
    return bytes(out)


@dataclass(frozen=True)
class SolidImageStackReferencedKey:
    attribute_value_pairs: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class SolidImageStackLayerReference:
    origin_x: int
    origin_y: int
    reserved0: int
    width: int
    height: int
    reserved1: int
    opacity: float
    referenced_key: SolidImageStackReferencedKey


@dataclass(frozen=True)
class SolidImageStackLayerFlag:
    reserved0: bytes
    enabled: int
    reserved1: bytes


@dataclass(frozen=True)
class SolidImageStackLayerReserved:
    raw: bytes


@dataclass(frozen=True)
class SolidImageStackLayerList:
    layers: tuple[SolidImageStackLayerReference, ...]


@dataclass(frozen=True)
class SolidImageStackLayerFlags:
    flags: tuple[SolidImageStackLayerFlag, ...]


@dataclass(frozen=True)
class SolidImageStackLayerReservedList:
    entries: tuple[SolidImageStackLayerReserved, ...]


def parse_solidimagestack_layer_list(raw: bytes | bytearray | memoryview) -> SolidImageStackLayerList:
    data = bytes(raw)
    if len(data) < 8:
        raise SolidImageStackError("solid image stack layer list is truncated")
    count, reserved = struct.unpack_from("<2I", data, 0)
    if reserved != 0:
        raise SolidImageStackError("solid image stack layer list reserved field is nonzero")
    cursor = 8
    layers: list[SolidImageStackLayerReference] = []
    for _ in range(count):
        if cursor + 32 > len(data):
            raise SolidImageStackError("solid image stack layer entry is truncated")
        origin_x, origin_y, reserved0, width, height, reserved1, opacity, key_length = struct.unpack_from("<6IfI", data, cursor)
        cursor += 32
        if key_length % 4 or cursor + key_length > len(data):
            raise SolidImageStackError("solid image stack layer key payload is invalid")
        key_pairs = []
        for off in range(cursor, cursor + key_length, 4):
            key_pairs.append(struct.unpack_from("<2H", data, off))
        cursor += key_length
        layers.append(SolidImageStackLayerReference(
            origin_x, origin_y, reserved0, width, height, reserved1, opacity,
            SolidImageStackReferencedKey(tuple(key_pairs)),
        ))
    if cursor != len(data):
        raise SolidImageStackError("solid image stack layer list has trailing bytes")
    return SolidImageStackLayerList(tuple(layers))


def parse_solidimagestack_layer_flags(raw: bytes | bytearray | memoryview) -> SolidImageStackLayerFlags:
    data = bytes(raw)
    if len(data) < 8:
        raise SolidImageStackError("solid image stack layer flags are truncated")
    count, reserved = struct.unpack_from("<2I", data, 0)
    if reserved != 0:
        raise SolidImageStackError("solid image stack layer flags reserved field is nonzero")
    cursor = 8
    flags: list[SolidImageStackLayerFlag] = []
    for _ in range(count):
        if cursor + 13 > len(data):
            raise SolidImageStackError("solid image stack layer flag entry is truncated")
        flags.append(SolidImageStackLayerFlag(data[cursor:cursor + 8], data[cursor + 8], data[cursor + 9:cursor + 13]))
        cursor += 13
    if cursor != len(data):
        raise SolidImageStackError("solid image stack layer flags have trailing bytes")
    return SolidImageStackLayerFlags(tuple(flags))


def parse_solidimagestack_layer_reserved(raw: bytes | bytearray | memoryview) -> SolidImageStackLayerReservedList:
    data = bytes(raw)
    if len(data) < 8:
        raise SolidImageStackError("solid image stack reserved payload is truncated")
    count, reserved = struct.unpack_from("<2I", data, 0)
    if reserved != 0:
        raise SolidImageStackError("solid image stack reserved field is nonzero")
    cursor = 8
    entries: list[SolidImageStackLayerReserved] = []
    for _ in range(count):
        if cursor + 20 > len(data):
            raise SolidImageStackError("solid image stack reserved entry is truncated")
        entries.append(SolidImageStackLayerReserved(data[cursor:cursor + 20]))
        cursor += 20
    if cursor != len(data):
        raise SolidImageStackError("solid image stack reserved payload has trailing bytes")
    return SolidImageStackLayerReservedList(tuple(entries))
