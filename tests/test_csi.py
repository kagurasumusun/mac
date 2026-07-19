import struct
import unittest

from actool_linux.bom import BOMError
from actool_linux.csi import parse_csi


def make_csi() -> bytes:
    data = bytearray(184)
    data[:4] = b"ISTC"
    struct.pack_into("<5I", data, 4, 1, 0x18, 20, 10, 200)
    data[24:28] = b" GRA"  # little-endian spelling of ARG<space>
    struct.pack_into("<I", data, 28, 2)
    struct.pack_into("<I2H", data, 32, 123, 12, 0)
    data[40:48] = b"icon.png"
    tlv = struct.pack("<2I4s", 0x3EE, 4, b"\x01\0\0\0")
    payload = b"PAYLOAD"
    struct.pack_into("<4I", data, 168, len(tlv), 0, 0, len(payload))
    return bytes(data) + tlv + payload


class CSITests(unittest.TestCase):
    def test_parses_header_tlv_and_payload(self):
        csi = parse_csi(make_csi())
        self.assertEqual((csi.width, csi.height, csi.scale), (20, 10, 2.0))
        self.assertEqual((csi.pixel_format, csi.layout, csi.name), ("ARG ", 12, "icon.png"))
        self.assertEqual(csi.tlvs[0].tag, 0x3EE)
        self.assertEqual(csi.rendition_data, b"PAYLOAD")

    def test_rejects_payload_overrun(self):
        data = bytearray(make_csi())
        struct.pack_into("<I", data, 180, 999999)
        with self.assertRaises(BOMError):
            parse_csi(data)


if __name__ == "__main__":
    unittest.main()
