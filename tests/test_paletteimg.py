import binascii
import importlib.util
from pathlib import Path
import struct
import unittest
import zlib

from actool_linux.bom import BOMStore
from actool_linux.car import CARFile
from actool_linux.carwriter import build_palette_img_car
from actool_linux.paletteimg import (
    decode_quantized_image_payload,
    parse_theme_pixel_rendition,
)

HAS_LZFSE = importlib.util.find_spec("lzfse") is not None


def chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", binascii.crc32(kind + payload) & 0xffffffff)


def indexed_png(size: int = 4) -> bytes:
    palette = bytes.fromhex('ff000000ff000000ffffff00')
    trns = bytes([255, 128, 255, 64])
    rows = []
    for y in range(size):
        idx = [(x + y) % 4 for x in range(size)]
        packed = bytearray()
        for x in range(0, size, 4):
            value = 0
            for j in range(4):
                sample = idx[x + j] if x + j < size else 0
                value |= sample << (6 - 2 * j)
            packed.append(value)
        rows.append(b'\0' + packed)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 2, 3, 0, 0, 0)) + chunk(b'PLTE', palette) + chunk(b'tRNS', trns) + chunk(b'IDAT', zlib.compress(b''.join(rows))) + chunk(b'IEND', b'')


TIMAC_FIXTURE = Path(__file__).resolve().parents[1] / 'public-fixtures' / 'timac-demo-assets.car'


@unittest.skipUnless(HAS_LZFSE, "optional lzfse dependency is unavailable")
class PaletteImgTests(unittest.TestCase):
    @unittest.skipUnless(TIMAC_FIXTURE.exists(), "public Timac palette fixture is unavailable")
    def test_parses_public_timac_palette_fixture(self):
        car = CARFile(BOMStore.from_path(str(TIMAC_FIXTURE)))
        image = next(r for r in car.renditions if r.csi.name == 'Timac.png')
        wrapper = parse_theme_pixel_rendition(image.csi.rendition_data)
        self.assertEqual(wrapper.compression_type, 8)
        decoded = decode_quantized_image_payload(wrapper.raw_data, width=image.csi.width, height=image.csi.height, pixel_format=image.csi.pixel_format)
        self.assertEqual(decoded.version, 1)
        # Public Timac fixture ground truth: 105-color palette, whole-byte
        # indices (discrete widths 1/2/4/8), one index per pixel.
        self.assertEqual(len(decoded.palette), 105)
        self.assertEqual(decoded.bits_per_index, 8)
        self.assertEqual(len(decoded.indices), image.csi.width * image.csi.height)

    def test_builds_palette_img_car(self):
        car = CARFile(BOMStore(build_palette_img_car('Palette', indexed_png(), 'palette.png')))
        rendition = car.renditions[0]
        self.assertEqual((rendition.csi.pixel_format, rendition.csi.layout), ('ARGB', 12))
        wrapper = parse_theme_pixel_rendition(rendition.csi.rendition_data)
        self.assertEqual(wrapper.compression_type, 8)
        decoded = decode_quantized_image_payload(wrapper.raw_data, width=4, height=4, pixel_format='ARGB')
        self.assertEqual(len(decoded.palette), 4)
        self.assertEqual(len(decoded.indices), 16)


if __name__ == '__main__':
    unittest.main()
