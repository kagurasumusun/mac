import base64
import unittest

from actool_linux.bom import BOMStore
from actool_linux.car import CARFile
from actool_linux.carwriter import build_assets_car, png_rendition
from actool_linux.thinning import ThinningOptions, thin_renditions

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")


class ThinningTests(unittest.TestCase):
    def test_all_apple_platform_idiom_ids(self):
        expected = {"universal": 0, "iphone": 1, "ipad": 2, "tv": 3,
                    "car": 4, "watch": 5, "marketing": 6, "mac": 7,
                    "vision": 8}
        assets = [png_rendition("P", PNG, f"{name}.png", idiom=name)
                  for name in expected]
        car = CARFile(BOMStore(build_assets_car(assets)))
        observed = {r.csi.name[:-4]: r.key["kCRThemeIdiomName"] for r in car.renditions}
        self.assertEqual(observed, expected)

    def test_selector_keeps_universal_and_target(self):
        assets = [
            png_rendition("P", PNG, "any.png", idiom="universal", scale=2),
            png_rendition("P", PNG, "phone.png", idiom="iphone", scale=2),
            png_rendition("P", PNG, "pad.png", idiom="ipad", scale=2),
            png_rendition("P", PNG, "phone3.png", idiom="iphone", scale=3),
        ]
        options = ThinningOptions(idiom="iphone", scale=2)
        selected = thin_renditions(assets, options)
        self.assertEqual([x.csi[40:168].split(b"\0", 1)[0] for x in selected], [b"any.png", b"phone.png"])
        car = CARFile(BOMStore(build_assets_car(selected, thinning_arguments=options.metadata_arguments())))
        self.assertEqual(car.extended_metadata.thinning_arguments, "idiom 1 scale 2")

    def test_selector_localization_and_appearance_fallbacks(self):
        assets = [
            png_rendition("P", PNG, "base.png"),
            png_rendition("P", PNG, "ja.png", localization="ja"),
            png_rendition("P", PNG, "ar.png", localization="ar"),
            png_rendition("P", PNG, "dark.png", appearance="dark"),
        ]
        selected = thin_renditions(assets, ThinningOptions(localization="ja", appearance=1))
        names = {x.csi[40:168].split(b"\0", 1)[0] for x in selected}
        self.assertEqual(names, {b"base.png", b"ja.png", b"dark.png"})


    def test_thinning_subtype_and_scale_fallbacks(self):
        assets = [
            png_rendition("P", PNG, "univ.png", idiom="universal", scale=1),
            png_rendition("P", PNG, "watch.png", idiom="watch", scale=2),
            png_rendition("P", PNG, "watch3.png", idiom="watch", scale=3),
        ]
        selected = thin_renditions(assets, ThinningOptions(idiom="watch", scale=2))
        names = {x.csi[40:168].split(b"\0", 1)[0] for x in selected}
        self.assertEqual(names, {b"watch.png"})


if __name__ == "__main__":
    unittest.main()
