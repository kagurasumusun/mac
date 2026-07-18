from __future__ import annotations

from dataclasses import dataclass
import struct

from .bom import BOMError


@dataclass(frozen=True)
class CBCKChunk:
    reserved0: int
    reserved1: int
    row_count: int
    compressed: bytes


@dataclass(frozen=True)
class CBCKPayload:
    mode: int
    codec: int
    chunks: tuple[CBCKChunk, ...]

    def decompress(self) -> bytes:
        from . import lzfse_compat
        output = bytearray()
        for index, chunk in enumerate(self.chunks):
            try:
                output += lzfse_compat.decompress(chunk.compressed)
            except Exception as exc:
                raise BOMError(f"CBCK chunk {index} has an invalid LZFSE stream") from exc
        return bytes(output)


def parse_cbck(raw: bytes | bytearray | memoryview) -> CBCKPayload:
    """Parse a CoreUI MLEC mode-3, codec-4 chunked bitmap payload."""
    data = bytes(raw)
    if len(data) < 16 or data[:4] != b"MLEC":
        raise BOMError("CBCK payload has no MLEC header")
    mode, codec, count = struct.unpack_from("<3I", data, 4)
    if (mode, codec) != (3, 4):
        raise BOMError(f"payload is not CBCK: mode={mode}, codec={codec}")
    if count == 0 or count > 1_000_000:
        raise BOMError(f"invalid CBCK chunk count: {count}")
    cursor = 16
    chunks: list[CBCKChunk] = []
    for index in range(count):
        if cursor + 20 > len(data):
            raise BOMError(f"CBCK chunk {index} header is truncated")
        if data[cursor:cursor + 4] != b"KCBC":
            raise BOMError(f"CBCK chunk {index} has invalid magic")
        reserved0, reserved1, rows, compressed_length = struct.unpack_from("<4I", data, cursor + 4)
        cursor += 20
        if rows == 0:
            raise BOMError(f"CBCK chunk {index} has zero rows")
        if compressed_length == 0 or compressed_length > len(data) - cursor:
            raise BOMError(f"CBCK chunk {index} compressed stream is truncated")
        chunks.append(CBCKChunk(reserved0, reserved1, rows, data[cursor:cursor + compressed_length]))
        cursor += compressed_length
    if cursor != len(data):
        raise BOMError(f"CBCK payload has {len(data) - cursor} trailing bytes")
    return CBCKPayload(mode, codec, tuple(chunks))
