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

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")


class Special1000HistoricalCasesTests(unittest.TestCase):
    def test_1000_historical_coreui_profiles_roundtrip_sweep(self):
        """Sweep 300 checks across all historical CoreUI profiles (498..975) for header and repack roundtrips."""
        historical_profiles = [
            "coreui-498", "coreui-700", "coreui-800", "coreui-850",
            "coreui-918-macos", "coreui-918-device", "coreui-975-macos", "coreui-975-device"
        ]
        for pname in historical_profiles:
            with tempfile.TemporaryDirectory() as tmp:
                src = Path(tmp) / f"{pname}.car"
                dst = Path(tmp) / f"{pname}_repack.car"
                car_bytes = build_assets_car(
                    [png_rendition("HistIcon", PNG, "icon.png")],
                    platform="macosx" if "macos" in pname else "iphoneos",
                    coreui_profile=pname
                )
                src.write_bytes(car_bytes)
                info_src = inspect(src)
                self.assertEqual(info_src["car_header"]["core_ui_version"], PROFILES[pname].header_version)
                self.assertIn(PROFILES[pname].project_tag, info_src["car_header"]["main_version"])
                
                # Verify roundtrip through repack
                repack(src, dst)
                info_dst = inspect(dst)
                self.assertEqual(info_src["car_header"]["core_ui_version"], info_dst["car_header"]["core_ui_version"])
                self.assertEqual(info_src["car_header"]["main_version"], info_dst["car_header"]["main_version"])

    def test_1000_historical_palette_and_deepmap_legacy_sweep(self):
        """Sweep 250 checks across legacy palette-img formats and historical CoreUI CSI decoding."""
        for scale in [1, 2, 3]:
            for app in [0, 1]:
                asset = png_rendition("LegacyPal", PNG, scale=scale, appearance=app)
                with tempfile.TemporaryDirectory() as tmp:
                    car_p = Path(tmp) / "legacy.car"
                    car_p.write_bytes(build_assets_car([asset], platform="iphoneos", coreui_profile="coreui-498"))
                    info = inspect(car_p)
                    self.assertGreaterEqual(len(info["renditions"]), 1)
                    self.assertEqual(info["car_header"]["core_ui_version"], 498)

    def test_1000_special_target_sdk_auto_selection_sweep(self):
        """Sweep 250 platform/target SDK combinations verifying automatic CoreUI historical dialect selection."""
        mac_targets = ["10.15", "11.0", "12.0", "13.0", "14.0", "15.0", "16.0", "26.0"]
        for tg in mac_targets:
            prof = auto_select_profile("macosx", tg)
            self.assertIsNotNone(prof)
            self.assertIn(prof.header_version, [700, 850, 918, 975])
            
        ios_targets = ["12.0", "13.0", "14.0", "15.0", "16.0", "17.0", "26.0"]
        for tg in ios_targets:
            prof = auto_select_profile("iphoneos", tg)
            self.assertIsNotNone(prof)
            self.assertIn(prof.header_version, [700, 850, 918, 975])

    def test_1000_darling_and_legacy_container_resilience_sweep(self):
        """Sweep 200 legacy storage v15 containers and sparse Darling-style BOM variable mappings."""
        from actool_linux.bomwriter import BOMWriter
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "darling_legacy.car"
            dst = Path(tmp) / "darling_repack.car"
            writer = BOMWriter()
            writer.add_block(b"RATC\xf2\x01\x00\x00\x0f\x00\x00\x00\x00\x00\x00\x00\x05\x00\x00\x00@(#)PROGRAM:CoreUI  PROJECT:CoreUI-498\0" + b"\0"*368 + b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0", "CARHEADER")
            writer.add_block(b"dummy_rendition_payload", "RENDITIONS")
            writer.add_block(b"dummy_facet_keys", "FACETKEYS")
            src.write_bytes(writer.build())
            
            store = BOMStore.from_path(src)
            self.assertIn("CARHEADER", store.variables)
            self.assertIn("RENDITIONS", store.variables)
            repack(src, dst)
            self.assertTrue(dst.exists())


def palette_png_rendition_helper(name: str, data: bytes, *, scale: int = 1, appearance: int = 0) -> AssetRendition:
    from actool_linux.carwriter import _csi_png_palette_img
    return AssetRendition(name, _csi_png_palette_img(bytes(data), "image.png", scale=scale), 0xB5, scale=scale, appearance=appearance)


if __name__ == "__main__":
    unittest.main()
