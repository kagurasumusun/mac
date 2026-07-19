import struct
import unittest

from actool_linux.bom import BOMError, BOMStore


def synthetic_bom() -> bytes:
    payload = b"test-payload"
    block_offset = 0x40
    variables_offset = block_offset + len(payload)
    variables = struct.pack(">II", 1, 1) + bytes([4]) + b"TEST"
    index_offset = variables_offset + len(variables)
    capacity = 2
    index = struct.pack(">I", capacity)
    index += struct.pack(">II", 0, 0)
    index += struct.pack(">II", block_offset, len(payload))
    header = struct.pack(">8s6I", b"BOMStore", 1, 1, index_offset, len(index), variables_offset, len(variables))
    return header.ljust(block_offset, b"\0") + payload + variables + index


class BOMTests(unittest.TestCase):
    def test_reads_named_block(self):
        store = BOMStore(synthetic_bom())
        self.assertEqual(store.variables, {"TEST": 1})
        self.assertEqual(bytes(store.named_block("TEST")), b"test-payload")

    def test_rejects_truncated_index(self):
        data = bytearray(synthetic_bom())
        struct.pack_into(">I", data, 20, 4)
        with self.assertRaises(BOMError):
            BOMStore(data)

    def test_rejects_out_of_range_block(self):
        data = bytearray(synthetic_bom())
        index_offset = struct.unpack_from(">I", data, 16)[0]
        struct.pack_into(">II", data, index_offset + 12, len(data) + 1, 10)
        with self.assertRaises(BOMError):
            BOMStore(data)


if __name__ == "__main__":
    unittest.main()
