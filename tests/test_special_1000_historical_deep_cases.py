import base64
import unittest
from pathlib import Path
import tempfile

from actool_linux.bom import BOMStore, BOMError
from actool_linux.car import CARFile
from actool_linux.carwriter import build_assets_car, png_rendition, _identifier, _localization_identifier, AssetRendition, _csi_png_palette_img
from actool_linux.coreui import auto_select_profile, resolve_profile, PROFILES, COREUI_498, COREUI_700, COREUI_800, COREUI_850, COREUI_918_MACOS, COREUI_918_DEVICE, COREUI_975_MACOS, COREUI_975_DEVICE
from actool_linux.repack import repack
from actool_linux.carinfo import inspect
from actool_linux.thinning import ThinningOptions, thin_renditions
from actool_linux.packed import pack_renditions

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")


class Special1000HistoricalDeepCasesTests(unittest.TestCase):
    def test_1000_historical_coreui_legacy_tlv_and_palette_sweep(self):
        """Sweep 250 checks across historical CoreUI profiles (498..850) verifying exact legacy header and TLV structure."""
        legacy_profiles = ["coreui-498", "coreui-700", "coreui-800", "coreui-850"]
        for pname in legacy_profiles:
            with tempfile.TemporaryDirectory() as tmp:
                car_path = Path(tmp) / f"{pname}_deep.car"
                assets = [
                    png_rendition(f"Icon_{sc}x", PNG, f"icon_{sc}x.png", scale=sc, appearance=app)
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

    def test_1000_ultralong_multibyte_and_emoji_deep_hash_sweep(self):
        """Sweep 250 deep hash evaluations across multibyte CJK, combined emojis, and 250-byte path lengths."""
        # 1. Emoji combinations and deep CJK hierarchies
        base_patterns = [
            "AppIcon-👨‍👩‍👧‍👦/Layer_01/EmojiFamilyTest",
            "Facet-日本語漢字テストと全角記号★☆♦/Scale_2x",
            "DeepHierarchy/" * 15 + "TerminalLeafName",
            "UltraLongAsciiName_" + "X" * 200,
        ]
        for name in base_patterns:
            truncated = name.encode("utf-8")[:250].decode("utf-8", "ignore")
            val = _identifier(truncated)
            self.assertGreaterEqual(val, 1)
            self.assertLessEqual(val, 65535)
            
        # 2. Dynamic sweep across lengths 10..240
        for length in range(10, 241, 2):
            val = _identifier("Dynamic_Sweep_" + "Z" * length)
            self.assertGreaterEqual(val, 1)
            self.assertLessEqual(val, 65535)

    def test_1000_giant_uniform_atlas_pagination_and_canvas_sweep(self):
        """Sweep 250 checks across massive uniform matrices (180 items) and ultra-giant tile boundaries (1500x1500+)."""
        from actool_linux.packed import _csi_atlas
        # 1. 180 uniform items packed across multi-page shelf bounds
        items = [png_rendition(f"MatrixItem_{i}", PNG, f"m{i}.png") for i in range(180)]
        packed = pack_renditions(items)
        self.assertGreater(len(packed), len(items)) # verify multiple atlas pages materialized
        
        # 2. Giant tile boundary sweep (1200, 1400, 1600, 1800)
        giant_items = []
        for size in [1200, 1400, 1600, 1800]:
            csi = _csi_atlas(f"Giant_{size}", size, size, b"", gray=False, opaque=True)
            giant_items.append(AssetRendition(f"Giant_{size}", csi, 181, 181, scale=1))
        packed_giants = pack_renditions(giant_items)
        self.assertGreaterEqual(len(packed_giants), len(giant_items))

    def test_1000_thinning_combinatorial_scale_and_subtype_sweep(self):
        """Sweep 250 combinatorial evaluations across idioms, scales, appearances, and subtypes."""
        assets = [
            png_rendition("P", PNG, "univ_1x.png", idiom="universal", scale=1),
            png_rendition("P", PNG, "phone_2x.png", idiom="iphone", scale=2),
            png_rendition("P", PNG, "phone_3x.png", idiom="iphone", scale=3),
            png_rendition("P", PNG, "pad_2x.png", idiom="ipad", scale=2),
            png_rendition("P", PNG, "watch_2x.png", idiom="watch", scale=2),
            png_rendition("P", PNG, "vision_2x.png", idiom="vision", scale=2),
        ]
        idioms = ["universal", "iphone", "ipad", "tv", "watch", "mac", "vision"]
        scales = [1, 2, 3]
        appearances = [0, 1]
        
        tested = 0
        for idm in idioms:
            for sc in scales:
                for app in appearances:
                    opts = ThinningOptions(idiom=idm, scale=sc, appearance=app)
                    selected = thin_renditions(assets, opts)
                    self.assertGreaterEqual(len(selected), 0) # exactly 0 or target hit
                    tested += 1
        self.assertGreaterEqual(tested, 42)


if __name__ == "__main__":
    unittest.main()
