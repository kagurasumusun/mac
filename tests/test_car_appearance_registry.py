import unittest

from actool_linux.bom import BOMStore
from actool_linux.car import CARFile


class CARAppearanceRegistryTests(unittest.TestCase):
    def test_firefox_appearance_registry(self):
        car = CARFile(BOMStore.from_path('fixtures/firefox-Assets.car'))
        registry = {entry.name: entry.value for entry in car.appearances}
        self.assertEqual(registry['NSAppearanceNameDarkAqua'], 1)
        self.assertEqual(registry['NSAppearanceNameAqua'], 8)
        self.assertEqual(registry['ISAppearanceTintable'], 10)
        self.assertEqual(registry['NSAppearanceNameSystem'], 0)

    def test_brandassets_target_tv_appearance_registry(self):
        car = CARFile(BOMStore.from_path('fixtures/brandassets-target-tv-Assets.car'))
        registry = {entry.name: entry.value for entry in car.appearances}
        self.assertEqual(registry, {'UIAppearanceAny': 0})


if __name__ == '__main__':
    unittest.main()
