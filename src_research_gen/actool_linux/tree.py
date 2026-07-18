from __future__ import annotations

from dataclasses import dataclass
import struct

from .bom import BOMError, BOMStore


@dataclass(frozen=True)
class TreeDescriptor:
    version: int
    root_block: int
    node_size: int
    path_count: int


@dataclass(frozen=True)
class TreeEntry:
    key_block: int
    value_block: int
    key: bytes
    value: bytes


def parse_descriptor(raw: bytes | memoryview) -> TreeDescriptor:
    data = bytes(raw)
    if len(data) < 20:
        raise BOMError("tree descriptor is truncated")
    magic, version, root, node_size, path_count = struct.unpack_from(">4s4I", data)
    if magic != b"tree":
        raise BOMError(f"invalid tree descriptor magic: {magic!r}")
    if version != 1:
        raise BOMError(f"unsupported BOM tree version: {version}")
    if node_size == 0 or node_size > 16 * 1024 * 1024:
        raise BOMError(f"invalid BOM tree node size: {node_size}")
    if path_count > 10_000_000:
        raise BOMError(f"invalid BOM tree path count: {path_count}")
    return TreeDescriptor(version, root, node_size, path_count)


def read_leaf_entries(store: BOMStore, name: str) -> list[TreeEntry]:
    """Traverse a bounds-checked BOM B+ tree and return its leaf records.

    Node reference pairs are ``(value block, key block)``. In leaves they are
    the user value/key blocks. In internal nodes the value reference is a child
    node and the key reference is its separator key. Apple-generated internal
    nodes list children in traversal order; leaf forward/backward links are not
    needed for a root-based walk.
    """
    descriptor = parse_descriptor(store.named_block(name))
    result: list[TreeEntry] = []
    active: set[int] = set()
    visited: set[int] = set()

    def visit(block_id: int, depth: int) -> None:
        if depth > 64:
            raise BOMError(f"tree {name!r} exceeds the maximum depth")
        if block_id in active:
            raise BOMError(f"tree {name!r} contains a node cycle at block {block_id}")
        if block_id in visited:
            raise BOMError(f"tree {name!r} references node {block_id} more than once")
        try:
            node = bytes(store.block(block_id))
        except (KeyError, IndexError, ValueError) as exc:
            raise BOMError(f"tree {name!r} references missing node {block_id}") from exc
        if len(node) < 12:
            raise BOMError(f"tree {name!r} node {block_id} is truncated")
        is_leaf, count, _forward, _backward = struct.unpack_from(">HHII", node)
        if is_leaf not in (0, 1):
            raise BOMError(f"tree {name!r} node {block_id} has invalid type {is_leaf}")
        if count > 1_000_000 or 12 + count * 8 > len(node):
            raise BOMError(f"tree {name!r} node {block_id} has invalid entry count {count}")
        active.add(block_id)
        visited.add(block_id)
        references = [struct.unpack_from(">II", node, 12 + index * 8) for index in range(count)]
        if is_leaf:
            for value_id, key_id in references:
                if len(result) >= descriptor.path_count + 1:
                    raise BOMError(f"tree {name!r} contains more leaves than its path count")
                try:
                    key = bytes(store.block(key_id))
                    value = bytes(store.block(value_id))
                except (KeyError, IndexError, ValueError) as exc:
                    raise BOMError(f"tree {name!r} leaf references a missing key/value block") from exc
                result.append(TreeEntry(key_id, value_id, key, value))
        else:
            # An internal node has N (child, separator-key) pairs followed by
            # one final child u32. Thus N separators partition N+1 children.
            # This was confirmed against Xcode's 5,000-rendition CAR fixture.
            final_child_offset = 12 + count * 8
            if final_child_offset + 4 > len(node):
                raise BOMError(f"tree {name!r} internal node {block_id} lacks its final child")
            for child_id, separator_id in references:
                # Resolve the separator too, so malformed references are not
                # silently accepted even though a full scan need not compare it.
                try:
                    bytes(store.block(separator_id))
                except (KeyError, IndexError, ValueError) as exc:
                    raise BOMError(f"tree {name!r} references missing separator {separator_id}") from exc
                visit(child_id, depth + 1)
            final_child = struct.unpack_from(">I", node, final_child_offset)[0]
            if final_child == 0:
                raise BOMError(f"tree {name!r} internal node {block_id} has a null final child")
            visit(final_child, depth + 1)
        active.remove(block_id)

    visit(descriptor.root_block, 0)
    if descriptor.path_count != len(result):
        raise BOMError(
            f"tree {name!r} path count mismatch: descriptor={descriptor.path_count}, leaves={len(result)}"
        )
    return result
