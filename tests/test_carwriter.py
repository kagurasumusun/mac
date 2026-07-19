import base64
import importlib.util
import unittest

HAS_LZFSE = importlib.util.find_spec("lzfse") is not None
HAS_CAIROSVG = importlib.util.find_spec("cairosvg") is not None

from actool_linux.bom import BOMStore
from actool_linux.car import CARFile
from actool_linux.carwriter import (
    build_app_icon_car, build_assets_car, build_color_car, build_data_car, build_jpeg_car, build_pdf_fallback_car, build_svg_car, build_symbol_car, build_symbol_template_car, build_layered_icon_car, build_watch_complication_car, build_solid_image_stack_aggregate_car,
    color_rendition, data_rendition, heif_rendition, jpeg_rendition, pdf_rendition, png_rendition,
)


class CARWriterTests(unittest.TestCase):
    def test_builds_self_consistent_data_car(self):
        raw = build_data_car("Blob", b"hello-linux-car", "public.plain-text")
        car = CARFile(BOMStore(raw))
        self.assertEqual(car.header.rendition_count, 1)
        self.assertEqual(car.extended_metadata.deployment_platform, "macosx")
        self.assertEqual(car.facets[0].name, "Blob")
        rendition = car.renditions[0]
        self.assertEqual((rendition.csi.pixel_format, rendition.csi.layout), ("DATA", 1000))
        self.assertEqual(rendition.csi.rendition_data[-15:], b"hello-linux-car")

    def test_builds_true_multi_level_trees(self):
        import struct
        from actool_linux.carwriter import _identifier
        names = []; used = set(); candidate = 0
        while len(names) < 140:
            name = f"Large{candidate:04d}"; candidate += 1
            identifier = _identifier(name)
            if identifier in used: continue
            used.add(identifier); names.append(name)
        raw = build_assets_car([data_rendition(name, name.encode()) for name in names])
        store = BOMStore(raw); car = CARFile(store)
        self.assertEqual((len(car.facets), len(car.renditions)), (140, 140))
        for tree_name in ("RENDITIONS", "FACETKEYS", "BITMAPKEYS"):
            descriptor = bytes(store.named_block(tree_name))
            root = struct.unpack_from(">I", descriptor, 8)[0]
            self.assertEqual(struct.unpack_from(">H", store.block(root), 0)[0], 0)

    def test_builds_mixed_multi_asset_car(self):
        jpeg = bytes.fromhex("ffd8ffc0000b080001000201011100ffd9")
        raw = build_assets_car([
            data_rendition("A", b"data"),
            jpeg_rendition("LongImage", jpeg, "photo.jpg"),
            color_rendition("Brand", 0.1, 0.2, 0.3, 1.0),
        ])
        car = CARFile(BOMStore(raw))
        self.assertEqual([f.name for f in car.facets], ["A", "Brand", "LongImage"])
        self.assertEqual(len(car.renditions), 3)
        self.assertEqual({r.csi.layout for r in car.renditions}, {12, 1000, 1009})

    def test_builds_color_rendition(self):
        car = CARFile(BOMStore(build_color_car("Brand", 1.0, 0.5, 0.25, 0.75)))
        rendition = car.renditions[0]
        self.assertEqual((rendition.csi.pixel_format, rendition.csi.layout), ("\0\0\0\0", 1009))
        self.assertEqual(car.facets[0].named_attributes["kCRThemePartName"], 0xD9)
        self.assertEqual(rendition.csi.rendition_data[:4], b"RLOC")

    def test_builds_display_p3_color(self):
        car = CARFile(BOMStore(build_assets_car([
            color_rendition("P3Col", 0.1, 0.2, 0.3, 0.8, color_space="display-p3")
        ])))
        self.assertEqual(car.renditions[0].csi.rendition_data[8:12], b"\x03\0\0\0")

    def test_builds_heif_rendition(self):
        heif = bytes.fromhex("000000106674797068656963000000000000001469737065000000000000000200000003")
        car = CARFile(BOMStore(build_assets_car([heif_rendition("Photo", heif, "photo.heic")])))
        rendition = car.renditions[0]
        self.assertEqual(rendition.csi.pixel_format, "HEIF")
        self.assertEqual(rendition.csi.rendition_data[-len(heif):], heif)

    def test_builds_verified_png_deepmap_subset(self):
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
        car = CARFile(BOMStore(build_assets_car([png_rendition("Logo", png, "pixel.png")])))
        rendition = car.renditions[0]
        self.assertEqual((rendition.csi.pixel_format, rendition.csi.width, rendition.csi.height), ("GA8 ", 1, 1))
        mode, version, w, h, pixels = self._decode_dmp2_pixels(rendition.csi.rendition_data)
        self.assertEqual(((w, h), mode, version), ((1, 1), 2, 1))  # 1px: Apple g_1x1 oracle -> v1 raw
        self.assertEqual(pixels, bytes.fromhex("00ff"))

    def test_builds_general_size_ga8_deepmap(self):
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAQAAADYv8WvAAAAEklEQVR4nGPg/m/wiCH0aNUKABRABFncH0e8AAAAAElFTkSuQmCC")
        car = CARFile(BOMStore(build_assets_car([png_rendition("Grid", png, "grid.png")])))
        rendition = car.renditions[0]
        self.assertEqual((rendition.csi.width, rendition.csi.height), (2, 2))
        mode, version, w, h, pixels = self._decode_dmp2_pixels(rendition.csi.rendition_data)
        self.assertEqual(((w, h), mode, version), ((2, 2), 0, 2))  # varying value channel -> v2
        self.assertEqual(pixels, bytes.fromhex("0bff2be242c550a8"))

    @staticmethod
    def _decode_dmp2_pixels(payload: bytes) -> tuple[int, int, int, int, bytes]:
        """Decode our MLEC/dmp2 payload (v1 raw / v2 LZFSE / v4 palette)."""
        import struct
        from actool_linux import lzfse_compat
        assert payload[:4] == b"MLEC"
        mode, codec, _flen, _f1, bpp, dlen, _z = struct.unpack_from("<7I", payload, 4)
        dmp2 = payload[32:32 + dlen]
        assert dmp2[:4] == b"dmp2"
        version = dmp2[4]
        w, h = struct.unpack_from("<HH", dmp2, 8)
        if version == 1:
            return mode, version, w, h, bytes(dmp2[12:])
        if version in (2, 3):
            (slen,) = struct.unpack_from("<I", dmp2, 12)
            return mode, version, w, h, lzfse_compat.decompress(dmp2[16:16 + slen])
        if version == 4:
            count, _bppv = struct.unpack_from("<HH", dmp2, 12)
            palette = dmp2[16:16 + 4 * count]
            (slen,) = struct.unpack_from("<I", dmp2, 16 + 4 * count)
            indices = lzfse_compat.decompress(dmp2[20 + 4 * count:20 + 4 * count + slen])
            out = bytearray()
            for idx in indices:
                out += palette[4 * idx:4 * idx + 4]
            return mode, version, w, h, bytes(out)
        raise AssertionError(f"unexpected dmp2 version {version}")

    def test_builds_rgba_argb_deepmap(self):
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAYAAABytg0kAAAAGklEQVR4nGPgFtf8b2Bi9YAhNND7YFVezCIAMaYGYTE5bUIAAAAASUVORK5CYII=")
        car = CARFile(BOMStore(build_assets_car([png_rendition("RGBA", png, "rgba.png")])))
        rendition = car.renditions[0]
        self.assertEqual((rendition.csi.pixel_format, rendition.csi.width, rendition.csi.height), ("ARGB", 2, 2))
        mode, version, w, h, pixels = self._decode_dmp2_pixels(rendition.csi.rendition_data)
        self.assertEqual(((w, h), mode), ((2, 2), 0))
        self.assertIn(version, (1, 2))
        self.assertEqual(pixels, bytes.fromhex("29170bff332e2ae0393d40c13a464ea2"))

    def test_builds_opaque_rgb_argb_deepmap(self):
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGPgFtc0MLFiCA30rsqLAQAQXQMfVfFocgAAAABJRU5ErkJggg==")
        car = CARFile(BOMStore(build_assets_car([png_rendition("RGB", png, "rgb.png")])))
        rendition = car.renditions[0]
        self.assertEqual(rendition.csi.pixel_format, "ARGB")
        # tiny (<=8px) varied sources store a v1 raw frame (hp9 k_2x2
        # oracle); larger varied RGB(A) use v2 LZFSE. MLEC mode 2 when
        # fully opaque (probe6 chk oracles)
        mode, version, w, h, pixels = self._decode_dmp2_pixels(rendition.csi.rendition_data)
        self.assertEqual(((w, h), mode, version), ((2, 2), 2, 1))
        self.assertEqual(pixels, bytes.fromhex("29170bff3a3430ff4b5155ff5c6e7aff"))

    def test_expands_indexed_png_to_argb_deepmap(self):
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACAgMAAAAP2OW3AAAADFBMVEX/AAAA/wAAAP///wDWAo97AAAABHRSTlP/gP9AaVvHCQAAAAxJREFUeJxjEGDYAAAA5ADBJ6joVwAAAABJRU5ErkJggg==")
        car = CARFile(BOMStore(build_assets_car([png_rendition("Indexed", png, "indexed.png")])))
        rendition = car.renditions[0]
        self.assertEqual(rendition.csi.pixel_format, "ARGB")
        mode, version, w, h, pixels = self._decode_dmp2_pixels(rendition.csi.rendition_data)
        self.assertEqual(((w, h), mode, version), ((2, 2), 0, 1))  # 4px: Apple k_2x2 oracle -> v1 raw
        self.assertEqual(pixels, bytes.fromhex("0000ffff00800080ff0000ff00404040"))

    def test_quantizes_16bit_ga_to_ga8_deepmap(self):
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACEAQAAACILxnsAAAAG0lEQVR4nGMQMvn/3yTszBmGsIqZMytmpaUBAEo6CEVd9yF5AAAAAElFTkSuQmCC")
        car = CARFile(BOMStore(build_assets_car([png_rendition("GA16", png, "ga16.png")])))
        rendition = car.renditions[0]
        self.assertEqual(rendition.csi.pixel_format, "GA8 ")
        mode, version, w, h, pixels = self._decode_dmp2_pixels(rendition.csi.rendition_data)
        self.assertEqual(((w, h), mode, version), ((2, 2), 0, 2))
        self.assertEqual(pixels, bytes.fromhex("12ff2acc34993066"))

    def test_decodes_adam7_rgba_png(self):
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAMAAAADCAYAAAEhL4UpAAAALUlEQVR4nA3IMQEAMAgDwZeDEubIYUQAIuI07Y0HEA4FrJwdmlras6Da1m/NPiwfDxJlJIrIAAAAAElFTkSuQmCC")
        car = CARFile(BOMStore(build_assets_car([png_rendition("Adam7", png)])))
        rendition = car.renditions[0]
        self.assertEqual((rendition.csi.width, rendition.csi.height), (3, 3))
        _mode, _ver, w, h, pixels = self._decode_dmp2_pixels(rendition.csi.rendition_data)
        self.assertEqual((w, h), (3, 3))
        expected = bytearray()
        for y in range(3):
            for x in range(3):
                r, g, b, a = x * 70, y * 80, (x + y) * 40, 255 if (x + y) % 2 == 0 else 128
                expected += bytes(((b*a+127)//255, (g*a+127)//255, (r*a+127)//255, a))
        self.assertEqual(pixels, bytes(expected))

    @unittest.skipUnless(HAS_LZFSE, "optional lzfse dependency is unavailable")
    def test_builds_cbck_app_icon_records(self):
        import lzfse
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGPgFtc0MLFiCA30rsqLAQAQXQMfVfFocgAAAABJRU5ErkJggg==")
        car = CARFile(BOMStore(build_app_icon_car("AppIcon", png)))
        self.assertEqual(len(car.facets), 1)
        self.assertEqual(len(car.renditions), 4)
        self.assertEqual(car.key_format.names[5], "kCRThemeDimension2Name")
        images = [r for r in car.renditions if r.csi.width]
        self.assertEqual([(r.key["kCRThemeIdiomName"], r.key["kCRThemePartName"], r.key["kCRThemeDimension2Name"]) for r in images], [(1, 220, 1), (2, 220, 1)])
        payload = images[0].csi.rendition_data
        self.assertEqual(payload[:20], b"MLEC" + bytes.fromhex("0300000004000000010000004b434243"))
        rows, size = __import__("struct").unpack_from("<2I", payload, 28)
        self.assertEqual(rows, 2)
        self.assertEqual(len(lzfse.decompress(payload[36:36 + size])), 16)

    def test_localization_registry_and_rendition_keys(self):
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
        store = BOMStore(build_assets_car([
            png_rendition("Localized", png, "base.png"),
            png_rendition("Localized", png, "ja.png", localization="ja"),
            png_rendition("Localized", png, "arabic.png", localization="ar"),
        ], platform="iphoneos", target="15.0"))
        from actool_linux.tree import read_leaf_entries
        registry = {e.key.decode(): int.from_bytes(e.value, "little") for e in read_leaf_entries(store, "LOCALIZATIONKEYS")}
        self.assertEqual(set(registry), {"ar", "ja"})
        car = CARFile(store)
        observed = {r.csi.name: r.key["kCRThemeLocalizationName"] for r in car.renditions}
        self.assertEqual(observed, {"base.png": 0, "arabic.png": registry["ar"], "ja.png": registry["ja"]})

    def test_high_contrast_appearance_registry(self):
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
        store = BOMStore(build_assets_car([
            png_rendition("Contrast", png, "base.png"),
            png_rendition("Contrast", png, "high.png", appearance="high-contrast"),
        ], platform="iphoneos", target="15.0"))
        from actool_linux.tree import read_leaf_entries
        registry = [(e.key, int.from_bytes(e.value, "little")) for e in read_leaf_entries(store, "APPEARANCEKEYS")]
        self.assertEqual(registry, [(b"UIAppearanceAny", 0), (b"UIAppearanceHighContrastAny", 2)])
        car = CARFile(store)
        self.assertEqual(car.renditions[-1].key["kCRThemeAppearanceName"], 2)

    def test_idiom_and_dark_appearance_keys(self):
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
        car = CARFile(BOMStore(build_assets_car([
            png_rendition("Variant", png, "base.png"),
            png_rendition("Variant", png, "phone.png", idiom="iphone"),
            png_rendition("Variant", png, "pad.png", idiom="ipad"),
            png_rendition("Variant", png, "dark.png", appearance="dark"),
        ], platform="iphoneos", target="15.0")))
        self.assertEqual(car.key_format.names, (
            "kCRThemeAppearanceName", "kCRThemeLocalizationName", "kCRThemeScaleName",
            "kCRThemeIdiomName", "kCRThemeSubtypeName", "kCRThemeIdentifierName",
            "kCRThemeElementName", "kCRThemePartName",
        ))
        self.assertEqual([(r.csi.name, r.key["kCRThemeAppearanceName"], r.key["kCRThemeIdiomName"]) for r in car.renditions], [
            ("base.png", 0, 0), ("phone.png", 0, 1), ("pad.png", 0, 2), ("dark.png", 1, 0),
        ])

    def test_multiple_scales_share_one_facet(self):
        png1 = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
        png2 = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAQAAADYv8WvAAAAEklEQVR4nGPg/m/wiCH0aNUKABRABFncH0e8AAAAAElFTkSuQmCC")
        car = CARFile(BOMStore(build_assets_car([
            png_rendition("Logo", png1, scale=1), png_rendition("Logo", png2, scale=2),
        ])))
        self.assertEqual(len(car.facets), 1)
        self.assertEqual(len(car.renditions), 2)
        self.assertEqual([r.key["kCRThemeScaleName"] for r in car.renditions], [1, 2])
        self.assertEqual([r.csi.scale for r in car.renditions], [1.0, 2.0])

    @unittest.skipUnless(HAS_CAIROSVG, "optional cairosvg dependency is unavailable")
    def test_builds_svg_with_automatic_deepmap_fallbacks(self):
        svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="20"><rect width="10" height="20" fill="#369"/></svg>'
        car = CARFile(BOMStore(build_svg_car("Vector", svg)))
        self.assertEqual(len(car.facets), 1)
        self.assertEqual([(r.key["kCRThemePartName"], r.key["kCRThemeScaleName"]) for r in car.renditions], [(42, 1), (181, 1), (181, 2), (181, 3)])
        self.assertEqual(car.renditions[0].csi.pixel_format, "SVG ")
        self.assertEqual(car.renditions[0].csi.rendition_data[-len(svg):], svg)
        self.assertEqual([(r.csi.width, r.csi.height, r.csi.flags) for r in car.renditions[1:]], [(10,20,276),(20,40,276),(30,60,276)])

    def test_builds_pdf_with_deepmap_fallbacks(self):
        pdf = b"%PDF-1.3\n1 0 obj<<>>endobj\n%%EOF"
        png1 = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
        png2 = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAQAAADYv8WvAAAAEklEQVR4nGPg/m/wiCH0aNUKABRABFncH0e8AAAAAElFTkSuQmCC")
        car = CARFile(BOMStore(build_pdf_fallback_car("Vector", pdf, png1, png2, "vector.pdf", png_3x=png2)))
        self.assertEqual(len(car.renditions), 4)
        self.assertEqual([(r.key["kCRThemePartName"], r.key["kCRThemeScaleName"]) for r in car.renditions], [(42, 1), (181, 1), (181, 2), (181, 3)])
        self.assertEqual([r.csi.flags for r in car.renditions], [4, 276, 276, 276])

    def test_builds_pdf_vector_rendition(self):
        pdf = b"%PDF-1.3\n1 0 obj<<>>endobj\n%%EOF"
        car = CARFile(BOMStore(build_assets_car([pdf_rendition("Vector", pdf, "vector.pdf")])))
        rendition = car.renditions[0]
        self.assertEqual((rendition.csi.pixel_format, rendition.csi.layout, rendition.csi.flags), ("PDF ", 9, 4))
        self.assertEqual(rendition.csi.rendition_data[-len(pdf):], pdf)

    def test_builds_jpeg_rendition(self):
        jpeg = bytes.fromhex("ffd8ffc0000b080001000201011100ffd9")
        car = CARFile(BOMStore(build_jpeg_car("Photo", jpeg, "photo.jpg")))
        rendition = car.renditions[0]
        self.assertEqual((rendition.csi.pixel_format, rendition.csi.layout), ("JPEG", 12))
        self.assertEqual(rendition.csi.name, "photo.jpg")
        self.assertEqual(rendition.csi.rendition_data[-len(jpeg):], jpeg)

    def test_is_deterministic(self):
        args = ("Blob", b"same", "public.data")
        self.assertEqual(build_data_car(*args), build_data_car(*args))


    def test_builds_symbol_svg_rendition(self):
        svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><path d="M0 0h10v10H0z"/></svg>'
        car = CARFile(BOMStore(build_symbol_car("Glyph", svg, "glyph.svg")))
        self.assertEqual(car.key_format.names[-2:], ("kCRThemeGlyphWeightName", "kCRThemeGlyphSizeName"))
        rendition = car.renditions[0]
        self.assertEqual((rendition.csi.pixel_format, rendition.csi.layout, rendition.csi.flags), ("SVG ", 1017, 4))
        self.assertEqual((rendition.key["kCRThemePartName"], rendition.key["kCRThemeGlyphWeightName"], rendition.key["kCRThemeGlyphSizeName"]), (59, 4, 2))
        self.assertEqual([x.tag for x in rendition.csi.tlvs], [1004, 1006, 1018, 1019])


    def test_expands_multi_weight_symbol_template(self):
        svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><g id="Symbols"><g id="Regular-M"><path d="M0 0h10v10H0z"/></g><g id="Bold-L"><path d="M0 0h20v20H0z"/></g></g></svg>'
        car = CARFile(BOMStore(build_symbol_template_car("Multi", svg)))
        self.assertEqual([(r.key["kCRThemeGlyphWeightName"],r.key["kCRThemeGlyphSizeName"]) for r in car.renditions], [(4,2),(7,3)])
        self.assertTrue(all(r.csi.layout == 1017 for r in car.renditions))

    @unittest.skipUnless(HAS_LZFSE, "optional lzfse dependency is unavailable")
    def test_platform_specific_app_icon_idioms(self):
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGPgFtc0MLFiCA30rsqLAQAQXQMfVfFocgAAAABJRU5ErkJggg==")
        from actool_linux.carwriter import build_app_icon_car
        expected={"appletvos":3,"watchos":5,"macosx":7,"xros":8}
        for platform,idiom in expected.items():
            car=CARFile(BOMStore(build_app_icon_car("AppIcon",png,platform=platform)))
            self.assertEqual({r.key["kCRThemeIdiomName"] for r in car.renditions},{idiom})
            self.assertEqual({r.key["kCRThemePartName"] for r in car.renditions},{218,220})


    def test_layered_tv_and_vision_icons(self):
        png=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAQAAADYv8WvAAAAEklEQVR4nGPg/m/wiCH0aNUKABRABFncH0e8AAAAAElFTkSuQmCC")
        for platform,idiom in (("appletvos",3),("xros",8)):
            car=CARFile(BOMStore(build_layered_icon_car("LayeredIcon",[png,png],platform=platform,depths=[10,20] if platform=="xros" else None)))
            expected_depths=[10,20] if platform=="xros" else [0,0]
            self.assertEqual([(r.key["kCRThemeIdiomName"],r.key["kCRThemeLayerName"],r.key["kCRThemeDimension2Name"]) for r in car.renditions],[(idiom,1,expected_depths[0]),(idiom,2,expected_depths[1])])

    def test_watch_complication_subtypes(self):
        png=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAQAAADYv8WvAAAAEklEQVR4nGPg/m/wiCH0aNUKABRABFncH0e8AAAAAElFTkSuQmCC")
        car=CARFile(BOMStore(build_watch_complication_car("Complication",[png,png],families=["graphicCircular","graphicRectangular"],roles=["foreground","mask"])))
        self.assertEqual([(r.key["kCRThemeIdiomName"],r.key["kCRThemeSubtypeName"],r.key["kCRThemeDimension2Name"]) for r in car.renditions],[(5,4,2),(5,7,3)])

    @unittest.skipUnless(HAS_LZFSE, "optional lzfse dependency is unavailable")
    def test_builds_experimental_solid_image_stack_aggregate(self):
        png=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAQAAADYv8WvAAAAEklEQVR4nGPg/m/wiCH0aNUKABRABFncH0e8AAAAAElFTkSuQmCC")
        car=CARFile(BOMStore(build_solid_image_stack_aggregate_car("AppIcon",[("Front",png),("Middle",png),("Back",png)])))
        self.assertIn(1018,[r.csi.layout for r in car.renditions])
        self.assertEqual(sum(r.csi.layout==1007 for r in car.renditions),6)
        self.assertEqual(sum(r.csi.layout==1008 for r in car.renditions),6)

    def test_localization_and_long_identifier_formulas(self):
        from actool_linux.carwriter import _identifier, _localization_identifier
        self.assertEqual(_localization_identifier("de"), 4651)
        self.assertEqual(_localization_identifier("ja"), 29613)
        self.assertEqual(_localization_identifier("en"), 31336)
        long_name = "App Icon - Large/Middle/Content/HighContrast/Variant/Subtype/VeryLongNameSuffixExceedingThirtyTwoBytes"
        val = _identifier(long_name)
        self.assertGreater(val, 0)
        self.assertLessEqual(val, 65535)

    def test_extended_localization_subtags(self):
        from actool_linux.carwriter import _localization_identifier
        subtags = ["en-GB", "en-US", "zh-Hans", "zh-Hant", "pt-BR", "es-MX", "fr-CA"]
        ids = [_localization_identifier(tag) for tag in subtags]
        self.assertEqual(len(set(ids)), len(subtags))
        self.assertEqual(_localization_identifier("en-GB"), 31340)
        self.assertEqual(_localization_identifier("zh-Hans"), 20115)


if __name__ == "__main__":
    unittest.main()

