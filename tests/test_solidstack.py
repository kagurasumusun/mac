import unittest

from actool_linux.solidstack import (
    build_solidimagestack_layer_flags,
    build_solidimagestack_layer_list,
    build_solidimagestack_layer_reserved,
    parse_solidimagestack_layer_flags,
    parse_solidimagestack_layer_list,
    parse_solidimagestack_layer_reserved,
)

LAYER_LIST_HEX = (
    '0300000000000000'
    '0000000000000000000000000001000000010000000000000000803f10000000010055000200b500110076c400000000'
    '0000000000000000000000000001000000010000000000000000803f10000000010055000200b50011008b4800000000'
    '0000000000000000000000000001000000010000000000000000803f10000000010055000200b5001100aafc00000000'
)
FLAGS_HEX = (
    '0300000000000000'
    '00000000000000000100000000'
    '00000000000000000100000000'
    '00000000000000000100000000'
)
RESERVED_HEX = '0300000000000000' + ('00' * 60)


class SolidStackParsingTests(unittest.TestCase):
    def test_parses_layer_list(self):
        parsed = parse_solidimagestack_layer_list(bytes.fromhex(LAYER_LIST_HEX))
        self.assertEqual(len(parsed.layers), 3)
        self.assertEqual(parsed.layers[0].width, 256)
        self.assertEqual(parsed.layers[0].height, 256)
        self.assertEqual(parsed.layers[0].opacity, 1.0)
        self.assertEqual(parsed.layers[0].referenced_key.attribute_value_pairs, ((1,85),(2,181),(17,50294),(0,0)))
        self.assertEqual(parsed.layers[2].referenced_key.attribute_value_pairs[2], (17,64682))

    def test_parses_flags(self):
        parsed = parse_solidimagestack_layer_flags(bytes.fromhex(FLAGS_HEX))
        self.assertEqual(len(parsed.flags), 3)
        self.assertTrue(all(flag.enabled == 1 for flag in parsed.flags))

    def test_parses_reserved(self):
        parsed = parse_solidimagestack_layer_reserved(bytes.fromhex(RESERVED_HEX))
        self.assertEqual(len(parsed.entries), 3)
        self.assertTrue(all(entry.raw == b'\0'*20 for entry in parsed.entries))

    def test_roundtrip_serializers(self):
        layers = parse_solidimagestack_layer_list(bytes.fromhex(LAYER_LIST_HEX))
        self.assertEqual(build_solidimagestack_layer_list(list(layers.layers)), bytes.fromhex(LAYER_LIST_HEX))
        flags = parse_solidimagestack_layer_flags(bytes.fromhex(FLAGS_HEX))
        self.assertEqual(build_solidimagestack_layer_flags(list(flags.flags)), bytes.fromhex(FLAGS_HEX))
        reserved = parse_solidimagestack_layer_reserved(bytes.fromhex(RESERVED_HEX))
        self.assertEqual(build_solidimagestack_layer_reserved(list(reserved.entries)), bytes.fromhex(RESERVED_HEX))


if __name__ == '__main__':
    unittest.main()
