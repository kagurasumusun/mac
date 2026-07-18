from __future__ import annotations

from dataclasses import dataclass
import struct

from .bom import BOMError


@dataclass(frozen=True)
class PendingBlock:
    identifier: int
    data: bytes


class BOMWriter:
    """Deterministic writer for the generic BOMStore container layer.

    This layer knows nothing about CoreUI payloads. Blocks are allocated in
    insertion order, payloads are 16-byte aligned, and index capacity is a
    power of two. All container metadata is big-endian as required by BOM.
    """

    def __init__(self):
        self._blocks: list[PendingBlock] = []
        self._variables: list[tuple[str, int]] = []

    def add_block(self, data: bytes | bytearray | memoryview, name: str | None = None) -> int:
        raw = bytes(data)
        identifier = len(self._blocks) + 1
        self._blocks.append(PendingBlock(identifier, raw))
        if name is not None:
            if not name or "\0" in name:
                raise BOMError("BOM variable name must be non-empty and contain no NUL")
            encoded = name.encode("utf-8")
            if len(encoded) > 255:
                raise BOMError("BOM variable name exceeds 255 UTF-8 bytes")
            if any(existing == name for existing, _ in self._variables):
                raise BOMError(f"duplicate BOM variable name: {name!r}")
            self._variables.append((name, identifier))
        return identifier

    @staticmethod
    def _align(value: int, alignment: int = 16) -> int:
        return (value + alignment - 1) & ~(alignment - 1)

    def replace_block(self, identifier: int, data: bytes | bytearray | memoryview) -> None:
        """Replace a reserved block without changing its stable identifier."""
        if identifier <= 0 or identifier > len(self._blocks):
            raise BOMError(f"invalid BOM block identifier: {identifier}")
        self._blocks[identifier - 1] = PendingBlock(identifier, bytes(data))

    def build(self) -> bytes:
        import io
        cursor = 0x200
        chunks: list[tuple[int, bytes]] = []
        locations: dict[int, tuple[int, int]] = {}
        for block in self._blocks:
            cursor = self._align(cursor)
            chunks.append((cursor, block.data))
            locations[block.identifier] = (cursor, len(block.data))
            cursor += len(block.data)

        cursor = self._align(cursor)
        variables_offset = cursor
        variables = bytearray(struct.pack(">I", len(self._variables)))
        for name, identifier in self._variables:
            encoded = name.encode("utf-8")
            variables += struct.pack(">IB", identifier, len(encoded)) + encoded
        variables_length = len(variables)
        chunks.append((variables_offset, bytes(variables)))

        cursor = self._align(variables_offset + variables_length)
        index_offset = cursor
        capacity = 1
        while capacity <= len(self._blocks):
            capacity *= 2
        capacity = max(16, capacity)
        index = bytearray(struct.pack(">I", capacity))
        index += struct.pack(">II", 0, 0)
        for identifier in range(1, capacity):
            index += struct.pack(">II", *locations.get(identifier, (0, 0)))
        # Observed BOMStore files carry a five-word free-list trailer.
        index += bytes(20)
        index_length = len(index)
        chunks.append((index_offset, bytes(index)))

        total = index_offset + index_length
        out = io.BytesIO()
        header = struct.pack(
            ">8s6I", b"BOMStore", 1, len(self._blocks),
            index_offset, index_length, variables_offset, variables_length,
        )
        out.write(header)
        for offset, data in chunks:
            out.seek(offset)
            out.write(data)

        # pad to total if needed
        out.seek(total - 1)
        out.write(bytes(1))
        return out.getvalue()
