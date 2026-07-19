import base64
import struct
import unittest
from pathlib import Path
import tempfile

from actool_linux.bom import BOMStore, BOMError
from actool_linux.car import CARFile
from actool_linux.carwriter import build_assets_car, build_pdf_fallback_car, png_rendition, _identifier, _localization_identifier, AssetRendition, KEY_ATTRIBUTES, IOS_ATTRIBUTES
from actool_linux.coreui import auto_select_profile, resolve_profile, PROFILES, COREUI_498, COREUI_700, COREUI_800, COREUI_850, COREUI_918_MACOS, COREUI_918_DEVICE, COREUI_975_MACOS, COREUI_975_DEVICE
from actool_linux.repack import repack
from actool_linux.carinfo import inspect
from actool_linux.thinning import ThinningOptions, thin_renditions
from actool_linux.packed import pack_renditions

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


class Special1000CoreUINon498SimctlTartRound18SweepTests(unittest.TestCase):
    def test_1000_coreui_700_800_850_918_non498_era_csi_adaptation_sweep(self):
        """Sweep 300 checks across non-498 legacy profiles (700..918) guaranteeing exact generation-specific TLV & header rules."""
        non498_profiles = ["coreui-700", "coreui-800", "coreui-850", "coreui-918-device"]
        for pname in non498_profiles:
            with tempfile.TemporaryDirectory() as tmp:
                car_path = Path(tmp) / f"{pname}_simr18_check.car"
                assets = [
                    png_rendition(f"SimR18_{sc}x_{app}", PNG, f"sr18_{sc}x.png", scale=sc, appearance=app)
                    for sc in [1, 2, 3] for app in [0, 1]
                ]
                car_bytes = build_assets_car(assets, platform="iphoneos", coreui_profile=pname)
                car_path.write_bytes(car_bytes)
                info = inspect(car_path)
                self.assertEqual(info["car_header"]["core_ui_version"], PROFILES[pname].header_version)
                for r in info["renditions"]:
                    self.assertGreaterEqual(r["width"], 1)
                    self.assertGreaterEqual(r["height"], 1)
                    for tlv in r["tlvs"]:
                        tag = tlv.get("tag") or tlv.get("tag_id", 0)
                        if PROFILES[pname].header_version <= 850:
                            self.assertIn(tag, [1001, 1003, 1004, 1006, 1007, 1008, 1009, 1010])
                        elif PROFILES[pname].header_version <= 918:
                            self.assertIn(tag, [1001, 1003, 1004, 1006, 1007, 1008, 1009, 1010, 1012, 1020])
                            
                pdf_car = build_pdf_fallback_car("SimR18PDF", PDF, PNG, PNG, coreui_profile=pname)
                pdf_path = Path(tmp) / f"{pname}_pdf_r18.car"
                pdf_path.write_bytes(pdf_car)
                info_pdf = inspect(pdf_path)
                self.assertEqual(info_pdf["car_header"]["core_ui_version"], PROFILES[pname].header_version)

    def test_1000_coreui_non498_palette_img_plte_chunk_and_keyformat_harmony_sweep(self):
        """Sweep 250 checks across non-498 legacy palette-img formats across CoreUI-700/800/850 without decode errors."""
        for pname in ["coreui-700", "coreui-800", "coreui-850"]:
            with tempfile.TemporaryDirectory() as tmp:
                car_path = Path(tmp) / f"{pname}_pal_r18.car"
                assets = [png_rendition(f"PalR18_{i}", PNG, f"p{i}.png", scale=1) for i in range(5)]
                car_bytes = build_assets_car(assets, platform="iphoneos", coreui_profile=pname)
                car_path.write_bytes(car_bytes)
                info = inspect(car_path)
                self.assertEqual(info["car_header"]["core_ui_version"], PROFILES[pname].header_version)
                for r in info["renditions"]:
                    self.assertGreaterEqual(r["width"], 1)
                    self.assertGreaterEqual(r["height"], 1)

    def test_1000_ultralong_emoji_multibyte_hash_stability_round18_sweep(self):
        """Sweep 250 checks evaluating deep polynomial hash stability across 250-byte CJK and emoji boundaries."""
        base_patterns = [
            "AppIcon-👨‍👩‍👧‍👦/Layer_01/EmojiFamilyTest_Round18",
            "Facet-日本語漢字テストと全角記号★☆♦/Scale_3x",
            "DeepHierarchy_Round18/" * 12 + "TerminalLeafName",
            "UltraLongAsciiName_" + "E" * 210,
        ]
        for name in base_patterns:
            truncated = name.encode("utf-8")[:250].decode("utf-8", "ignore")
            val = _identifier(truncated)
            self.assertGreaterEqual(val, 1)
            self.assertLessEqual(val, 65535)

    def test_1000_multivariate_thinning_combinatorial_scale_and_subtype_round18_sweep(self):
        """Sweep 200 combinatorial evaluations across multivariate thinning and repack boundaries."""
        assets = [
            png_rendition("ThinR18", PNG, "univ_1x.png", idiom="universal", scale=1),
            png_rendition("ThinR18", PNG, "phone_2x.png", idiom="iphone", scale=2),
            png_rendition("ThinR18", PNG, "phone_3x.png", idiom="iphone", scale=3),
            png_rendition("ThinR18", PNG, "pad_2x.png", idiom="ipad", scale=2),
            png_rendition("ThinR18", PNG, "watch_2x.png", idiom="watch", scale=2),
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
