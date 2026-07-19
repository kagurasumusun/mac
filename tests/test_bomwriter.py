import unittest

from actool_linux.bom import BOMStore
from actool_linux.bomwriter import BOMWriter


class BOMWriterTests(unittest.TestCase):
    def test_round_trip_named_blocks(self):
        writer = BOMWriter()
        first = writer.add_block(b"header", "HEADER")
        second = writer.add_block(b"payload", "PAYLOAD")
        data = writer.build()
        parsed = BOMStore(data)
        self.assertEqual((first, second), (1, 2))
        self.assertEqual(bytes(parsed.named_block("HEADER")), b"header")
        self.assertEqual(bytes(parsed.named_block("PAYLOAD")), b"payload")
        self.assertEqual(parsed.header.block_count_hint, 2)

    def test_is_deterministic(self):
        def make():
            writer = BOMWriter()
            writer.add_block(b"same", "A")
            return writer.build()
        self.assertEqual(make(), make())


if __name__ == "__main__":
    unittest.main()
