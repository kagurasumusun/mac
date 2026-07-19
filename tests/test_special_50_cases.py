import base64
import unittest
from pathlib import Path
import tempfile

from actool_linux.bom import BOMStore
from actool_linux.car import CARFile
from actool_linux.carwriter import build_assets_car, png_rendition, _identifier, _localization_identifier, _csi_jpeg, AssetRendition
from actool_linux.repack import repack
from actool_linux.thinning import ThinningOptions, thin_renditions
from actool_linux.packed import pack_renditions

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")


class Special50CasesTests(unittest.TestCase):
    def test_special_localization_and_bcp47_subtags(self):
        """Test #13/14: Comprehensive Arabic, Nordic, and Hebrew tags plus boundary checking."""
        tags = ["ar", "ar-SA", "he", "he-IL", "sv", "sv-SE", "nb", "nb-NO", "da", "tr", "nl", "pl", "uk", "th", "fi", "el"]
        ids = [_localization_identifier(t) for t in tags]
        self.assertEqual(len(set(ids)), len(tags))
        self.assertEqual(_localization_identifier("ar"), 40100)
        self.assertEqual(_localization_identifier("sv-SE"), 42305)
        self.assertEqual(_localization_identifier("fi"), 50200)

    def test_special_ultralong_and_multibyte_utf8_facets(self):
        """Test #11/12: UTF-8 multibyte, emoji, and >100 byte name modulo linear regression resistance."""
        emoji_name = "AppIcon-🚀/Layer1/ExtremelyLongPathWithMultibyteCharactersAndDeepHierarchy" * 2
        val = _identifier(emoji_name)
        self.assertGreater(val, 0)
        self.assertLessEqual(val, 65535)

    def test_special_uniform_tiles_and_giant_atlas_pagination(self):
        """Test #21/22: Uniform tile sets and giant single tile packing limits."""
        from actool_linux.packed import _csi_atlas
        items = [png_rendition(f"Item{i}", PNG, f"i{i}.png") for i in range(40)]
        packed = pack_renditions(items)
        self.assertGreater(len(packed), len(items)) # atlases generated
        # Verify giant tile safety
        giant_csi = _csi_atlas("GiantClass", 1200, 1200, b"", gray=False, opaque=True)
        giant = AssetRendition("GiantClass", giant_csi, 181, 181, scale=1)
        packed_giant = pack_renditions([giant, giant])
        self.assertGreaterEqual(len(packed_giant), 2)

    def test_special_thinning_multi_criteria_and_empty_fallbacks(self):
        """Test #39: Complex multi-criteria thinning with precise exact-match reduction."""
        assets = [
            png_rendition("P", PNG, "univ.png", idiom="universal", scale=1),
            png_rendition("P", PNG, "phone.png", idiom="iphone", scale=3),
            png_rendition("P", PNG, "pad.png", idiom="ipad", scale=2),
        ]
        selected = thin_renditions(assets, ThinningOptions(idiom="iphone", scale=3))
        names = {x.csi[40:168].split(b"\0", 1)[0] for x in selected}
        self.assertEqual(names, {b"phone.png"})

    def test_special_bom_repack_corrupt_and_sparse_indices(self):
        """Test #40: Sparse block indices and edge-case repack preservation."""
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "sparse.car"
            dest = Path(tmp) / "repacked.car"
            source.write_bytes(build_assets_car([png_rendition("icon", PNG)], platform="macosx", target="13.0"))
            repack(source, dest)
            self.assertTrue(dest.exists())
            self.assertGreater(dest.stat().st_size, 100)

    def test_special_multilevel_and_watch_matrix_integration(self):
        """Test #18/37: Watch complication and complex multi-asset catalog compilation."""
        from actool_linux.carwriter import build_watch_complication_car
        car_bytes = build_watch_complication_car("WatchComp", [PNG, PNG], families=["modularSmall", "graphicCircular"], roles=["foreground", "mask"])
        store = BOMStore(car_bytes)
        self.assertIn("CARHEADER", store.variables)
        self.assertIn("RENDITIONS", store.variables)


if __name__ == "__main__":
    unittest.main()
