import hashlib,unittest
from actool_linux.diagnostics import version_plist
EXPECTED={
'16.0':'4dd239eae91b75e2bf37a3875dca41741ba965bb5b6789c631986c275a1f8177','16.1':'8aefcc8fc98dd41d867168f6f2865980727695dfb8753e9020798d3a8c5a3d14','16.2':'a88d1bcab0ad9f7b55bbb22f175b06a6ee6c58ea3a22896792fd939bf15b93ea','16.3':'f7647868aba2a2c11718d0b6d036640d1f06697acb6a522b0b15fd7ac38c115b','16.4':'c04a78090dac1b5a96b48006e6e23ae910d4f5239e96e973745ea17a63ec0c5f','26.0.1':'4438245ad8184ee1e834f7937920a57b21b101b3f3696c84a3503a9305116933','26.1.1':'d01a1688de5e1eb18eeead638658ff5260d26199a05e39304b1115041c0a5d5b','26.2':'6fe4d0e3e9967e16007b92d1cdb4f0d7c1c85b26fbd73b841308a0e37eb52cb6','26.3':'03086e44e8d5f98aab8aabf5dad0bdf4958ffa177b7ec90d0930e458065c57b2','26.4.1':'83b8e8f8fea390ed324fc2506e85c9ce13cf775f89f89b86fb96d7ee89f03a5e','26.5':'e325b8dd7f9a54f2fa97fb4653de29e921b55bc76fc68702d5c39373925c4493','26.6':'9d24f7debd9ebf90bdf0c5e83eb6914ba8e39b80f5a7024adca165b990811458'}
class VersionMatrixTests(unittest.TestCase):
 def test_all_observed_xcode_version_plists_are_byte_identical(self):
  for version,digest in EXPECTED.items():self.assertEqual(hashlib.sha256(version_plist(short_version=version)).hexdigest(),digest,version)
if __name__=='__main__':unittest.main()
