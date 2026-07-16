import json
import importlib.util
from pathlib import Path
import tempfile
import unittest
import base64
import plistlib
import struct
import zlib

from actool_linux.bom import BOMStore
from actool_linux.car import CARFile
from actool_linux.model import load_catalog
from actool_linux.compiler import CompileOptions, compile_catalogs


def _solid_rgba_png(width: int, height: int, rgba: tuple[int, int, int, int]) -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    row = bytes(rgba) * width
    scanlines = b"".join(b"\0" + row for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(scanlines, 9))
        + chunk(b"IEND", b"")
    )


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

    def test_corrupt_png_preserves_failed_distill_output_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"Assets.xcassets";item=root/"Bad.imageset";item.mkdir(parents=True);(item/"bad.png").write_bytes(b"not png")
            (item/"Contents.json").write_text(json.dumps({"images":[{"idiom":"universal","scale":"1x","filename":"bad.png"}],"info":{"author":"xcode","version":1}}))
            output=Path(tmp)/"out";result=compile_catalogs([root],CompileOptions(output,platform="iphoneos",minimum_deployment_target="15.0"))
            self.assertFalse(result.ok);self.assertEqual(result.diagnostics[0].message,"Distill failed for unknown reasons.");self.assertTrue((output/"Assets.car").is_file())
            CARFile(BOMStore.from_path(output/"Assets.car"))

    def test_missing_color_components_default_to_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"Assets.xcassets";item=root/"Bad.colorset";item.mkdir(parents=True)
            (item/"Contents.json").write_text(json.dumps({"colors":[{"idiom":"universal","color":{"color-space":"srgb","components":{"red":"1","alpha":"1"}}}],"info":{"author":"xcode","version":1}}))
            result=compile_catalogs([root],CompileOptions(Path(tmp)/"out",platform="iphoneos",minimum_deployment_target="15.0"));self.assertTrue(result.ok)

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

    @unittest.skipUnless(importlib.util.find_spec("lzfse") is not None, "optional lzfse dependency is unavailable")
    def test_watch_marketing_icon_yields_only_partial_plist(self):
        watch_png = _solid_rgba_png(1024, 1024, (255, 0, 0, 255))
        ios_png = _solid_rgba_png(1024, 1024, (0, 255, 0, 255))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Assets.xcassets"
            item = root / "AppIcon.appiconset"
            item.mkdir(parents=True)
            (item / "watch.png").write_bytes(watch_png)
            (item / "ios.png").write_bytes(ios_png)
            (item / "Contents.json").write_text(json.dumps({
                "images": [
                    {"filename": "ios.png", "platform": "ios", "idiom": "ios-marketing", "size": "1024x1024"},
                    {"filename": "watch.png", "platform": "watchos", "idiom": "watch-marketing", "role": "notificationCenter", "size": "1024x1024"},
                ],
                "info": {"author": "xcode", "version": 1},
            }))
            output = Path(tmp) / "out"; partial = Path(tmp) / "partial.plist"
            result = compile_catalogs([root], CompileOptions(
                output, platform="watchos", minimum_deployment_target="11.0",
                app_icon="AppIcon", partial_info_plist=partial,
            ))
            self.assertTrue(result.ok, [d.render() for d in result.diagnostics])
            self.assertEqual(sorted(p.name for p in result.outputs), ["partial.plist"])
            self.assertFalse((output / "Assets.car").exists())
            self.assertFalse(any(output.glob("AppIcon*.png")))
            self.assertEqual(plistlib.loads(partial.read_bytes()), {})

    def test_compiles_spriteatlas_catalog(self):
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAQAAADYv8WvAAAAEklEQVR4nGPg/m/wiCH0aNUKABRABFncH0e8AAAAAElFTkSuQmCC")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Assets.xcassets"
            atlas = root / "Particle Sprite Atlas.spriteatlas"
            bokeh = atlas / "bokeh.imageset"
            spark = atlas / "spark.imageset"
            bokeh.mkdir(parents=True)
            spark.mkdir()
            (atlas / "Contents.json").write_text(json.dumps({"info":{"author":"xcode","version":1}}))
            for directory, stem in ((bokeh, "bokeh"), (spark, "spark")):
                (directory / f"{stem}.png").write_bytes(png)
                (directory / "Contents.json").write_text(json.dumps({
                    "images": [{"filename": f"{stem}.png", "idiom": "universal", "scale": "1x"}],
                    "info": {"author": "xcode", "version": 1},
                }))
            output = Path(tmp) / "out"
            result = compile_catalogs([root], CompileOptions(output, platform="macosx", minimum_deployment_target="13.0"))
            self.assertTrue(result.ok, [d.render() for d in result.diagnostics])
            car = CARFile(BOMStore.from_path(output / "Assets.car"))
            self.assertEqual(sorted(r.csi.layout for r in car.renditions), [1003, 1003, 1004, 1005])
            self.assertEqual(sorted(f.name for f in car.facets), ["Particle Sprite Atlas", "bokeh", "spark"])

    def test_compiles_tv_image_stack_catalog(self):
        # Apple oracle (probe2/v1): standalone stack whose layers declare
        # idiom "tv" has NO applicable content -> document error, no CAR, rc 0.
        png=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"Assets.xcassets";stack=root/"Hero.imagestack";front=stack/"Front.imagestacklayer";back=stack/"Back.imagestacklayer"
            front.mkdir(parents=True);back.mkdir();
            (stack/"Contents.json").write_text(json.dumps({"layers":[{"filename":"Front.imagestacklayer"},{"filename":"Back.imagestacklayer"}],"info":{"author":"xcode","version":1}}))
            for d,n in ((front,"front.png"),(back,"back.png")):
                (d/n).write_bytes(png);(d/"Contents.json").write_text(json.dumps({"images":[{"idiom":"tv","scale":"1x","filename":n}],"info":{"author":"xcode","version":1}}))
            output=Path(tmp)/"out";result=compile_catalogs([root],CompileOptions(output,platform="appletvos",minimum_deployment_target="15.0"))
            doc=[d for d in result.diagnostics if d.document]
            self.assertEqual(len(doc),1)
            self.assertIn('The image stack "Hero" must have at least 2 layers with applicable content',doc[0].message)
            self.assertIn("none have applicable content",doc[0].message)
            self.assertFalse((output/"Assets.car").exists())

    def test_compiles_tv_image_stack_universal_aggregate(self):
        # Apple oracle (probe2/v3): standalone stack with universal idiom
        # emits the ImageStack aggregate (layout 1002 + flattened + radiosity).
        import struct, zlib, binascii
        def chunk(kind, payload):
            return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", binascii.crc32(kind + payload) & 0xFFFFFFFF)
        def png_rgba(w, h, rgba):
            raw = (b"\x00" + bytes(rgba) * w) * h
            return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"Assets.xcassets";stack=root/"Hero.imagestack";front=stack/"Front.imagestacklayer";back=stack/"Back.imagestacklayer"
            front.mkdir(parents=True);back.mkdir()
            (stack/"Contents.json").write_text(json.dumps({"layers":[{"filename":"Front.imagestacklayer"},{"filename":"Back.imagestacklayer"}],"info":{"author":"xcode","version":1}}))
            for d,n,c in ((front,"front.png",(250,10,10,255)),(back,"back.png",(10,10,250,255))):
                (d/n).write_bytes(png_rgba(4,4,c));(d/"Contents.json").write_text(json.dumps({"images":[{"idiom":"universal","scale":"1x","filename":n}],"info":{"author":"xcode","version":1}}))
            output=Path(tmp)/"out";result=compile_catalogs([root],CompileOptions(output,platform="appletvos",minimum_deployment_target="15.0"))
            self.assertTrue(result.ok,[d.render() for d in result.diagnostics]);car=CARFile(BOMStore.from_path(output/"Assets.car"))
            layouts=sorted(r.csi.layout for r in car.renditions)
            self.assertEqual(layouts,[0,0,12,12,1002])
            parts=sorted(r.key["kCRThemePartName"] for r in car.renditions)
            self.assertEqual(parts,[181,181,181,208,209])
            self.assertTrue(all(r.key["kCRThemeIdiomName"]==0 for r in car.renditions))
            root_rend=next(r for r in car.renditions if r.csi.layout==1002)
            self.assertEqual(root_rend.csi.pixel_format,"DATA")
            self.assertEqual(root_rend.csi.rendition_data,b"DWAR"+b"\0"*8)
            self.assertEqual([t.tag for t in root_rend.csi.tlvs],[1012,1020,1021,1004,1005,1006])

    def test_compiles_vision_image_stack_with_explicit_depths(self):
        png=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"Assets.xcassets";stack=root/"Vision.imagestack";front=stack/"Front.imagestacklayer";back=stack/"Back.imagestacklayer"
            front.mkdir(parents=True);back.mkdir()
            (stack/"Contents.json").write_text(json.dumps({"layers":[
                {"filename":"Front.imagestacklayer","depth":10},
                {"filename":"Back.imagestacklayer","depth":"20"}
            ],"info":{"author":"xcode","version":1}}))
            for d,n in ((front,"front.png"),(back,"back.png")):
                (d/n).write_bytes(png);(d/"Contents.json").write_text(json.dumps({"images":[{"idiom":"vision","scale":"1x","filename":n}],"info":{"author":"xcode","version":1}}))
            output=Path(tmp)/"out";result=compile_catalogs([root],CompileOptions(output,platform="xros",minimum_deployment_target="1.0"))
            self.assertTrue(result.ok,[d.render() for d in result.diagnostics]);car=CARFile(BOMStore.from_path(output/"Assets.car"))
            self.assertEqual([(r.key["kCRThemeLayerName"],r.key["kCRThemeDimension2Name"]) for r in car.renditions],[(1,10),(2,20)])

    def test_compiles_solid_image_stack_with_nested_content_imageset(self):
        png=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"Assets.xcassets";stack=root/"AppIcon.solidimagestack";front=stack/"Front.solidimagestacklayer";middle=stack/"Middle.solidimagestacklayer";back=stack/"Back.solidimagestacklayer"
            for d in (front,middle,back): (d/"Content.imageset").mkdir(parents=True)
            (stack/"Contents.json").write_text(json.dumps({"layers":[{"filename":"Front.solidimagestacklayer"},{"filename":"Middle.solidimagestacklayer"},{"filename":"Back.solidimagestacklayer"}],"info":{"author":"xcode","version":1}}))
            for d in (front,middle,back):
                (d/"Contents.json").write_text(json.dumps({"info":{"author":"xcode","version":1}}))
                (d/"Content.imageset"/"content.png").write_bytes(png)
                (d/"Content.imageset"/"Contents.json").write_text(json.dumps({"images":[{"idiom":"vision","scale":"2x","filename":"content.png"}],"info":{"author":"xcode","version":1}}))
            output=Path(tmp)/"out";result=compile_catalogs([root],CompileOptions(output,platform="xros",minimum_deployment_target="1.0"))
            self.assertTrue(result.ok,[d.render() for d in result.diagnostics]);car=CARFile(BOMStore.from_path(output/"Assets.car"))
            self.assertEqual(len(car.renditions),3)
            self.assertTrue(all(r.key["kCRThemeIdiomName"]==8 for r in car.renditions))

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
