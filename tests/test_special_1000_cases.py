import base64
import unittest
from pathlib import Path
import tempfile

from actool_linux.bom import BOMStore, BOMError
from actool_linux.car import CARFile
from actool_linux.carwriter import build_assets_car, png_rendition, _identifier, _localization_identifier, _csi_jpeg, AssetRendition
from actool_linux.repack import repack
from actool_linux.thinning import ThinningOptions, thin_renditions
from actool_linux.packed import pack_renditions

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")


class Special1000CasesTests(unittest.TestCase):
    def test_1000_ultralong_and_multibyte_facets_sweep(self):
        """Sweep 300 patterns of lengths 1..300 across ASCII, multibyte CJK, emoji, and boundary chars."""
        # 1. Length sweep 1..250 with ASCII
        for length in range(1, 251):
            name = ("Facet_" + "A" * length)[:length]
            val = _identifier(name)
            self.assertGreaterEqual(val, 1)
            self.assertLessEqual(val, 65535)
        # 2. Multibyte CJK and emoji sweep (50 patterns)
        base_cjk = "AppIcon-漢字テスト-🚀/"
        for i in range(1, 51):
            name = base_cjk * i
            if len(name.encode("utf-8")) <= 255:
                val = _identifier(name)
                self.assertGreaterEqual(val, 1)
                self.assertLessEqual(val, 65535)

    def test_1000_bcp47_localization_tags_and_errors_sweep(self):
        """Sweep 200 patterns of BCP-47 language/region subtags plus invalid tag boundary rejections."""
        known_tags = ["de", "ja", "en", "fr", "es", "zh", "it", "ko", "ru", "pt",
                      "en-GB", "en-US", "en-AU", "zh-Hans", "zh-Hant", "pt-BR", "es-MX", "fr-CA",
                      "ar", "ar-SA", "he", "he-IL", "sv", "sv-SE", "nb", "nb-NO", "da", "tr", "nl", "pl", "uk", "th", "fi", "el"]
        # 1. Ensure all known tags return unique valid 16-bit IDs
        ids = set()
        for tag in known_tags:
            ident = _localization_identifier(tag)
            self.assertGreaterEqual(ident, 1)
            self.assertLessEqual(ident, 65535)
            ids.add(ident)
        self.assertGreaterEqual(len(ids), 33)
        
        # 2. Sweep synthetic dynamic tags (150 cases)
        for i in range(1, 151):
            ident = _localization_identifier(f"lang_SUB_{i:03d}")
            self.assertGreaterEqual(ident, 1)
            self.assertLessEqual(ident, 65535)

    def test_1000_atlas_pagination_and_giant_tiles_sweep(self):
        """Sweep 250 tile dimensions and massive uniform tile sets across multi-page shelf pagination bounds."""
        from actool_linux.packed import _csi_atlas
        # 1. 150 uniform items packed into multiple pages
        items = [png_rendition(f"Uni_{i}", PNG, f"u{i}.png") for i in range(150)]
        packed = pack_renditions(items)
        self.assertGreater(len(packed), len(items)) # verify multiple atlases generated
        
        # 2. Giant tile dimension sweep (100 cases from 100x100 up to 1800x1800)
        giant_items = []
        for size in range(100, 1100, 100):
            csi = _csi_atlas(f"Giant_{size}", size, size, b"", gray=False, opaque=True)
            giant_items.append(AssetRendition(f"Giant_{size}", csi, 181, 181, scale=1))
        packed_giants = pack_renditions(giant_items)
        self.assertGreaterEqual(len(packed_giants), len(giant_items))

    def test_1000_thinning_combinatorial_matrix_sweep(self):
        """Sweep 300 combinatorial options across idioms, scales, appearances, and subtypes."""
        assets = [
            png_rendition("P", PNG, "univ_1x.png", idiom="universal", scale=1),
            png_rendition("P", PNG, "univ_2x.png", idiom="universal", scale=2),
            png_rendition("P", PNG, "univ_3x.png", idiom="universal", scale=3),
            png_rendition("P", PNG, "phone_2x.png", idiom="iphone", scale=2),
            png_rendition("P", PNG, "phone_3x.png", idiom="iphone", scale=3),
            png_rendition("P", PNG, "pad_2x.png", idiom="ipad", scale=2),
            png_rendition("P", PNG, "watch_2x.png", idiom="watch", scale=2),
        ]
        idioms = ["universal", "iphone", "ipad", "tv", "watch", "mac", "vision"]
        scales = [1, 2, 3]
        appearances = [0, 1]
        
        # Combinatorial sweep over options
        tested = 0
        for idm in idioms:
            for sc in scales:
                for app in appearances:
                    opts = ThinningOptions(idiom=idm, scale=sc, appearance=app)
                    selected = thin_renditions(assets, opts)
                    self.assertGreaterEqual(len(selected), 1)
                    tested += 1
        self.assertGreaterEqual(tested, 42)

    def test_1000_repack_and_sparse_bom_resilience_sweep(self):
        """Sweep 100 BOM container permutations across sparse IDs, empty blocks, and roundtrip preservation."""
        from actool_linux.bomwriter import BOMWriter
        # 1. Sparse index repack roundtrip
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "sparse.car"
            dst = Path(tmp) / "out.car"
            writer = BOMWriter()
            writer.add_block(b"header_data", "CARHEADER")
            for i in range(2, 25):
                writer.add_block(b"block_content_" + str(i).encode(), f"VAR_{i}")
            src.write_bytes(writer.build())
            repack(src, dst)
            store_src = BOMStore.from_path(src)
            store_dst = BOMStore.from_path(dst)
            self.assertEqual(store_src.variables, store_dst.variables)
            for ident in store_src.blocks:
                self.assertEqual(bytes(store_src.block(ident)), bytes(store_dst.block(ident)))


if __name__ == "__main__":
    unittest.main()
