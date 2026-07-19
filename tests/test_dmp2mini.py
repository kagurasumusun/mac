import struct
import unittest

from actool_linux import dmp2mini
from actool_linux.carwriter import _csi_png_deepmap

BGRA_A = bytes((0x11, 0x08, 0x5A, 0xFF))   # RGBA (0x5a,0x08,0x11,0xff) premultiplied
GA_OPAQUE = bytes((0x4D, 0xFF))
GA_TRANSLUCENT = bytes((0x27, 0x80))


def png_rgba(w, h, px):
    import zlib
    raw = b''.join(b'\x00' + bytes(px) * w for _ in range(h))
    def chunk(t, d):
        c = t + d
        return struct.pack('>I', len(d)) + c + struct.pack('>I', zlib.crc32(c))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def png_ga(w, h, ga):
    import zlib
    raw = b''.join(b'\x00' + bytes(ga) * w for _ in range(h))
    def chunk(t, d):
        c = t + d
        return struct.pack('>I', len(d)) + c + struct.pack('>I', zlib.crc32(c))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 4, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def dmp2_of(csi: bytes) -> bytes:
    tlv_len = struct.unpack_from('<I', csi, 168)[0]
    payload = csi[184 + tlv_len:]
    dlen = struct.unpack_from('<I', payload, 24)[0]
    return payload[32:32 + dlen]


def body_of(dmp2: bytes) -> bytes:
    return dmp2[16:]


class OracleByteEquality(unittest.TestCase):
    """Emitters must reproduce the Apple dmp2 bytes observed in oracles
    (probe suite hp9; hex fixtures captured from Apple actool output)."""

    def test_v1_color_2x2(self):
        d = dmp2mini.v1_raw(2, 2, BGRA_A * 4, 4)
        self.assertEqual(d[4], 1)
        self.assertEqual(d[12:], BGRA_A * 4)

    def test_v3_mini_color_8x8(self):
        d = dmp2mini.v3_mini_color(8, 8, BGRA_A)
        self.assertEqual(body_of(d).hex(), 'e411085aff3804f0dfe3085aff0600000000000000')

    def test_v3_mini_color_3x3(self):
        d = dmp2mini.v3_mini_color(3, 3, BGRA_A)
        self.assertEqual(body_of(d).hex(), 'e411085aff3804f003e3085aff0600000000000000')

    def test_v3_mini_color_16x8_two_tokens(self):
        d = dmp2mini.v3_mini_color(16, 8, BGRA_A)
        self.assertEqual(body_of(d).hex(), 'e411085aff3804f0fff0d0e3085aff0600000000000000')

    def test_v3_mini_ga_8x8(self):
        d = dmp2mini.v3_mini_ga(8, 8, GA_OPAQUE)
        self.assertEqual(body_of(d).hex(), '98024dfff067e1ff0600000000000000')

    def test_v3_mini_ga_40x40_deep_continuation(self):
        # 3200 source bytes probe: 11 full tokens + tail token (f0 c2).
        d = dmp2mini.v3_mini_ga(40, 40, GA_OPAQUE)
        expect = ('98024dff' + 'f0ff' * 11 + 'f0c2' + 'e1ff' + '0600000000000000')
        self.assertEqual(body_of(d).hex(), expect)

    def test_v3_mini_ga_translucent(self):
        d = dmp2mini.v3_mini_ga(8, 8, GA_TRANSLUCENT)
        self.assertEqual(body_of(d).hex(), '98022780f067e1800600000000000000')

    def test_v4_mini_16x16(self):
        d = dmp2mini.v4_mini(16, 16, BGRA_A)
        self.assertEqual(body_of(d).hex(), '11085aff10000000680100f0e5e200000600000000000000')

    def test_v4_mini_17x15_odd(self):
        d = dmp2mini.v4_mini(17, 15, BGRA_A)
        self.assertEqual(body_of(d).hex(), '11085aff0f000000680100f0e5e1000600000000000000')

    def test_v4_mini_20x20(self):
        d = dmp2mini.v4_mini(20, 20, BGRA_A)
        self.assertEqual(body_of(d).hex(), '11085aff12000000680100f0fff066e200000600000000000000')

    # --- probe5 uniform-size sweep oracles (p5a_s_u*, Apple actool output).
    # The u-series color encodes the height: BGRA (0x5a, H, 0x11, 0xff).

    def test_v4_mini_u17_odd_bare_token(self):
        # 289 px: f0 ff (282) + bare f6 (+7) + e3 end (npix % 4 == 1).
        d = dmp2mini.v4_mini(17, 17, bytes((0x5A, 0x11, 0x11, 0xFF)))
        self.assertEqual(body_of(d).hex(),
                         '5a1111ff12000000680100f0fff6e30000000600000000000000')

    def test_v4_mini_u24(self):
        d = dmp2mini.v4_mini(24, 24, bytes((0x5A, 0x18, 0x11, 0xFF)))
        self.assertEqual(body_of(d).hex(),
                         '5a1811ff14000000680100f0fff0fff007e200000600000000000000')

    def test_v4_mini_u28(self):
        d = dmp2mini.v4_mini(28, 28, bytes((0x5A, 0x1C, 0x11, 0xFF)))
        self.assertEqual(body_of(d).hex(),
                         '5a1c11ff14000000680100f0fff0fff0d7e200000600000000000000')

    def test_v4_mini_u32(self):
        d = dmp2mini.v4_mini(32, 32, bytes((0x5A, 0x20, 0x11, 0xFF)))
        self.assertEqual(body_of(d).hex(),
                         '5a2011ff16000000680100f0fff0fff0fff0b8e200000600000000000000')

    def test_v4_mini_u48_largest_probed(self):
        d = dmp2mini.v4_mini(48, 48, bytes((0x5A, 0x30, 0x11, 0xFF)))
        self.assertEqual(body_of(d).hex(),
                         '5a3011ff20000000680100'
                         + 'f0ff' * 8 + 'f06d'
                         + 'e200000600000000000000')

    def test_v4_mini_u12_smallest_probed(self):
        d = dmp2mini.v4_mini(12, 12, bytes((0x5A, 0x0C, 0x11, 0xFF)))
        self.assertEqual(body_of(d).hex(),
                         '5a0c11ff10000000680100f075e200000600000000000000')


class GrammarSelectionTests(unittest.TestCase):
    """carwriter picks the right grammar per size (Apple probed ranges)."""

    def _version(self, csi: bytes) -> int:
        return dmp2_of(csi)[4]

    def test_uniform_color_sizes(self):
        # <=8 px: v1 raw; 9..128 px: v3-mini; 144..2304 px: v4-mini;
        # above that the v4 LZFSE form (probe5 u12..u48 vs u64 oracles).
        for (w, h), want in [((1, 1), 1), ((2, 2), 1), ((8, 1), 1),
                             ((3, 3), 3), ((4, 4), 3), ((8, 8), 3), ((16, 8), 3),
                             ((12, 12), 4), ((16, 16), 4), ((17, 17), 4),
                             ((20, 20), 4), ((48, 48), 4)]:
            csi = _csi_png_deepmap(png_rgba(w, h, (0x5a, 0x08, 0x11, 0xff)), 's.png')
            self.assertEqual(self._version(csi), want, f'{w}x{h}')
        # u64 oracle: 4096 px leaves the mini family for the LZFSE stream.
        csi = _csi_png_deepmap(png_rgba(64, 64, (0x5a, 0x08, 0x11, 0xff)), 's.png')
        self.assertIn(b'bvx', dmp2_of(csi))

    def test_uniform_ga_sizes(self):
        for (w, h), want in [((2, 2), 1), ((8, 8), 3), ((40, 40), 3)]:
            csi = _csi_png_deepmap(png_ga(w, h, (0x4d, 0xff)), 's.png')
            self.assertEqual(self._version(csi), want, f'{w}x{h}')

    def test_translucent_ga_mini_mode0(self):
        csi = _csi_png_deepmap(png_ga(8, 8, (0x4d, 0x80)), 's.png')
        self.assertEqual(self._version(csi), 3)
        tlv_len = struct.unpack_from('<I', csi, 168)[0]
        payload = csi[184 + tlv_len:]
        mode = struct.unpack_from('<I', payload, 4)[0]
        self.assertEqual(mode, 0)

    def test_mini_roundtrips(self):
        for (w, h) in [(4, 4), (8, 8), (16, 8), (40, 40)]:
            d = dmp2mini.v3_mini_ga(w, h, GA_OPAQUE)
            self.assertEqual(dmp2mini.decode_mini(d, w, h, 2), GA_OPAQUE * (w * h))
        for (w, h) in [(3, 3), (8, 8), (10, 10), (16, 8), (13, 7)]:
            d = dmp2mini.v3_mini_color(w, h, BGRA_A)
            self.assertEqual(dmp2mini.decode_mini(d, w, h, 4), BGRA_A * (w * h))
        for (w, h) in [(12, 12), (16, 16), (17, 15), (20, 20), (17, 17), (48, 48),
                       (1, 283), (7, 79), (2, 145), (2, 277)]:  # incl. odd/rebalanced tails
            d = dmp2mini.v4_mini(w, h, BGRA_A)
            self.assertEqual(dmp2mini.decode_mini(d, w, h, 4), BGRA_A * (w * h), f'{w}x{h}')


if __name__ == '__main__':
    unittest.main()
