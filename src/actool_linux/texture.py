from __future__ import annotations

from dataclasses import dataclass
import struct


class TextureRenditionError(ValueError):
    pass


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
    if len(data) < 32:
        raise TextureRenditionError('texture reference payload is truncated')
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
