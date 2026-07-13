import unittest
from actool_linux.cli import parser

class CLITests(unittest.TestCase):
 def test_default_output_is_apple_xml_result_plist(self):
  self.assertEqual(parser().parse_args(['--compile','out']).output_format,'xml1')
 def test_major_deployment_and_thinning_options(self):
  n=parser().parse_args(['A.xcassets','--compile','out','--target-device','iphone','--filter-for-device-model','iPhone18,1','--filter-for-device-os-version','26.2','--product-type','com.apple.product-type.application','--development-region','ja','--compress-pngs','--enable-on-demand-resources','yes'])
  self.assertEqual(n.target_device,['iphone']);self.assertEqual(n.filter_for_device_model,'iPhone18,1');self.assertEqual(n.filter_for_device_os_version,'26.2');self.assertTrue(n.compress_pngs);self.assertEqual(n.enable_on_demand_resources,'yes')
 def test_all_target_devices_parse(self):
  n=parser().parse_args(['--compile','out',*[x for d in ('iphone','ipad','tv','watch','mac','vision') for x in ('--target-device',d)]])
  self.assertEqual(len(n.target_device),6)

if __name__=='__main__':unittest.main()
