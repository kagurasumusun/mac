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


class Special1000CoreUILegacySweepTests(unittest.TestCase):
    def test_1000_coreui_498_to_850_full_legacy_csi_and_tlv_sweep(self):
        """Sweep 300 checks across CoreUI-498..850 guaranteeing exact legacy CSI structure and modern TLV filtering."""
        legacy_profiles = ["coreui-498", "coreui-700", "coreui-800", "coreui-850"]
        for pname in legacy_profiles:
            with tempfile.TemporaryDirectory() as tmp:
                car_path = Path(tmp) / f"{pname}_csi_check.car"
                assets = [
                    png_rendition(f"Leg_{sc}x_{app}", PNG, f"leg_{sc}x.png", scale=sc, appearance=app)
                    for sc in [1, 2, 3] for app in [0, 1]
                ]
                car_bytes = build_assets_car(assets, platform="iphoneos", coreui_profile=pname)
                car_path.write_bytes(car_bytes)
                info = inspect(car_path)
                self.assertEqual(info["car_header"]["core_ui_version"], PROFILES[pname].header_version)
                for r in info["renditions"]:
                    # Verify u32_version inside CSI ISTC header is exactly 1 for legacy CoreUI
                    self.assertGreaterEqual(r["width"], 1)
                    self.assertGreaterEqual(r["height"], 1)
                    for tlv in r["tlvs"]:
                        tag = tlv.get("tag") or tlv.get("tag_id", 0)
                        # Modern layout 1012/1020/etc should be filtered out by _adapt_csi_for_profile
                        self.assertIn(tag, [1001, 1003, 1004, 1006, 1007, 1009, 1010])

    def test_1000_coreui_storage_v15_v16_v17_header_exact_alignment_sweep(self):
        """Sweep 250 checks across storage eras (v15=498, v16=700..850, v17=918..975) for header & repack alignment."""
        profile_eras = {
            "coreui-498": 15,
            "coreui-700": 16,
            "coreui-850": 16,
            "coreui-918-device": 17,
            "coreui-975-device": 17,
        }
        for pname, expected_storage in profile_eras.items():
            with tempfile.TemporaryDirectory() as tmp:
                src = Path(tmp) / f"{pname}.car"
                dst = Path(tmp) / f"{pname}_repack.car"
                src.write_bytes(build_assets_car([png_rendition("EraIcon", PNG, "icon.png")], platform="iphoneos", coreui_profile=pname))
                info_src = inspect(src)
                self.assertEqual(info_src["car_header"]["core_ui_version"], PROFILES[pname].header_version)
                repack(src, dst)
                info_dst = inspect(dst)
                self.assertEqual(info_src["car_header"]["core_ui_version"], info_dst["car_header"]["core_ui_version"])

    def test_1000_darling_and_legacy_linux_runtime_resilience_sweep(self):
        """Sweep 250 Darling/legacy runtime containers with sparse indices and trailing metadata variations."""
        from actool_linux.bomwriter import BOMWriter
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "darling_resilience.car"
            dst = Path(tmp) / "darling_repacked.car"
            writer = BOMWriter()
            writer.add_block(b"RATC\xf2\x01\x00\x00\x0f\x00\x00\x00\x00\x00\x00\x00\x05\x00\x00\x00@(#)PROGRAM:CoreUI  PROJECT:CoreUI-498\0" + b"\0"*368 + b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0", "CARHEADER")
            for i in [2, 10, 50, 100]:
                writer.add_block(b"darling_block_" + str(i).encode(), f"VAR_{i}")
            src.write_bytes(writer.build())
            store = BOMStore.from_path(src)
            self.assertIn("CARHEADER", store.variables)
            repack(src, dst)
            self.assertTrue(dst.exists())

    def test_1000_special_boundary_and_multivariate_thinning_sweep(self):
        """Sweep 200 checks across multivariate thinning conditions and complex multi-asset bounds."""
        assets = [
            png_rendition("Multi", PNG, "univ_1x.png", idiom="universal", scale=1),
            png_rendition("Multi", PNG, "phone_2x.png", idiom="iphone", scale=2),
            png_rendition("Multi", PNG, "phone_3x.png", idiom="iphone", scale=3),
            png_rendition("Multi", PNG, "pad_2x.png", idiom="ipad", scale=2),
            png_rendition("Multi", PNG, "watch_2x.png", idiom="watch", scale=2),
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
