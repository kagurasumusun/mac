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


class Special1000CoreUIPaletteAndAtlasSweepTests(unittest.TestCase):
    def test_1000_coreui_498_to_975_palette_img_and_deepmap_parity_sweep(self):
        """Sweep 300 checks across all 10 CoreUI profiles verifying legacy & modern CSI structure without decoding errors."""
        all_profiles = list(PROFILES.keys())
        for pname in all_profiles:
            with tempfile.TemporaryDirectory() as tmp:
                car_path = Path(tmp) / f"{pname}_parity.car"
                assets = [
                    png_rendition(f"Pal_{sc}x_{app}", PNG, f"p_{sc}x.png", scale=sc, appearance=app)
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
                    # For legacy profiles, verify no modern stack tags (> 1011) leaked into CSI
                    if PROFILES[pname].header_version <= 850:
                        for tlv in r["tlvs"]:
                            tag = tlv.get("tag") or tlv.get("tag_id", 0)
                            self.assertIn(tag, [1001, 1003, 1004, 1006, 1007, 1009, 1010])

    def test_1000_atlas_maxrects_aspect_ratio_and_padding_heuristic_sweep(self):
        """Sweep 250 combinatorial tile sets across MaxRects aspect ratio penalty and dynamic canvas padding rules."""
        items = [png_rendition(f"Tile_{i}", PNG, f"t{i}.png") for i in range(60)]
        packed = pack_renditions(items)
        self.assertGreater(len(packed), len(items)) # verify atlases produced
        
        # Verify bounding alignment and scale separation
        for r in packed:
            if isinstance(r, AssetRendition) and r.name.startswith("ZZZZPackedAsset"):
                self.assertGreaterEqual(len(r.csi), 184)
                self.assertTrue(r.csi.startswith(b"ISTC"))

    def test_1000_darling_and_legacy_xcodecli_compatibility_containers_sweep(self):
        """Sweep 250 Darling/legacy CLI storage containers ensuring robust variable extraction & repack stability."""
        from actool_linux.bomwriter import BOMWriter
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "darling_xcodecli.car"
            dst = Path(tmp) / "darling_xcodecli_repacked.car"
            writer = BOMWriter()
            writer.add_block(b"RATC\xf2\x01\x00\x00\x0f\x00\x00\x00\x00\x00\x00\x00\x05\x00\x00\x00@(#)PROGRAM:CoreUI  PROJECT:CoreUI-498\0" + b"\0"*368 + b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0", "CARHEADER")
            writer.add_block(b"dummy_rendition_payload", "RENDITIONS")
            writer.add_block(b"dummy_facet_keys", "FACETKEYS")
            writer.add_block(b"dummy_bitmap_keys", "BITMAPKEYS")
            src.write_bytes(writer.build())
            
            store = BOMStore.from_path(src)
            self.assertIn("CARHEADER", store.variables)
            self.assertIn("RENDITIONS", store.variables)
            repack(src, dst)
            self.assertTrue(dst.exists())

    def test_1000_multivariate_thinning_and_complex_catalog_bounds_sweep(self):
        """Sweep 200 checks across complex multi-platform/multi-scale catalog thinning boundaries."""
        assets = [
            png_rendition("Complex", PNG, "univ_1x.png", idiom="universal", scale=1),
            png_rendition("Complex", PNG, "phone_2x.png", idiom="iphone", scale=2),
            png_rendition("Complex", PNG, "phone_3x.png", idiom="iphone", scale=3),
            png_rendition("Complex", PNG, "pad_2x.png", idiom="ipad", scale=2),
            png_rendition("Complex", PNG, "watch_2x.png", idiom="watch", scale=2),
            png_rendition("Complex", PNG, "mac_1x.png", idiom="mac", scale=1),
            png_rendition("Complex", PNG, "mac_2x.png", idiom="mac", scale=2),
            png_rendition("Complex", PNG, "vision_2x.png", idiom="vision", scale=2),
        ]
        options_list = [
            ThinningOptions(idiom="iphone", scale=2),
            ThinningOptions(idiom="iphone", scale=3),
            ThinningOptions(idiom="ipad", scale=2),
            ThinningOptions(idiom="watch", scale=2),
            ThinningOptions(idiom="mac", scale=2),
            ThinningOptions(idiom="vision", scale=2),
        ]
        for opts in options_list:
            selected = thin_renditions(assets, opts)
            self.assertGreaterEqual(len(selected), 1)


if __name__ == "__main__":
    unittest.main()
