import unittest
from actool_linux.appicons import app_icon_entry_rank, app_icon_sidecar_specs

class AppIconSidecarTests(unittest.TestCase):
 def test_ios_compatibility_manifest(self):
  x=app_icon_sidecar_specs('iphoneos'); self.assertEqual(len(x),13)
  self.assertIn(('AppIcon60x60@3x.png',180,180),x)
  self.assertIn(('AppIcon83.5x83.5@2x~ipad.png',167,167),x)
 def test_watch_and_mac_manifests(self):
  self.assertEqual(len(app_icon_sidecar_specs('watchos')),9)
  self.assertEqual(len(app_icon_sidecar_specs('macosx')),10)
 def test_layered_platforms_have_no_flattened_sidecar(self):
  self.assertEqual(app_icon_sidecar_specs('appletvos'),())
  self.assertEqual(app_icon_sidecar_specs('xros'),())
 def test_entry_rank_rejects_watch_marketing_slots_in_compiler_path(self):
  self.assertIsNone(app_icon_entry_rank({'platform':'watchos','idiom':'watch-marketing'},'watchos'))
  self.assertIsNone(app_icon_entry_rank({'platform':'watchos','idiom':'watch-marketing','role':'notificationCenter'},'watchos'))
 def test_entry_rank_still_prefers_matching_non_watch_marketing_slot(self):
  ios=app_icon_entry_rank({'platform':'ios','idiom':'ios-marketing'},'iphoneos')
  generic=app_icon_entry_rank({'idiom':'universal'},'iphoneos')
  wrong=app_icon_entry_rank({'platform':'watchos','idiom':'watch-marketing'},'iphoneos')
  self.assertGreater(ios,generic)
  self.assertIsNone(wrong)

if __name__=='__main__': unittest.main()
