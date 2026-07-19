import struct
import unittest

from actool_linux.bom import BOMError
from actool_linux.tree import parse_descriptor, read_leaf_entries


class FakeStore:
    def __init__(self):
        self.blocks = {
            1: struct.pack(">HHII2I", 1, 1, 0, 0, 3, 2),
            2: b"key",
            3: b"value",
        }

    def named_block(self, name):
        return struct.pack(">4s4I", b"tree", 1, 1, 4096, 1) + b"\0" * 9

    def block(self, identifier):
        return memoryview(self.blocks[identifier])


class TreeTests(unittest.TestCase):
    def test_reads_single_leaf(self):
        entries = read_leaf_entries(FakeStore(), "TEST")
        self.assertEqual([(e.key, e.value) for e in entries], [(b"key", b"value")])

    def test_reads_multi_level_tree(self):
        store = FakeStore()
        store.blocks.update({
            10: struct.pack(">HHII3I", 0, 1, 0, 0, 11, 20, 12),
            11: struct.pack(">HHII2I", 1, 1, 12, 0, 31, 30),
            12: struct.pack(">HHII2I", 1, 1, 0, 11, 33, 32),
            20: b"separator-a",
            30: b"a", 31: b"value-a", 32: b"b", 33: b"value-b",
        })
        store.named_block = lambda name: struct.pack(">4s4I", b"tree", 1, 10, 4096, 2)
        entries = read_leaf_entries(store, "TEST")
        self.assertEqual([(e.key, e.value) for e in entries], [(b"a", b"value-a"), (b"b", b"value-b")])

    def test_rejects_internal_cycle(self):
        store = FakeStore()
        store.blocks.update({10: struct.pack(">HHIII", 0, 0, 0, 0, 10)})
        store.named_block = lambda name: struct.pack(">4s4I", b"tree", 1, 10, 4096, 1)
        with self.assertRaisesRegex(BOMError, "cycle"):
            read_leaf_entries(store, "TEST")

    def test_rejects_bad_magic(self):
        with self.assertRaises(BOMError):
            parse_descriptor(b"nope" + b"\0" * 16)


if __name__ == "__main__":
    unittest.main()
