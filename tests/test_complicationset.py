import base64
import json
from pathlib import Path
import tempfile
import unittest

from actool_linux.bom import BOMStore
from actool_linux.car import CARFile
from actool_linux.compiler import CompileOptions, compile_catalogs

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAQAAADYv8WvAAAAEklEQVR4nGPg/m/wiCH0aNUKABRABFncH0e8AAAAAElFTkSuQmCC")


class ComplicationSetTests(unittest.TestCase):
    def test_compiles_named_complication_set(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'Assets.xcassets'
            comp = root / 'Complication.complicationset'
            comp.mkdir(parents=True)
            (comp / 'Contents.json').write_text(json.dumps({
                'assets': [
                    {'idiom': 'watch', 'filename': 'Circular.imageset', 'role': 'circular'},
                    {'idiom': 'watch', 'filename': 'Modular.imageset', 'role': 'modular'},
                    {'idiom': 'watch', 'filename': 'Utilitarian.imageset', 'role': 'utilitarian'},
                ],
                'info': {'author': 'xcode', 'version': 1},
            }))
            for name in ('Circular', 'Modular', 'Utilitarian'):
                img = comp / f'{name}.imageset'
                img.mkdir()
                (img / 'image.png').write_bytes(PNG)
                (img / 'Contents.json').write_text(json.dumps({
                    'images': [{'idiom': 'watch', 'scale': '2x', 'filename': 'image.png'}],
                    'info': {'author': 'xcode', 'version': 1},
                }))
            out = Path(td) / 'out'; out.mkdir(parents=True, exist_ok=True)
            result = compile_catalogs([root], CompileOptions(out, platform='watchos', minimum_deployment_target='8.0', complication='Complication'))
            self.assertTrue(result.ok, [d.render() for d in result.diagnostics])
            car = CARFile(BOMStore.from_path(out / 'Assets.car'))
            self.assertEqual(sorted(r.csi.layout for r in car.renditions), [1003, 1003, 1003, 1004])
            self.assertEqual(sorted(f.name for f in car.facets), ['Complication/Circular', 'Complication/Modular', 'Complication/Utilitarian', 'ZZZZPackedAsset-2.1.0-gamut0'])


if __name__ == '__main__':
    unittest.main()
