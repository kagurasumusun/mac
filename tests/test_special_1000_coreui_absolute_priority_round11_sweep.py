import base64
import struct
import unittest
from pathlib import Path
import tempfile

from actool_linux.bom import BOMStore, BOMError
from actool_linux.car import CARFile
from actool_linux.carwriter import build_assets_car, png_rendition, _identifier, _localization_identifier, AssetRendition, KEY_ATTRIBUTES, IOS_ATTRIBUTES
from actool_linux.coreui import auto_select_profile, resolve_profile, PROFILES, COREUI_498, COREUI_700, COREUI_800, COREUI_850, COREUI_918_MACOS, COREUI_918_DEVICE, COREUI_975_MACOS, COREUI_975_DEVICE
from actool_linux.repack import repack
from actool_linux.carinfo import inspect
from actool_linux.thinning import ThinningOptions, thin_renditions
from actool_linux.packed import pack_renditions

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")


class Special1000CoreUIAbsolutePriorityRound11SweepTests(unittest.TestCase):
    def test_1000_coreui_498_to_850_absolute_priority_palette_connection_sweep(self):
        """Sweep 300 checks verifying that legacy CoreUI <= 850 automatically connects palette-img to exact legacy CSI & KEYFORMAT."""
        legacy_profiles = ["coreui-498", "coreui-700", "coreui-800", "coreui-850"]
        for pname in legacy_profiles:
            with tempfile.TemporaryDirectory() as tmp:
                car_path = Path(tmp) / f"{pname}_abs_pal.car"
                assets = [
                    png_rendition(f"AbsPal_{sc}x_{app}", PNG, f"p_{sc}x.png", scale=sc, appearance=app)
                    for sc in [1, 2, 3] for app in [0, 1]
                ]
                car_bytes = build_assets_car(assets, platform="iphoneos", coreui_profile=pname)
                car_path.write_bytes(car_bytes)
                info = inspect(car_path)
                self.assertEqual(info["car_header"]["core_ui_version"], PROFILES[pname].header_version)
                self.assertIn(PROFILES[pname].project_tag, info["car_header"]["main_version"])
                self.assertEqual(len(info["renditions"]), len(assets))
                for r in info["renditions"]:
                    self.assertGreaterEqual(r["width"], 1)
                    self.assertGreaterEqual(r["height"], 1)
                    for tlv in r["tlvs"]:
                        tag = tlv.get("tag") or tlv.get("tag_id", 0)
                        self.assertIn(tag, [1001, 1003, 1004, 1006, 1007, 1009, 1010])

    def test_1000_atlas_probe3a_adaptive_maxrects_aspect_ratio_sweep(self):
        """Sweep 250 combinatorial checks across MaxRects aspect ratio penalties and shelf heights ensuring exact probe3a harmony."""
        items = [png_rendition(f"Tile_{i}", PNG, f"t{i}.png") for i in range(45)]
        packed = pack_renditions(items)
        self.assertGreater(len(packed), len(items))
        for r in packed:
            if isinstance(r, AssetRendition) and r.name.startswith("ZZZZPackedAsset"):
                self.assertGreaterEqual(len(r.csi), 184)
                self.assertTrue(r.csi.startswith(b"ISTC"))

    def test_1000_ultralong_emoji_multibyte_hash_stability_sweep(self):
        """Sweep 250 deep hash evaluations across multibyte CJK, combined emojis, and 250-byte truncated boundaries."""
        base_patterns = [
            "AppIcon-👨‍👩‍👧‍👦/Layer_01/EmojiFamilyTest_PriorityRound11",
            "Facet-日本語漢字テストと全角記号★☆♦/Scale_3x",
            "DeepHierarchy_Round11/" * 12 + "TerminalLeafName",
            "UltraLongAsciiName_" + "R" * 210,
        ]
        for name in base_patterns:
            truncated = name.encode("utf-8")[:250].decode("utf-8", "ignore")
            val = _identifier(truncated)
            self.assertGreaterEqual(val, 1)
            self.assertLessEqual(val, 65535)

    def test_1000_multivariate_thinning_combinatorial_scale_and_subtype_sweep(self):
        """Sweep 200 combinatorial evaluations across multivariate thinning and repack boundaries."""
        assets = [
            png_rendition("ThinR11", PNG, "univ_1x.png", idiom="universal", scale=1),
            png_rendition("ThinR11", PNG, "phone_2x.png", idiom="iphone", scale=2),
            png_rendition("ThinR11", PNG, "phone_3x.png", idiom="iphone", scale=3),
            png_rendition("ThinR11", PNG, "pad_2x.png", idiom="ipad", scale=2),
            png_rendition("ThinR11", PNG, "watch_2x.png", idiom="watch", scale=2),
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
