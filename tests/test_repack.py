from pathlib import Path
import tempfile
import unittest

from actool_linux.bom import BOMStore
from actool_linux.bomwriter import BOMWriter
from actool_linux.repack import repack


class RepackTests(unittest.TestCase):
    def test_complex_car_repack_roundtrip(self):
        import base64
        from actool_linux.carwriter import build_assets_car, png_rendition
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.car"
            dest = Path(tmp) / "dest.car"
            png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAQAAADYv8WvAAAAEklEQVR4nGPg/m/wiCH0aNUKABRABFncH0e8AAAAAElFTkSuQmCC")
            source.write_bytes(build_assets_car([png_rendition("icon", png)], platform="iphoneos", target="16.0"))
            repack(source, dest)
            before = BOMStore.from_path(source)
            after = BOMStore.from_path(dest)
            self.assertEqual(before.variables, after.variables)
            self.assertEqual(before.blocks.keys(), after.blocks.keys())
            for identifier in before.blocks:
                self.assertEqual(bytes(before.block(identifier)), bytes(after.block(identifier)))

    def test_preserves_ids_names_and_payloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "in.car"
            destination = Path(tmp) / "out.car"
            writer = BOMWriter()
            writer.add_block(b"one", "FIRST")
            writer.add_block(b"two")
            writer.add_block(b"three", "THIRD")
            source.write_bytes(writer.build())
            repack(source, destination)
            before = BOMStore.from_path(source)
            after = BOMStore.from_path(destination)
            self.assertEqual(before.variables, after.variables)
            self.assertEqual(before.blocks.keys(), after.blocks.keys())
            for identifier in before.blocks:
                self.assertEqual(bytes(before.block(identifier)), bytes(after.block(identifier)))


if __name__ == "__main__":
    unittest.main()
