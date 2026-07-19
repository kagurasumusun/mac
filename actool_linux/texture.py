from __future__ import annotations

from dataclasses import dataclass
import struct


class TextureRenditionError(ValueError):
    pass


def build_texture_reference_payload(reference: 'TextureReference') -> bytes:
    pairs = bytes().join(struct.pack('<2H', attribute, value) for attribute, value in reference.key_pairs)
    return b'RTXT' + struct.pack('<7I', reference.reserved0, reference.payload_value, reference.u32_2, reference.u32_3, reference.u32_4, len(pairs), 0) + pairs


def build_texture_auxiliary_flag(flag: 'TextureAuxiliaryFlag') -> bytes:
    if len(flag.raw) == 12:
        return flag.raw
    return struct.pack('<3I', *flag.values)


@dataclass(frozen=True)
class TextureReference:
    payload_value: int
    reserved0: int
    u32_2: int
    u32_3: int
    u32_4: int
    key_pairs: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class TextureAuxiliaryFlag:
    raw: bytes
    values: tuple[int, int, int]


def parse_texture_reference_payload(raw: bytes | bytearray | memoryview) -> TextureReference:
    data = bytes(raw)
    if len(data) < 32 or data[:4] != b'RTXT':
        raise TextureRenditionError('invalid texture reference payload')
    _tag, reserved0, payload_value, u32_2, u32_3, u32_4, key_length, reserved1 = struct.unpack_from('<8I', data, 0)
    if reserved0 != 0 or reserved1 != 0 or key_length % 4 or 32 + key_length > len(data):
        raise TextureRenditionError('texture reference header is invalid')
    pairs = []
    for off in range(32, 32 + key_length, 4):
        pairs.append(struct.unpack_from('<2H', data, off))
    if 32 + key_length != len(data):
        raise TextureRenditionError('texture reference payload has trailing bytes')
    return TextureReference(payload_value, reserved0, u32_2, u32_3, u32_4, tuple(pairs))


def parse_texture_auxiliary_flag(raw: bytes | bytearray | memoryview) -> TextureAuxiliaryFlag:
    data = bytes(raw)
    if len(data) != 12:
        raise TextureRenditionError('texture auxiliary flag payload length is invalid')
    return TextureAuxiliaryFlag(data, struct.unpack('<3I', data))
