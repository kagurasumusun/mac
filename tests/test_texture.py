import unittest

from actool_linux.texture import parse_texture_auxiliary_flag, parse_texture_reference_payload

REFERENCE_HEX = '5254585400000000370000000100000001000000010001001c00000000000000010029000200b500080001000c000200110076c40f00080000000000'
AUX_HEX = '000000000000000001000000'


class TextureParsingTests(unittest.TestCase):
    def test_parses_texture_reference_payload(self):
        parsed = parse_texture_reference_payload(bytes.fromhex(REFERENCE_HEX))
        self.assertEqual(parsed.payload_value, 55)
        self.assertEqual(parsed.key_pairs, ((1,41),(2,181),(8,1),(12,2),(17,50294),(15,8),(0,0)))

    def test_parses_texture_auxiliary_flag(self):
        parsed = parse_texture_auxiliary_flag(bytes.fromhex(AUX_HEX))
        self.assertEqual(parsed.values, (0,0,1))


if __name__ == '__main__':
    unittest.main()
