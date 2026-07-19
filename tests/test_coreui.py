"""CoreUI dialect profile selection and header stamping."""
import struct
import unittest
import zlib

from actool_linux.carwriter import build_assets_car, png_rendition, _car_header
from actool_linux.coreui import (
    COREUI_918, COREUI_975_DEVICE, COREUI_975_MACOS, PROFILES, profile_for_platform,
    resolve_profile,
)


def _png() -> bytes:
    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    raw = b"\x00\xff\x00\x00\xff"
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


class CoreUIProfileTests(unittest.TestCase):
    def _header(self, car: bytes):
        i = car.index(b"RATC")
        version = struct.unpack_from("<4I", car, i + 4)
        program = car[i + 20:i + 148].split(b"\x00")[0]
        tail = struct.unpack_from("<4I", car, i + 420)
        return version, program, tail

    def test_platform_defaults_match_oracles(self):
        asset = png_rendition("Red", _png())
        v, prog, tail = self._header(build_assets_car([asset], platform="macosx"))
        self.assertEqual(v[:3], (975, 17, 0))
        self.assertIn(b"[LAR]", prog)
        self.assertEqual(tail, (0, 2, 1, 1))
        v, prog, tail = self._header(build_assets_car([asset], platform="iphoneos"))
        self.assertEqual(v[:3], (975, 17, 0))
        self.assertNotIn(b"[LAR]", prog)
        self.assertEqual(tail, (0, 2, 1, 2))

    def test_legacy_918_profile_selectable(self):
        asset = png_rendition("Red", _png())
        v, prog, tail = self._header(build_assets_car([asset], platform="iphoneos", coreui_profile="coreui-918"))
        self.assertEqual(v[0], 918)
        self.assertIn(b"918.5", prog)
        self.assertEqual(tail, (0, 5, 1, 1))

    def test_profile_registry_and_errors(self):
        self.assertIs(profile_for_platform("macosx"), COREUI_975_MACOS)
        self.assertIs(profile_for_platform("iphoneos"), COREUI_975_DEVICE)
        self.assertIs(profile_for_platform(None), COREUI_975_MACOS)
        self.assertIs(resolve_profile(COREUI_918, "iphoneos"), COREUI_918)
        self.assertIs(resolve_profile("coreui-975", "iphoneos"), COREUI_975_DEVICE)
        with self.assertRaises(ValueError):
            resolve_profile("coreui-999", "macosx")
        self.assertIn("coreui-918", set(PROFILES))
        self.assertIn("coreui-975-macos", set(PROFILES))
        self.assertIn("coreui-800", set(PROFILES))

    def test_auto_select_profile(self):
        from actool_linux.coreui import auto_select_profile, COREUI_700, COREUI_850, COREUI_918_MACOS
        self.assertIs(auto_select_profile("macosx", "11.0"), COREUI_700)
        self.assertIs(auto_select_profile("macosx", "13.0"), COREUI_850)
        self.assertIs(auto_select_profile("macosx", "15.0"), COREUI_918_MACOS)

    def test_writer_comment_is_own_provenance(self):
        raw = _car_header(1, COREUI_975_MACOS)
        self.assertIn(b"actool-linux", raw)
        self.assertNotIn(b"Xcode", raw)

    def test_unknown_appearance_rejected(self):
        from actool_linux.carwriter import AssetRendition
        asset = AssetRendition("Red", png_rendition("Red", _png()).csi, 181, appearance=42)
        with self.assertRaises(ValueError):
            build_assets_car([asset])


if __name__ == "__main__":
    unittest.main()


class AppearanceRegistryTests(unittest.TestCase):
    def _dark_pair_pngs(self):
        # two variants -> registry triggered; solid colors keep payloads small
        import binascii
        def chunk(kind, payload):
            return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", binascii.crc32(kind + payload) & 0xFFFFFFFF)
        def png(px):
            raw = (b"\x00" + bytes(px) * 2) * 2
            return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 6, 0, 0, 0))
                    + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
        return png((255, 0, 0, 255)), png((0, 0, 255, 255))

    def test_macosx_uses_appkit_appearance_names(self):
        any_png, dark_png = self._dark_pair_pngs()
        assets = [png_rendition("A", any_png), png_rendition("A", dark_png, appearance=1)]
        car = build_assets_car(assets, platform="macosx")
        self.assertIn(b"NSAppearanceNameDarkAqua", car)
        self.assertIn(b"NSAppearanceNameSystem", car)
        self.assertNotIn(b"UIAppearanceDark", car)

    def test_ios_uses_uikit_appearance_names(self):
        any_png, dark_png = self._dark_pair_pngs()
        assets = [png_rendition("A", any_png), png_rendition("A", dark_png, appearance=1)]
        car = build_assets_car(assets, platform="iphoneos")
        self.assertIn(b"UIAppearanceDark", car)
        self.assertIn(b"UIAppearanceAny", car)
        self.assertNotIn(b"NSAppearanceNameDarkAqua", car)

    def test_multilevel_emits_appearancekeys(self):
        # >128 renditions -> multilevel writer; appearances must still produce
        # the APPEARANCEKEYS tree (single-level behavior observed in oracles).
        any_png, dark_png = self._dark_pair_pngs()
        assets = []
        for i in range(70):
            assets.append(png_rendition(f"Img{i:02d}", any_png))
            assets.append(png_rendition(f"Img{i:02d}", dark_png, appearance=1))
        self.assertGreater(len(assets), 128)  # force the multilevel writer
        car = build_assets_car(assets, platform="iphoneos")
        self.assertIn(b"UIAppearanceDark", car)
        self.assertIn(b"UIAppearanceAny", car)
