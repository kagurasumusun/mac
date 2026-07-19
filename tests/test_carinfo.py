import base64
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

HAS_LZFSE = importlib.util.find_spec("lzfse") is not None

from actool_linux.carinfo import inspect
from actool_linux.atlas import build_packed_atlas_car
from actool_linux.carwriter import build_palette_img_car

P2=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAQAAADYv8WvAAAAEklEQVR4nGPg/m/wiCH0aNUKABRABFncH0e8AAAAAElFTkSuQmCC")


def chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload) & 0xffffffff)


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


def rgba_png(width: int, height: int, transparent_last_col: bool = False) -> bytes:
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            alpha = 0 if transparent_last_col and x == width - 1 else 255
            rows += bytes((255, 255, 255, alpha))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(bytes(rows), 9)) + chunk(b'IEND', b'')


class CarInfoTests(unittest.TestCase):
    def test_decodes_explicit_atlas_tlvs(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'atlas.car'
            path.write_bytes(build_packed_atlas_car({'bokeh': rgba_png(64, 64), 'spark': rgba_png(64, 64, transparent_last_col=True)}, style='explicit', atlas_name='Particle Sprite Atlas'))
            info = inspect(path)
            linked = [r for r in info['renditions'] if r['layout'] == 1003]
            self.assertEqual(len(linked), 2)
            self.assertTrue(all(any(t['tag'] == 1010 and 'atlas_link' in t for t in r['tlvs']) for r in linked))
            self.assertTrue(any(any(t['tag'] == 1011 and 'atlas_trim' in t for t in r['tlvs']) for r in linked))
            meta = [r for r in info['renditions'] if r['layout'] == 1005][0]
            self.assertTrue(any(t['tag'] == 1013 and 'atlas_name_list' in t for t in meta['tlvs']))

    @unittest.skipUnless(HAS_LZFSE, 'optional lzfse dependency is unavailable')
    def test_decodes_paletteimg_payload(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'palette.car'
            path.write_bytes(build_palette_img_car('Palette', indexed_png(), 'palette.png'))
            info = inspect(path)
            rendition = info['renditions'][0]
            self.assertEqual(rendition['decoded_payload']['compression_type'], 8)
            self.assertEqual(rendition['decoded_payload']['quantized']['palette_count'], 4)


if __name__ == '__main__':
    unittest.main()
