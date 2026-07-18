from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct


class BOMError(ValueError):
    """Raised when a BOMStore container is malformed or unsupported."""


@dataclass(frozen=True)
class BOMHeader:
    version: int
    block_count_hint: int
    index_offset: int
    index_length: int
    variables_offset: int
    variables_length: int


@dataclass(frozen=True)
class Block:
    identifier: int
    offset: int
    length: int


class BOMStore:
    """Bounds-checked reader for the BOMStore container used by Assets.car.

    BOM scalar metadata is big-endian. The payload of a named block may use a
    different byte order and is intentionally left uninterpreted by this layer.
    """

    MAGIC = b"BOMStore"
    HEADER = struct.Struct(">8s6I")

    # Known CoreUI database names
    DATABASE_NAMES = frozenset({
        'imagedb', 'colordb', 'fontdb', 'fontsizedb',
        'appearancedb', 'facetKeysdb', 'bitmapKeydb',
        'zcbezeldb', 'zcglyphdb'
    })

    def __init__(self, data: bytes | bytearray | memoryview):
        self._data = memoryview(data).cast("B")
        self.header = self._read_header()
        self.blocks = self._read_block_index()
        self.variables = self._read_variables()

    @classmethod
    def from_path(cls, path: Path | str) -> "BOMStore":
        return cls(Path(path).read_bytes())

    def _range(self, offset: int, length: int, label: str) -> memoryview:
        if offset < 0 or length < 0 or offset > len(self._data) or length > len(self._data) - offset:
            raise BOMError(f"{label} range is outside the file: offset={offset}, length={length}")
        return self._data[offset:offset + length]

    def _read_header(self) -> BOMHeader:
        if len(self._data) < self.HEADER.size:
            raise BOMError("file is shorter than the 32-byte BOM header")
        magic, version, count, index_off, index_len, vars_off, vars_len = self.HEADER.unpack_from(self._data)
        if magic != self.MAGIC:
            raise BOMError(f"invalid BOM magic: {bytes(magic)!r}")
        if version != 1:
            raise BOMError(f"unsupported BOMStore version: {version}")
        self._range(index_off, index_len, "block index")
        self._range(vars_off, vars_len, "variables")
        return BOMHeader(version, count, index_off, index_len, vars_off, vars_len)

    def _read_block_index(self) -> dict[int, Block]:
        raw = self._range(self.header.index_offset, self.header.index_length, "block index")
        if len(raw) < 4:
            raise BOMError("block index is truncated")
        capacity = struct.unpack_from(">I", raw, 0)[0]
        # Index layout starts with a capacity word, followed by `capacity`
        # (offset,length) pairs. Identifier zero is the null block. A free-list
        # trailer may follow the allocated pair array.
        required = 4 + capacity * 8
        if capacity > 1_000_000 or required > len(raw):
            raise BOMError(f"invalid block index capacity: {capacity}")
        result: dict[int, Block] = {}
        for identifier in range(1, capacity):
            offset, length = struct.unpack_from(">II", raw, 4 + identifier * 8)
            if offset == 0 and length == 0:
                continue
            self._range(offset, length, f"block {identifier}")
            result[identifier] = Block(identifier, offset, length)
        return result

    def _read_variables(self) -> dict[str, int]:
        raw = self._range(self.header.variables_offset, self.header.variables_length, "variables")
        if len(raw) < 4:
            raise BOMError("variables table is truncated")
        count = struct.unpack_from(">I", raw, 0)[0]
        cursor = 4
        result: dict[str, int] = {}
        if count > 100_000:
            raise BOMError(f"unreasonable variable count: {count}")
        for _ in range(count):
            if cursor + 5 > len(raw):
                raise BOMError("variables table entry is truncated")
            identifier = struct.unpack_from(">I", raw, cursor)[0]
            name_length = raw[cursor + 4]
            cursor += 5
            if cursor + name_length > len(raw):
                raise BOMError("variable name is truncated")
            name_bytes = bytes(raw[cursor:cursor + name_length])
            cursor += name_length
            try:
                name = name_bytes.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise BOMError("variable name is not UTF-8") from exc
            if identifier not in self.blocks:
                raise BOMError(f"variable {name!r} references missing block {identifier}")
            if name in result:
                raise BOMError(f"duplicate variable name: {name!r}")
            result[name] = identifier
        return result

    def block(self, identifier: int) -> memoryview:
        try:
            item = self.blocks[identifier]
        except KeyError as exc:
            raise BOMError(f"unknown block identifier: {identifier}") from exc
        return self._range(item.offset, item.length, f"block {identifier}")

    def named_block(self, name: str) -> memoryview:
        try:
            identifier = self.variables[name]
        except KeyError as exc:
            raise BOMError(f"unknown named block: {name}") from exc
        return self.block(identifier)

    def get_databases(self) -> dict[str, int]:
        """Return a mapping of known CoreUI database names to their block identifiers.

        CoreUI uses multiple specialized databases for different types of assets.
        This method identifies which databases are present in this BOMStore.
        """
        return {
            name: identifier
            for name, identifier in self.variables.items()
            if name in self.DATABASE_NAMES
        }

    def has_database(self, name: str) -> bool:
        """Check if a specific CoreUI database is present."""
        return name in self.variables and name in self.DATABASE_NAMES
