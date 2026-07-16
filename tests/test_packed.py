"""Tests for the CoreUI packed-asset (ZZZZPackedAsset / LINK) writer."""
import base64
import binascii
import struct
import unittest
import zlib
from pathlib import Path

from actool_linux.bom import BOMStore
from actool_linux.car import CARFile
from actool_linux.carwriter import build_assets_car, png_rendition
from actool_linux import lzfse_compat
from actool_linux.packed import pack_renditions, is_pack_candidate, _shelf_pack


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", binascii.crc32(kind + payload) & 0xFFFFFFFF)


def _png_rgba(w: int, h: int, rgba) -> bytes:
    raw = (b"\x00" + bytes(rgba) * w) * h
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + _chunk(b"IDAT", zlib.compress(raw, 9)) + _chunk(b"IEND", b""))


def _png_gray(w: int, h: int, v: int) -> bytes:
    raw = (b"\x00" + bytes((v,)) * w) * h
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
            + _chunk(b"IDAT", zlib.compress(raw, 9)) + _chunk(b"IEND", b""))


def _write_car(tmp, rends):
    from pathlib import Path
    p = Path(tmp) / "Assets.car"
    p.write_bytes(build_assets_car(rends, platform="iphoneos", target="15.0"))
    return CARFile(BOMStore.from_path(p))


class PackedAssetTests(unittest.TestCase):
    def _candidates(self):
        return [
            png_rendition("Multi", _png_rgba(16, 16, (30, 100, 200, 255)), "img1x.png", scale=1),
            png_rendition("Multi", _png_rgba(32, 32, (30, 100, 200, 255)), "img2x.png", scale=2),
            png_rendition("Variant", _png_rgba(8, 8, (1, 2, 3, 255)), "any.png", scale=1),
            png_rendition("Variant", _png_rgba(8, 8, (4, 5, 6, 255)), "dark.png", scale=1, appearance=1),
        ]

    def test_candidate_predicate(self):
        rends = self._candidates()
        flags = [is_pack_candidate(r) for r in rends]
        self.assertEqual(flags, [True, False, True, True])  # 2x scale excluded

    def test_atlas_and_links_roundtrip(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            car = _write_car(tmp, self._candidates())
        layouts = {r.csi.layout for r in car.renditions}
        self.assertIn(1004, layouts)
        self.assertIn(1003, layouts)
        atlas = next(r for r in car.renditions if r.csi.layout == 1004)
        # atlas key: identifier 0, element 9, part 181, scale 1, appearance 0
        self.assertEqual((atlas.key["kCRThemeIdentifierName"], atlas.key["kCRThemeElementName"],
                          atlas.key["kCRThemePartName"], atlas.key["kCRThemeScaleName"],
                          atlas.key["kCRThemeAppearanceName"]), (0, 9, 181, 1, 0))
        self.assertEqual(atlas.csi.name, "ZZZZPackedAsset-1.1.0-gamut0")
        self.assertEqual(atlas.csi.pixel_format, "ARGB")
        self.assertEqual((atlas.csi.flags, [t.tag for t in atlas.csi.tlvs]), (0, [1001, 1004, 1006, 1007]))
        # no facet record for the atlas
        self.assertNotIn("ZZZZPackedAsset-1.1.0-gamut0", [f.name for f in car.facets])
        # decode atlas v4 palette and confirm swatch 0 is transparent
        pl = atlas.csi.rendition_data
        self.assertEqual(pl[:4], b"MLEC")
        mode, codec, _flen, _f1, bpp, dlen, _z = struct.unpack_from("<7I", pl, 4)
        self.assertEqual((mode, codec, bpp), (2, 11, 4))
        dmp2 = pl[32:32 + dlen]
        self.assertEqual(dmp2[4], 4)  # palette grammar
        n, _ = struct.unpack_from("<HH", dmp2, 12)
        pal = dmp2[16:16 + 4 * n]
        self.assertEqual(tuple(pal[:4]), (0, 0, 0, 0))
        self.assertIn((200, 100, 30, 255), [tuple(pal[4 * i:4 * i + 4]) for i in range(n)])
        # LINK renditions: both 1x facets link into the atlas
        links = {}
        for r in car.renditions:
            if r.csi.layout != 1003:
                continue
            t = next(t for t in r.csi.tlvs if t.tag == 1010)
            _m, _r, x, y, w, h = struct.unpack_from("<4s5I", t.value, 0)
            links[r.csi.name] = (x, y, w, h)
            self.assertEqual(t.value[:4], bytes.fromhex("4b4c4e49"))
            self.assertEqual((r.csi.flags, len(r.csi.rendition_data or b"")), (16, 0))
            self.assertEqual([tt.tag for tt in r.csi.tlvs], [1001, 1003, 1010, 1004, 1006])
        self.assertEqual(set(links), {"img1x.png", "any.png"})
        self.assertEqual(links["img1x.png"][2:], (16, 16))
        self.assertEqual(links["any.png"][2:], (8, 8))
        # every LINK rect fits inside the atlas and regions do not overlap
        aw, ah = atlas.csi.width, atlas.csi.height
        boxes = list(links.values())
        for x, y, w, h in boxes:
            self.assertTrue(0 <= x and 0 <= y and x + w <= aw and y + h <= ah)
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                self.assertFalse(a[0] < b[0] + b[2] and b[0] < a[0] + a[2]
                                 and a[1] < b[1] + b[3] and b[1] < a[1] + a[3])
        # decode the atlas plane and verify pixel colors at LINK rects
        (slen,) = struct.unpack_from("<I", dmp2, 16 + 4 * n)
        plane = lzfse_compat.decompress(dmp2[20 + 4 * n:20 + 4 * n + slen])
        x, y, w, h = links["img1x.png"]
        idx = plane[(y + 1) * aw + x + 1]
        self.assertEqual(tuple(pal[4 * idx:4 * idx + 4]), (200, 100, 30, 255))
        x, y, w, h = links["any.png"]
        idx = plane[(y + 1) * aw + x + 1]
        self.assertEqual(tuple(pal[4 * idx:4 * idx + 4]), (3, 2, 1, 255))

    def test_single_candidate_appearance_is_not_packed(self):
        import tempfile
        rends = [
            png_rendition("A", _png_rgba(32, 32, (1, 100, 200, 255)), "any.png", scale=1),
            png_rendition("A", _png_rgba(32, 32, (2, 100, 200, 255)), "dark.png", scale=1, appearance=1),
            png_rendition("B", _png_rgba(8, 8, (9, 8, 7, 255)), "b.png", scale=1),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            car = _write_car(tmp, rends)
        # appearance 0 has two candidates -> packed; appearance 1 has one -> stays layout 12
        app1 = next(r for r in car.renditions if r.key["kCRThemeAppearanceName"] == 1)
        self.assertEqual(app1.csi.layout, 12)
        layouts = [r.csi.layout for r in car.renditions]
        self.assertEqual(layouts.count(1004), 1)
        self.assertEqual(layouts.count(1003), 2)

    def test_grayscale_packs_into_gray_atlas(self):
        # probe4 established: grayscale sources pack into GA8 atlases named
        # ZZZZPackedAsset-1.{opaque}.1-gamut0 (GA is NOT exempt).
        import tempfile
        rends = [
            png_rendition("G", _png_gray(8, 8, 90), "any.png", scale=1),
            png_rendition("G", _png_gray(8, 8, 200), "dark.png", scale=1, appearance=1),
            png_rendition("H", _png_gray(8, 8, 33), "h.png", scale=1),
            png_rendition("H", _png_gray(8, 8, 44), "hd.png", scale=1, appearance=1),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            car = _write_car(tmp, rends)
        layouts = [r.csi.layout for r in car.renditions]
        self.assertEqual(layouts.count(1004), 2)   # one atlas per appearance
        self.assertEqual(layouts.count(1003), 4)   # every 1x rendition links
        atlases = [r for r in car.renditions if r.csi.layout == 1004]
        self.assertEqual({r.csi.name for r in atlases}, {"ZZZZPackedAsset-1.1.1-gamut0"})
        self.assertTrue(all(r.csi.pixel_format == "GA8 " for r in atlases))
        self.assertEqual({r.key["kCRThemeAppearanceName"] for r in atlases}, {0, 1})
        # atlas payload: MLEC mode 2 (opaque class), bpp 2, v2 raw-LZFSE grammar
        for atlas in atlases:
            pl = atlas.csi.rendition_data
            self.assertEqual(pl[:4], b"MLEC")
            mode, codec, _flen, _f1, bpp, dlen, _z = struct.unpack_from("<7I", pl, 4)
            self.assertEqual((mode, codec, bpp), (2, 11, 2))
            dmp2 = pl[32:32 + dlen]
            self.assertEqual((dmp2[:4], dmp2[4]), (b"dmp2", 2))
            # decode the (v, a) plane and confirm LINK rectangles land on it
            aw = atlas.csi.width
            links = {}
            for r in car.renditions:
                if r.csi.layout != 1003:
                    continue
                if r.key["kCRThemeAppearanceName"] != atlas.key["kCRThemeAppearanceName"]:
                    continue
                t = next(t for t in r.csi.tlvs if t.tag == 1010)
                _m, _r, x, y, w, h = struct.unpack_from("<4s5I", t.value, 0)
                links[r.csi.name] = (x, y, w, h)
            (slen,) = struct.unpack_from("<H", dmp2, 12)
            plane = lzfse_compat.decompress(dmp2[16:16 + slen])
            self.assertEqual(len(plane), aw * atlas.csi.height * 2)
            expected = {"any.png": 90, "h.png": 33} if atlas.key["kCRThemeAppearanceName"] == 0 \
                else {"dark.png": 200, "hd.png": 44}
            self.assertEqual(set(links), set(expected))
            for name, v_expected in expected.items():
                x, y, w, h = links[name]
                v, a = plane[2 * ((y + 2) * aw + x + 2): 2 * ((y + 2) * aw + x + 2) + 2]
                self.assertEqual((v, a), (v_expected, 255))

    def test_registry_not_required_for_packing(self):
        # probe4/probe5 established: no APPEARANCEKEYS/LOCALIZATIONKEYS tree is
        # needed; >= 2 same-class candidates always pack (probe5 c02 oracle).
        import tempfile
        rends = [
            png_rendition("A", _png_rgba(16, 16, (1, 2, 3, 255)), "a.png", scale=1),
            png_rendition("B", _png_rgba(16, 16, (4, 5, 6, 255)), "b.png", scale=1),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            car = _write_car(tmp, rends)
        layouts = [r.csi.layout for r in car.renditions]
        self.assertEqual(layouts.count(1004), 1)
        self.assertEqual(layouts.count(1003), 2)

    def test_shelf_pack_deterministic_and_padded(self):
        rects = [(16, 16), (8, 8), (32, 32)]
        positions, w, h = _shelf_pack(rects)
        self.assertEqual(w, 36)
        self.assertEqual(positions[2], (2, 2))  # tallest first
        self.assertEqual(h, 54)                 # second shelf below the 32px row
        # deterministic: same input -> identical layout
        self.assertEqual(_shelf_pack(rects), (positions, w, h))

    def test_pack_renditions_preserves_non_candidates(self):
        ga = png_rendition("G", _png_gray(8, 8, 90), "g.png", scale=1)
        two_x = png_rendition("M", _png_rgba(16, 16, (1, 2, 3, 255)), "m2.png", scale=2)
        out = pack_renditions([ga, two_x])
        self.assertEqual([id(a) for a in out], [id(ga), id(two_x)])


class GrayscaleReencodeTests(unittest.TestCase):
    """probe5 c04 oracle: gray-only RGB(A) sources are stored as GA8."""

    def test_rgb_gray_reencoded_to_ga8(self):
        import tempfile
        rgb = (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 4, 8, 2, 0, 0, 0))
               + _chunk(b"IDAT", zlib.compress((b"\x00" + bytes((128, 128, 128)) * 4) * 4, 9)) + _chunk(b"IEND", b""))
        with tempfile.TemporaryDirectory() as tmp:
            car = _write_car(tmp, [png_rendition("G", rgb, "g.png", scale=1)])
        r = car.renditions[0]
        self.assertEqual(r.csi.pixel_format, "GA8 ")
        pl = r.csi.rendition_data
        mode, codec, _flen, _f1, bpp, _dlen, _z = struct.unpack_from("<7I", pl, 4)
        self.assertEqual((mode, codec, bpp), (2, 11, 2))  # opaque GA, v1 grammar

    def test_translucent_gray_rgba_reencoded_to_ga8(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            car = _write_car(tmp, [png_rendition("T", _png_rgba(4, 4, (9, 9, 9, 128)), "t.png", scale=1)])
        r = car.renditions[0]
        self.assertEqual(r.csi.pixel_format, "GA8 ")
        pl = r.csi.rendition_data
        mode, _codec, _flen, _f1, bpp, dlen, _z = struct.unpack_from("<7I", pl, 4)
        self.assertEqual((mode, bpp), (0, 2))
        dmp2 = pl[32:32 + dlen]
        v, a = struct.unpack_from("<2B", dmp2, 12)
        self.assertEqual((v, a), ((9 * 128 + 127) // 255, 128))  # premultiplied


class MacosDimension1KeyFormatTests(unittest.TestCase):
    """probe4b oracle: macosx inserts attribute 8 into its base KEYFORMAT tuple."""

    def _two_classes(self):
        return [
            png_rendition("O1", _png_rgba(8, 8, (10, 20, 30, 255)), "o1.png", scale=1),
            png_rendition("O2", _png_rgba(8, 8, (40, 50, 60, 255)), "o2.png", scale=1),
            png_rendition("T1", _png_rgba(8, 8, (70, 80, 90, 200)), "t1.png", scale=1),
            png_rendition("T2", _png_rgba(8, 8, (100, 110, 120, 200)), "t2.png", scale=1),
        ]

    def _key_format(self, platform):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "Assets.car"
            p.write_bytes(build_assets_car(self._two_classes(), platform=platform, target="15.0"))
            return CARFile(BOMStore.from_path(p))

    def test_macosx_base_plus_dimension1(self):
        car = self._key_format("macosx")
        self.assertEqual(tuple(car.key_format.attributes), (7, 13, 1, 2, 3, 17, 8, 11, 12))
        # two pages of appearance 0 (opaque + translucent classes)
        pages = sorted(r.key["kCRThemeDimension1Name"] for r in car.renditions if r.csi.layout == 1004)
        self.assertEqual(pages, [0, 1])
        # Class names sort ascending, so the translucent class (1.0.0) is
        # page 0 and the opaque class (1.1.0) is page 1. LINK tails reference
        # nonzero pages with an (8, page) pair; page 0 omits attribute 8.
        def tail_pairs(csi):
            t = next(t for t in csi.tlvs if t.tag == 1010)
            _magic, _r, _x, _y, _w, _h = struct.unpack_from("<4s5I", t.value, 0)
            prefix, length, _zero = struct.unpack_from("<3H", t.value, 24)
            self.assertEqual(prefix, 12)
            return [struct.unpack_from("<2H", t.value, 30 + 4 * i) for i in range(length // 4)]
        by_name = {r.csi.name: tail_pairs(r.csi) for r in car.renditions if r.csi.layout == 1003}
        self.assertIn((8, 1), by_name["o1.png"])
        self.assertIn((8, 1), by_name["o2.png"])
        self.assertNotIn(8, [a for a, _v in by_name["t1.png"]])
        self.assertNotIn(8, [a for a, _v in by_name["t2.png"]])

    def test_ios_stack_tuple(self):
        car = self._key_format("iphoneos")
        self.assertEqual(tuple(car.key_format.attributes), (7, 13, 12, 15, 16, 8, 17, 1, 2))


if __name__ == "__main__":
    unittest.main()


class AtlasPaletteOverflowTests(unittest.TestCase):
    """Regression: >255-color atlases must fall back to v2, not crash."""

    def _rainbow_assets(self, count, *, per_color=4):
        """count images whose combined palette exceeds 255 colors (guaranteed
        unique via a global pixel counter)."""
        assets = []
        serial = 0
        for n in range(count):
            px = []
            for i in range(per_color):
                c = serial
                serial += 1
                px.append((c & 0xFF, (c >> 8) & 0xFF, (c * 7) % 251, 255))
            w = len(px)
            raw = b"\x00" + b"".join(bytes(p) for p in px)
            png = (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack(">IIBBBBB", w, 1, 8, 6, 0, 0, 0))
                   + _chunk(b"IDAT", zlib.compress(raw, 9)) + _chunk(b"IEND", b""))
            assets.append(png_rendition(f"R{n:03d}", png, f"r{n}.png", scale=1,
                                        appearance=0))
        return assets

    def test_many_color_atlas_uses_v2(self):
        from actool_linux.packed import _atlas_dmp2, atlas_name
        # 300 distinct opaque colors -> no v4 representation
        bgra = bytearray()
        for n in range(300):
            bgra += bytes((n & 0xFF, (n * 5 + 3) & 0xFF, (n * 11 + 7) & 0xFF, 255))
        dmp2 = _atlas_dmp2(300, 1, bytes(bgra), gray=False)
        self.assertEqual(dmp2[4], 2)  # raw-BGRA LZFSE grammar, no KeyError

        # and end-to-end through pack_renditions (atlas is layout 1004)
        assets = self._rainbow_assets(96)  # 96*4 = 384 colors per appearance bucket
        packed = pack_renditions(assets)
        atlas = next(a for a in packed if a.name == atlas_name(opaque=True, gray=False))
        tlv_length, _one, _zero, payload_length = struct.unpack_from("<4I", atlas.csi, 168)
        payload = atlas.csi[184 + tlv_length:184 + tlv_length + payload_length]
        self.assertEqual(payload[:4], b"MLEC")
        dlen = struct.unpack_from("<I", payload, 24)[0]
        dmp2 = payload[32:32 + dlen]
        self.assertEqual(dmp2[:4], b"dmp2")
        self.assertEqual(dmp2[4], 2)  # fallback grammar even at atlas scale
        aw, ah = struct.unpack_from("<HH", dmp2, 8)
        stream_length = struct.unpack_from("<H", dmp2, 12)[0]
        raw = lzfse_compat.decompress(dmp2[16:16 + stream_length])
        self.assertEqual(len(raw), aw * ah * 4)

    def test_palette_boundary_255_vs_256(self):
        from actool_linux.packed import _atlas_dmp2
        bgra255 = bytearray()
        for n in range(255):
            bgra255 += bytes((n, (n * 3) & 0xFF, (n * 7) & 0xFF, 255))
        self.assertEqual(_atlas_dmp2(255, 1, bytes(bgra255), gray=False)[4], 4)
        # 256 colors -> one more than swatch space allows (index 0 reserved)
        self.assertEqual(_atlas_dmp2(256, 1, bytes(bgra255) + b"\xfd\xfc\xfb\xff", gray=False)[4], 2)
        # pure (fully transparent) canvas still palettes to a single swatch
        self.assertEqual(_atlas_dmp2(4, 4, bytes(64), gray=False)[4], 4)
