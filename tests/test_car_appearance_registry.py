import os
import unittest

from actool_linux.bom import BOMStore
from actool_linux.car import CARFile


# The real-app fixture (`fixtures/firefox-Assets.car`) was removed for license
# hygiene on 2026-07-17. Its role is replaced by
# `fixtures/selfgen-rich-Assets.car`, compiled by Apple actool in CI from this
# project's own inputs (see fixtures/README.md). Skip until the self-made
# fixture is present locally, then pin the observed registry values.
RICH_FIXTURE = 'fixtures/selfgen-rich-Assets.car'


@unittest.skipUnless(os.path.exists(RICH_FIXTURE), 'self-made rich fixture is not generated yet')
class CARAppearanceRegistryTests(unittest.TestCase):
    def test_selfgen_rich_appearance_registry(self):
        car = CARFile(BOMStore.from_path(RICH_FIXTURE))
        registry = {entry.name: entry.value for entry in car.appearances}
        # Values pinned from the fixture generated on the GitHub-hosted macOS
        # runner (macOS 26.4 / Xcode 26.5 17F42); see fixtures/SELF-GENERATED.md.
        self.assertEqual(registry, {
            'NSAppearanceNameSystem': 0,
            'NSAppearanceNameDarkAqua': 1,
            'NSAppearanceNameAqua': 8,
        })

    def test_brandassets_target_tv_appearance_registry(self):
        car = CARFile(BOMStore.from_path('fixtures/brandassets-target-tv-Assets.car'))
        registry = {entry.name: entry.value for entry in car.appearances}
        self.assertEqual(registry, {'UIAppearanceAny': 0})


if __name__ == '__main__':
    unittest.main()
