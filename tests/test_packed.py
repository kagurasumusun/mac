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


def _decode_mini_isa_plane(stream: bytes, width: int, height: int) -> bytes:
    """Decode a simple multi-swatch mini ISA stream back to an index plane.
    
    Handles the basic opcodes: f0 (zero runs), e1 (literal), 38 (row-copy).
    """
    plane = bytearray(width * height)
    pos = 0
    
    # Skip section intro
    if stream[pos:pos+3] == b"\x68\x01\x00":
        pos += 3
    
    row = height - 1  # Start from bottom
    col = 0
    
    while pos < len(stream) and row >= 0:
        if pos + 2 > len(stream):
            break
            
        opcode = stream[pos]
        
        if opcode == 0xf0:  # Zero run
            val = stream[pos + 1]
            if col == 0 and row == height - 1:
                # First run: bias 25
                run_len = val + 25
            else:
                # Continuation: bias 16
                run_len = val + 16
            # Fill with zeros
            for _ in range(run_len):
                if row >= 0 and col < width:
                    plane[row * width + col] = 0
                    col += 1
                    if col >= width:
                        col = 0
                        row -= 1
            pos += 2
            
        elif opcode == 0xe1:  # Single literal
            idx = stream[pos + 1]
            if row >= 0 and col < width:
                plane[row * width + col] = idx
                col += 1
                if col >= width:
                    col = 0
                    row -= 1
            pos += 2
            
        elif opcode == 0x38:  # Row copy
            # Copy from 1 row back
            src_row = row + 1
            if src_row < height:
                for c in range(width):
                    plane[row * width + c] = plane[src_row * width + c]
            row -= 1
            pos += 2
            
        elif opcode in (0xe2, 0xe3):  # End markers
            break
        elif opcode == 0x06:  # Tail
            break
        else:
            # Unknown opcode, skip
            pos += 1
    
    return bytes(plane)


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


def _decode_mini_isa_plane(stream: bytes, width: int, height: int) -> bytes:
    """Decode a mini ISA stream back to an index plane (for testing)."""
    plane = bytearray(width * height)
    pos = 3  # Skip section intro (68 01 00)
    
    rows_decoded = []
    current_row = bytearray()
    first_zero_run = True  # Track first zero run for bias
    
    while pos < len(stream) and len(rows_decoded) < height:
        if pos >= len(stream):
            break
        
        opcode = stream[pos]
        
        if opcode == 0xf0:
            # Zero run
            if pos + 1 >= len(stream):
                break
            val = stream[pos + 1]
            # First zero run uses bias 25, others use 16
            if first_zero_run:
                run_len = val + 25
                first_zero_run = False
            else:
                run_len = val + 16
            current_row.extend(b'\x00' * run_len)
            pos += 2
        elif 0xf1 <= opcode <= 0xff:
            # Bare short zero run: X + 2 pixels
            run_len = (opcode & 0x0f) + 2
            current_row.extend(b'\x00' * run_len)
            pos += 1
        elif opcode == 0xe1:
            # Literal pixel
            if pos + 1 >= len(stream):
                break
            idx = stream[pos + 1]
            current_row.append(idx)
            first_zero_run = False  # Non-zero pixel breaks first zero run
            pos += 2
        elif opcode == 0x38:
            # Row copy
            if pos + 1 >= len(stream):
                break
            dist = stream[pos + 1]
            if dist == 1 and rows_decoded:
                # Copy from previous row
                prev_row = rows_decoded[-1]
                current_row.extend(prev_row)
            first_zero_run = False  # Row copy breaks first zero run
            pos += 2
        elif opcode in (0xe2, 0xe3, 0x06):
            # End marker or tail
            break
        else:
            # Unknown opcode, skip
            pos += 1
        
        # Check if row is complete
        if len(current_row) >= width:
            rows_decoded.append(current_row[:width])
            current_row = bytearray()
    
    # Assemble plane (bottom-up to top-down)
    rows_decoded.reverse()
    for y, row in enumerate(rows_decoded):
        plane[y * width:(y + 1) * width] = row
    
    return bytes(plane)


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
        # Packed atlas v4 palette: mini ISA stream (no u32 length prefix)
        stream_offset = 16 + 4 * n
        stream = dmp2[stream_offset:]
        
        # Detect format: mini ISA starts with 0x68, LZFSE starts with 'bvx2'
        if stream[:3] == b'\x68\x01\x00':
            # Mini ISA format - decode it
            plane = _decode_mini_isa_plane(stream, aw, ah)
        else:
            # LZFSE format (fallback)
            plane = lzfse_compat.decompress(stream)
        
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
        # Apple-probed packer: insertion area-desc -> 32px first, candidate
        # widths 36/54/64; (max(W,H), H, W) minimised -> 54x36.  The 8x8
        # rect guillotine-fills the hole below the 16x16 sibling (probe5 c05
        # shows Apple doing exactly this).
        self.assertEqual((w, h), (54, 36))
        self.assertEqual(positions[2], (2, 2))     # 32px rect first at origin
        self.assertEqual(positions[0], (36, 2))    # 16px shares its wide row
        self.assertEqual(positions[1], (36, 20))   # 8px nests in the hole below
        # deterministic: same input -> identical layout
        self.assertEqual(_shelf_pack(rects), (positions, w, h))

    def test_shelf_pack_matches_probed_apple_geometry(self):
        # Every (W, H, placements) below was extracted from Apple actool
        # (Xcode 26.5) output; rects are given in RENDITIONS tree order.
        corpus = [
            ([(2, 2), (2, 2)], 10, 6, [(6, 2), (2, 2)]),
            ([(2, 2), (4, 4)], 12, 8, [(8, 2), (2, 2)]),
            ([(4, 4), (2, 2)], 12, 8, [(2, 2), (8, 2)]),
            ([(2, 2), (2, 2), (2, 2)], 10, 10, [(2, 6), (6, 2), (2, 2)]),
            ([(2, 8), (8, 2)], 12, 16, [(2, 6), (2, 2)]),
            ([(6, 3), (1, 12), (10, 10)], 22, 28, [(14, 2), (2, 14), (2, 2)]),
            ([(2, 1), (1, 1)], 8, 4, [(2, 2), (6, 2)]),   # odd total -> right margin 1
            ([(1, 2), (1, 1)], 8, 6, [(2, 2), (5, 2)]),
            ([(1, 1), (1, 1), (1, 1)], 8, 8, [(2, 5), (5, 2), (2, 2)]),
            ([(4, 4), (4, 4)], 14, 8, [(8, 2), (2, 2)]),
            ([(1, 1), (1, 3)], 8, 6, [(5, 2), (2, 2)]),
            ([(1, 2), (2, 2)], 8, 6, [(6, 2), (2, 2)]),   # odd total -> right margin 1
            ([(1, 1), (1, 1)], 8, 4, [(5, 2), (2, 2)]),
            # probe5 c05: guillotine hole filling — the 8x8 nests below the
            # 16x16 sibling at (36,20) instead of starting a new band.
            ([(8, 8), (16, 16), (32, 32)], 54, 36, [(36, 20), (36, 2), (2, 2)]),
        ]
        for rects, want_w, want_h, want_pos in corpus:
            positions, w, h = _shelf_pack(rects)
            self.assertEqual((w, h), (want_w, want_h), rects)
            self.assertEqual(positions, want_pos, rects)

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
        self.assertEqual(dmp2[4], 3)  # constant value channel -> v3 grammar
        from actool_linux import dmp2mini
        ga = dmp2mini.decode_mini(dmp2, r.csi.width, r.csi.height, 2)
        if ga is None:  # larger sizes: v3 frame wraps an LZFSE stream
            (slen,) = struct.unpack_from("<I", dmp2, 12)
            ga = lzfse_compat.decompress(dmp2[16:16 + slen])
        self.assertEqual(len(ga), 2 * 16)
        v, a = struct.unpack_from("<2B", ga, 0)
        self.assertEqual((v, a), ((9 * 128 + 127) // 255, 128))  # premultiplied


class Probe6GrammarTests(unittest.TestCase):
    """probe6 oracle grammar rules for layout-12 color/GA sources."""

    def _checker_png(self, w, h, c0, c1, cell=1):
        def px(x, y):
            return c0 if ((x // cell) + (y // cell)) % 2 == 0 else c1
        raw = b"".join(b"\x00" + b"".join(bytes(px(x, y)) for x in range(w)) for y in range(h))
        return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                + _chunk(b"IDAT", zlib.compress(raw, 9)) + _chunk(b"IEND", b""))

    def _payload(self, png):
        csi = png_rendition("P", png, "p.png", scale=1).csi
        tlv_length, _one, _zero, payload_length = struct.unpack_from("<4I", csi, 168)
        return csi[184 + tlv_length:184 + tlv_length + payload_length]

    def _dmp2(self, png):
        pl = self._payload(png)
        mode, _codec, _flen, _f1, bpp, dlen, _z = struct.unpack_from("<7I", pl, 4)
        return mode, bpp, pl[32:32 + dlen]

    def test_two_color_checkerboard_uses_v4_palette_and_mode2(self):
        mode, bpp, dmp2 = self._dmp2(self._checker_png(64, 64, (255, 0, 0, 255), (0, 0, 255, 255), cell=8))
        self.assertEqual((mode, bpp, dmp2[4]), (2, 4, 4))  # opaque -> mode 2 (chk64 oracle)
        _w, _h, n, _bp = struct.unpack_from("<HHHH", dmp2, 8)
        self.assertEqual(n, 2)
        (slen,) = struct.unpack_from("<I", dmp2, 16 + 4 * n)
        plane = lzfse_compat.decompress(dmp2[20 + 4 * n:20 + 4 * n + slen])
        self.assertEqual(len(plane), 64 * 64)
        self.assertEqual(len(set(plane)), 2)

    def test_rich_translucent_gradient_uses_v2_mode0(self):
        rows = []
        for y in range(32):
            row = bytearray(b"\x00")
            for x in range(32):
                row += bytes((x * 255 // 31, y * 255 // 31, (x + y) * 255 // 62, 64 + 191 * x // 31))
            rows.append(bytes(row))
        png = (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack(">IIBBBBB", 32, 32, 8, 6, 0, 0, 0))
               + _chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + _chunk(b"IEND", b""))
        mode, bpp, dmp2 = self._dmp2(png)
        self.assertEqual((mode, bpp, dmp2[4]), (0, 4, 2))
        (slen,) = struct.unpack_from("<I", dmp2, 12)
        raw = lzfse_compat.decompress(dmp2[16:16 + slen])
        self.assertEqual(len(raw), 32 * 32 * 4)

    def test_opaque_noise_uses_v2_with_u32_frame_and_roundtrips(self):
        import random
        rng = random.Random(42)
        raw = b"\x00" + rng.randbytes(64 * 64 * 3)
        raw_rows = b"".join(b"\x00" + raw[1 + y * 64 * 3: 1 + (y + 1) * 64 * 3] for y in range(64))
        png = (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack(">IIBBBBB", 64, 64, 8, 2, 0, 0, 0))
               + _chunk(b"IDAT", zlib.compress(raw_rows, 9)) + _chunk(b"IEND", b""))
        mode, bpp, dmp2 = self._dmp2(png)
        self.assertEqual((mode, bpp, dmp2[4]), (2, 4, 2))  # opaque non-uniform rich: v2 + mode 2
        (slen,) = struct.unpack_from("<I", dmp2, 12)
        self.assertEqual(len(dmp2), 16 + slen)           # u32 frame is exact
        restored = lzfse_compat.decompress(dmp2[16:16 + slen])
        self.assertEqual(len(restored), 64 * 64 * 4)
        from actool_linux.packed import _decode_deepmap_pixels
        csi = png_rendition("P", png, "p.png", scale=1).csi
        decoded = _decode_deepmap_pixels(csi)
        self.assertIsNotNone(decoded)                    # noisy sources stay packable

    def test_ga_alpha_ramp_constant_value_uses_v3(self):
        rows = b"".join(b"\x00" + b"".join(bytes((90, 16 + x * 8)) for x in range(16)) for _y in range(16))
        png = (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack(">IIBBBBB", 16, 16, 8, 4, 0, 0, 0))
               + _chunk(b"IDAT", zlib.compress(rows, 9)) + _chunk(b"IEND", b""))
        mode, bpp, dmp2 = self._dmp2(png)
        self.assertEqual((mode, bpp, dmp2[4]), (0, 2, 3))  # ga_agrad oracle: v3, translucent -> mode 0

    def test_ga_value_gradient_uses_v2_mode2(self):
        rows = b"".join(b"\x00" + b"".join(bytes((x * 16, 255)) for x in range(16)) for _y in range(16))
        png = (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack(">IIBBBBB", 16, 16, 8, 4, 0, 0, 0))
               + _chunk(b"IDAT", zlib.compress(rows, 9)) + _chunk(b"IEND", b""))
        mode, bpp, dmp2 = self._dmp2(png)
        self.assertEqual((mode, bpp, dmp2[4]), (2, 2, 2))  # ga_vgrad oracle: v2, opaque -> mode 2


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

        # and end-to-end through pack_renditions (atlas is layout 1004).
        # 6 images x 64 colors land on one page under the 2026-07 pagination
        # rule (area 384 <= 20736, count <= 18) -> 384 colors in one page.
        assets = self._rainbow_assets(6, per_color=64)
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
