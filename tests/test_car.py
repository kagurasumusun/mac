import struct
import unittest

from actool_linux.bom import BOMError
from actool_linux.car import parse_car_header, parse_key_format


class CARTests(unittest.TestCase):
    def test_little_endian_key_format(self):
        raw = b"tmfk" + struct.pack("<2I3I", 0, 3, 12, 15, 17)
        parsed = parse_key_format(raw)
        self.assertEqual(parsed.attributes, (12, 15, 17))
        self.assertEqual(parsed.names, (
            "kCRThemeScaleName", "kCRThemeIdiomName", "kCRThemeIdentifierName"
        ))

    def test_current_little_endian_header(self):
        raw = bytearray(436)
        raw[:4] = b"RATC"
        struct.pack_into("<4I", raw, 4, 918, 17, 0, 3)
        raw[20:30] = b"CoreUI-918"
        struct.pack_into("<I", raw, 424, 5)
        parsed = parse_car_header(raw)
        self.assertEqual((parsed.core_ui_version, parsed.storage_version), (918, 17))
        self.assertEqual((parsed.rendition_count, parsed.schema_version), (3, 5))

    def test_rejects_invalid_key_count(self):
        with self.assertRaises(BOMError):
            parse_key_format(b"tmfk" + struct.pack("<2I", 0, 9999))


if __name__ == "__main__":
    unittest.main()
