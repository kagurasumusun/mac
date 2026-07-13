import json
import importlib.util
from pathlib import Path
import tempfile
import unittest
import base64
import plistlib

from actool_linux.bom import BOMStore
from actool_linux.car import CARFile
from actool_linux.model import load_catalog
from actool_linux.compiler import CompileOptions, compile_catalogs


class CatalogTests(unittest.TestCase):
    def test_reads_image_set_and_reports_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Assets.xcassets"
            item = root / "Logo.imageset"
            item.mkdir(parents=True)
            (item / "Contents.json").write_text(json.dumps({
                "images": [{"idiom": "universal", "filename": "logo.png", "scale": "1x"}],
                "info": {"author": "xcode", "version": 1},
            }))
            catalog = load_catalog(root)
            self.assertEqual([(a.name, a.kind) for a in catalog.assets], [("Logo", "image")])
            self.assertTrue(any("missing" in d.message for d in catalog.diagnostics))

    def test_empty_catalog_is_valid_and_does_not_emit_fake_car(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Assets.xcassets"
            root.mkdir()
            result = compile_catalogs([root], CompileOptions(Path(tmp) / "out"))
            self.assertTrue(result.ok)
            self.assertFalse((Path(tmp) / "out" / "Assets.car").exists())

    def test_compiles_all_assigned_multiscale_appearance_entries(self):
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Assets.xcassets"; item = root / "Logo.imageset"; item.mkdir(parents=True)
            for name in ("one.png", "two.png", "dark.png"): (item / name).write_bytes(png)
            (item / "Contents.json").write_text(json.dumps({"images": [
                {"filename":"one.png","idiom":"universal","scale":"1x"},
                {"filename":"two.png","idiom":"universal","scale":"2x"},
                {"filename":"dark.png","idiom":"universal","scale":"2x","appearances":[{"appearance":"luminosity","value":"dark"}]},
                {"idiom":"universal","scale":"3x"},
                {"filename":"one.png","idiom":"unsupported","scale":"1x"},
            ], "info":{"author":"xcode","version":1}}))
            output=Path(tmp)/"out";result=compile_catalogs([root],CompileOptions(output,platform="iphoneos",minimum_deployment_target="15.0"))
            self.assertTrue(result.ok)
            car=CARFile(BOMStore.from_path(output/"Assets.car"))
            self.assertEqual(len(car.renditions),3)
            self.assertEqual(sorted((r.key["kCRThemeScaleName"],r.key["kCRThemeAppearanceName"]) for r in car.renditions),[(1,0),(2,0),(2,1)])

    def test_compiles_multiple_assets_to_one_car(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Assets.xcassets"
            for name in ("A", "LongName"):
                item = root / f"{name}.dataset"
                item.mkdir(parents=True)
                (item / "data.bin").write_bytes(name.encode())
                (item / "Contents.json").write_text(json.dumps({
                    "data": [{"filename": "data.bin", "idiom": "universal", "universal-type-identifier": "public.data"}],
                    "info": {"author": "xcode", "version": 1},
                }))
            output = Path(tmp) / "out"
            result = compile_catalogs([root], CompileOptions(output))
            self.assertTrue(result.ok)
            car = CARFile(BOMStore.from_path(output / "Assets.car"))
            self.assertEqual([facet.name for facet in car.facets], ["A", "LongName"])
            self.assertEqual(len(car.renditions), 2)

    def test_compiles_single_color_set_to_car(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Assets.xcassets"
            item = root / "Brand.colorset"
            item.mkdir(parents=True)
            (item / "Contents.json").write_text(json.dumps({
                "colors": [{"idiom": "universal", "color": {
                    "color-space": "srgb",
                    "components": {"red": "1", "green": "0.5", "blue": "0.25", "alpha": "0.75"},
                }}],
                "info": {"author": "xcode", "version": 1},
            }))
            output = Path(tmp) / "out"
            result = compile_catalogs([root], CompileOptions(output))
            self.assertTrue(result.ok)
            car = CARFile(BOMStore.from_path(output / "Assets.car"))
            self.assertEqual(car.facets[0].name, "Brand")
            self.assertEqual(car.renditions[0].csi.layout, 1009)

    def test_compiles_single_jpeg_image_set_to_car(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Assets.xcassets"
            item = root / "Photo.imageset"
            item.mkdir(parents=True)
            jpeg = bytes.fromhex("ffd8ffc0000b080001000201011100ffd9")
            (item / "photo.jpg").write_bytes(jpeg)
            (item / "Contents.json").write_text(json.dumps({
                "images": [{"filename": "photo.jpg", "idiom": "universal", "scale": "1x"}],
                "info": {"author": "xcode", "version": 1},
            }))
            output = Path(tmp) / "out"
            result = compile_catalogs([root], CompileOptions(output))
            self.assertTrue(result.ok)
            car = CARFile(BOMStore.from_path(output / "Assets.car"))
            self.assertEqual(car.facets[0].name, "Photo")
            self.assertEqual(car.renditions[0].csi.pixel_format, "JPEG")

    @unittest.skipUnless(importlib.util.find_spec("lzfse") is not None, "optional lzfse dependency is unavailable")
    def test_compiles_app_icon_car_sidecars_and_partial_plist(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Assets.xcassets"
            item = root / "AppIcon.appiconset"
            item.mkdir(parents=True)
            png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGPgFtc0MLFiCA30rsqLAQAQXQMfVfFocgAAAABJRU5ErkJggg==")
            small = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
            (item / "icon.png").write_bytes(png); (item / "small.png").write_bytes(small)
            (item / "Contents.json").write_text(json.dumps({
                "images": [{"filename":"small.png","idiom":"iphone","size":"1x1"},{"filename": "icon.png", "idiom": "universal", "platform": "ios", "size": "2x2"}],
                "info": {"author": "xcode", "version": 1},
            }))
            output = Path(tmp) / "out"; partial = Path(tmp) / "partial.plist"
            result = compile_catalogs([root], CompileOptions(
                output, platform="iphoneos", minimum_deployment_target="15.0",
                app_icon="AppIcon", partial_info_plist=partial,
            ))
            self.assertTrue(result.ok, [d.render() for d in result.diagnostics])
            car = CARFile(BOMStore.from_path(output / "Assets.car"))
            self.assertEqual(len(car.renditions), 4)
            self.assertEqual(max(r.csi.width for r in car.renditions), 2)
            self.assertTrue((output / "AppIcon60x60@2x.png").is_file())
            self.assertTrue((output / "AppIcon76x76@2x~ipad.png").is_file())
            info = plistlib.loads(partial.read_bytes())
            self.assertEqual(info["CFBundleIcons"]["CFBundlePrimaryIcon"]["CFBundleIconFiles"], ["AppIcon60x60"])
            self.assertEqual(info["CFBundleIcons~ipad"]["CFBundlePrimaryIcon"]["CFBundleIconFiles"], ["AppIcon60x60", "AppIcon76x76"])

    def test_compiles_tv_image_stack_catalog(self):
        png=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"Assets.xcassets";stack=root/"Hero.imagestack";front=stack/"Front.imagestacklayer";back=stack/"Back.imagestacklayer"
            front.mkdir(parents=True);back.mkdir();
            (stack/"Contents.json").write_text(json.dumps({"layers":[{"filename":"Front.imagestacklayer"},{"filename":"Back.imagestacklayer"}],"info":{"author":"xcode","version":1}}))
            for d,n in ((front,"front.png"),(back,"back.png")):
                (d/n).write_bytes(png);(d/"Contents.json").write_text(json.dumps({"images":[{"idiom":"tv","scale":"1x","filename":n}],"info":{"author":"xcode","version":1}}))
            output=Path(tmp)/"out";result=compile_catalogs([root],CompileOptions(output,platform="appletvos",minimum_deployment_target="15.0"))
            self.assertTrue(result.ok,[d.render() for d in result.diagnostics]);car=CARFile(BOMStore.from_path(output/"Assets.car"))
            self.assertEqual(len(car.renditions),2);self.assertEqual(sorted(r.key["kCRThemeLayerName"] for r in car.renditions),[1,2]);self.assertTrue(all(r.key["kCRThemeIdiomName"]==3 for r in car.renditions))

    def test_compiles_launch_image_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Assets.xcassets"; item = root / "Launch.launchimage"
            item.mkdir(parents=True)
            png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGPgFtc0MLFiCA30rsqLAQAQXQMfVfFocgAAAABJRU5ErkJggg==")
            (item / "launch.png").write_bytes(png)
            (item / "Contents.json").write_text(json.dumps({
                "images": [{"filename":"launch.png","idiom":"iphone","scale":"2x","minimum-system-version":"7.0","orientation":"portrait","extent":"full-screen"}],
                "info": {"author":"xcode","version":1},
            }))
            output = Path(tmp) / "out"
            result = compile_catalogs([root], CompileOptions(output, platform="iphoneos", launch_image="Launch"))
            self.assertTrue(result.ok, [d.render() for d in result.diagnostics])
            self.assertEqual((output / "Launch-700@2x.png").read_bytes(), png)
            self.assertFalse((output / "Assets.car").exists())

    def test_compiles_single_data_set_to_car(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Assets.xcassets"
            item = root / "Blob.dataset"
            item.mkdir(parents=True)
            (item / "blob.txt").write_bytes(b"hello-linux-car")
            (item / "Contents.json").write_text(json.dumps({
                "data": [{
                    "filename": "blob.txt", "idiom": "universal",
                    "universal-type-identifier": "public.plain-text",
                }],
                "info": {"author": "xcode", "version": 1},
            }))
            output = Path(tmp) / "out"
            result = compile_catalogs([root], CompileOptions(output))
            self.assertTrue(result.ok)
            car = CARFile(BOMStore.from_path(output / "Assets.car"))
            self.assertEqual(car.facets[0].name, "Blob")
            self.assertEqual(car.renditions[0].csi.rendition_data[-15:], b"hello-linux-car")


if __name__ == "__main__":
    unittest.main()
