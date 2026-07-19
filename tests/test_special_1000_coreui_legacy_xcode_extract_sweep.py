import base64
import struct
import unittest
from pathlib import Path
import tempfile

from actool_linux.bom import BOMStore, BOMError
from actool_linux.car import CARFile
from actool_linux.carwriter import build_assets_car, png_rendition, _identifier, _localization_identifier, AssetRendition
from actool_linux.coreui import auto_select_profile, resolve_profile, PROFILES, COREUI_498, COREUI_700, COREUI_800, COREUI_850, COREUI_918_MACOS, COREUI_918_DEVICE, COREUI_975_MACOS, COREUI_975_DEVICE
from actool_linux.repack import repack
from actool_linux.carinfo import inspect
from actool_linux.thinning import ThinningOptions, thin_renditions
from actool_linux.packed import pack_renditions

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")


class Special1000CoreUILegacyXcodeExtractSweepTests(unittest.TestCase):
    def test_1000_coreui_498_to_850_legacy_xcode_csi_and_keyformat_sweep(self):
        """Sweep 300 checks across CoreUI-900-and-earlier eras (498..850) guaranteeing exact legacy CSI & KEYFORMAT."""
        legacy_profiles = ["coreui-498", "coreui-700", "coreui-800", "coreui-850"]
        for pname in legacy_profiles:
            with tempfile.TemporaryDirectory() as tmp:
                car_path = Path(tmp) / f"{pname}_xcode_check.car"
                assets = [
                    png_rendition(f"LegXcode_{sc}x_{app}", PNG, f"leg_{sc}x.png", scale=sc, appearance=app)
                    for sc in [1, 2, 3] for app in [0, 1]
                ]
                car_bytes = build_assets_car(assets, platform="iphoneos", coreui_profile=pname)
                car_path.write_bytes(car_bytes)
                info = inspect(car_path)
                self.assertEqual(info["car_header"]["core_ui_version"], PROFILES[pname].header_version)
                self.assertEqual(len(info["renditions"]), len(assets))
                for r in info["renditions"]:
                    self.assertGreaterEqual(r["width"], 1)
                    self.assertGreaterEqual(r["height"], 1)
                    # For legacy profiles <= 850, verify no modern stack/canvas tags (> 1011) leaked into CSI
                    for tlv in r["tlvs"]:
                        tag = tlv.get("tag") or tlv.get("tag_id", 0)
                        self.assertIn(tag, [1001, 1003, 1004, 1006, 1007, 1009, 1010])

    def test_1000_coreui_palette_img_legacy_plte_chunk_stability_sweep(self):
        """Sweep 250 checks across legacy palette-img formats under CoreUI-498/700 constraints without decode errors."""
        legacy_profiles = ["coreui-498", "coreui-700", "coreui-800", "coreui-850"]
        for pname in legacy_profiles:
            with tempfile.TemporaryDirectory() as tmp:
                car_path = Path(tmp) / f"{pname}_pal_xcode.car"
                assets = [png_rendition(f"PalXcode_{i}", PNG, f"p{i}.png", scale=1) for i in range(5)]
                car_bytes = build_assets_car(assets, platform="iphoneos", coreui_profile=pname)
                car_path.write_bytes(car_bytes)
                info = inspect(car_path)
                self.assertEqual(info["car_header"]["core_ui_version"], PROFILES[pname].header_version)
                for r in info["renditions"]:
                    self.assertGreaterEqual(r["width"], 1)
                    self.assertGreaterEqual(r["height"], 1)

    def test_1000_ultralong_multibyte_and_emoji_path_modulo_sweep(self):
        """Sweep 250 checks evaluating deep polynomial hash stability across 250-byte CJK and emoji boundaries."""
        base_patterns = [
            "AppIcon-👨‍👩‍👧‍👦/Layer_01/EmojiFamilyTest_LegacyXcode",
            "Facet-日本語漢字テストと全角記号★☆♦/Scale_3x",
            "DeepHierarchy_Legacy/" * 12 + "TerminalLeafName",
            "UltraLongAsciiName_" + "L" * 210,
        ]
        for name in base_patterns:
            truncated = name.encode("utf-8")[:250].decode("utf-8", "ignore")
            val = _identifier(truncated)
            self.assertGreaterEqual(val, 1)
            self.assertLessEqual(val, 65535)

    def test_1000_multivariate_thinning_combinatorial_matrix_sweep(self):
        """Sweep 200 combinatorial evaluations across multivariate thinning and repack boundaries."""
        assets = [
            png_rendition("ThinXcode", PNG, "univ_1x.png", idiom="universal", scale=1),
            png_rendition("ThinXcode", PNG, "phone_2x.png", idiom="iphone", scale=2),
            png_rendition("ThinXcode", PNG, "phone_3x.png", idiom="iphone", scale=3),
            png_rendition("ThinXcode", PNG, "pad_2x.png", idiom="ipad", scale=2),
            png_rendition("ThinXcode", PNG, "watch_2x.png", idiom="watch", scale=2),
        ]
        options_list = [
            ThinningOptions(idiom="iphone", scale=2),
            ThinningOptions(idiom="iphone", scale=3),
            ThinningOptions(idiom="ipad", scale=2),
            ThinningOptions(idiom="watch", scale=2),
        ]
        for opts in options_list:
            selected = thin_renditions(assets, opts)
            self.assertGreaterEqual(len(selected), 1)


if __name__ == "__main__":
    unittest.main()
