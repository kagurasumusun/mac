import unittest

from actool_linux.iconstack import (
    parse_iconstack_aux_list,
    parse_iconstack_group_style_reference,
    parse_iconstack_root_style_list,
    parse_named_gradient_payload,
)


FIREFOX_ROOT_STYLE_HEX = (
    '05000000000000000000000000000000010000000002000000000000000100000000020000009a99193e'
    '0100000000020000000000003f0100000000020000000000003f0100000000'
)

FIREFOX_ROOT_AUX_HEX = (
    '050000000000000000000000000000000000000000000000000000000100000000000000020000000000003f00000000'
    '010000003333b33e020000000000003f000000000100000000000000020000000000003f00000000'
    '010000003333333f030000000000003f00000000'
)

FILEMERGE_GROUP_STYLE_COLOR_HEX = '010000000000000001000000000000001a00000046696c654d657267655f4173736574732f436f6c6f722d313000'
FILEMERGE_GROUP_STYLE_GRADIENT_HEX = '010000000000000001000000000000001c00000046696c654d657267655f4173736574732f4772616469656e742d3400'
FILEMERGE_GRADIENT_HEX = (
    '415247470200000001000000000000000000003f000000000000003f0000803f00000000'
    '1900000046696c654d657267655f4173736574732f436f6c6f722d32000000803f1900000046696c654d657267655f4173736574732f436f6c6f722d3300'
)


class IconStackParserTests(unittest.TestCase):
    def test_parse_root_style_entries(self):
        parsed = parse_iconstack_root_style_list(bytes.fromhex(FIREFOX_ROOT_STYLE_HEX))
        self.assertEqual(len(parsed.entries), 5)
        self.assertEqual([entry.kind for entry in parsed.entries], [0, 2, 2, 2, 2])
        self.assertAlmostEqual(parsed.entries[0].value, 0.0)
        self.assertAlmostEqual(parsed.entries[2].value, 0.15, places=5)
        self.assertAlmostEqual(parsed.entries[3].value, 0.5, places=5)
        self.assertEqual([entry.enabled for entry in parsed.entries], [1, 1, 1, 1, 1])

    def test_parse_aux_entries(self):
        parsed = parse_iconstack_aux_list(bytes.fromhex(FIREFOX_ROOT_AUX_HEX))
        self.assertEqual(len(parsed.entries), 5)
        self.assertEqual(parsed.entries[0].u32_1, 0)
        self.assertEqual(parsed.entries[1].u32_1, 1)
        self.assertAlmostEqual(parsed.entries[2].f32_1, 0.35, places=5)
        self.assertEqual(parsed.entries[4].u32_2, 3)
        self.assertAlmostEqual(parsed.entries[4].f32_2, 0.5, places=5)

    def test_parse_group_style_reference_color(self):
        parsed = parse_iconstack_group_style_reference(bytes.fromhex(FILEMERGE_GROUP_STYLE_COLOR_HEX))
        self.assertEqual(parsed.count, 1)
        self.assertEqual(parsed.kind, 1)
        self.assertEqual(parsed.name, 'FileMerge_Assets/Color-10')

    def test_parse_group_style_reference_gradient(self):
        parsed = parse_iconstack_group_style_reference(bytes.fromhex(FILEMERGE_GROUP_STYLE_GRADIENT_HEX))
        self.assertEqual(parsed.count, 1)
        self.assertEqual(parsed.kind, 1)
        self.assertEqual(parsed.name, 'FileMerge_Assets/Gradient-4')

    def test_parse_named_gradient_payload(self):
        parsed = parse_named_gradient_payload(bytes.fromhex(FILEMERGE_GRADIENT_HEX))
        self.assertEqual(parsed.signature, 'ARGG')
        self.assertEqual(parsed.stop_count, 2)
        self.assertEqual(parsed.mode, 1)
        self.assertAlmostEqual(parsed.scalar_2, 0.5, places=5)
        self.assertAlmostEqual(parsed.scalar_5, 1.0, places=5)
        self.assertEqual([(stop.position, stop.name) for stop in parsed.stops], [
            (0.0, 'FileMerge_Assets/Color-2'),
            (1.0, 'FileMerge_Assets/Color-3'),
        ])


if __name__ == '__main__':
    unittest.main()
