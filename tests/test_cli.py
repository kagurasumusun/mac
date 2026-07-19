import unittest, io, sys
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from actool_linux.cli import parser, main

class CLITests(unittest.TestCase):
    def test_default_output_is_apple_xml_result_plist(self):
        self.assertEqual(parser().parse_args(['--compile','out']).output_format,'xml1')

    def test_major_deployment_and_thinning_options(self):
        n=parser().parse_args(['A.xcassets','--compile','out','--target-device','iphone','--filter-for-device-model','iPhone18,1','--filter-for-device-os-version','26.2','--product-type','com.apple.product-type.application','--development-region','ja','--compress-pngs','--enable-on-demand-resources','yes'])
        self.assertEqual(n.target_device,['iphone']);self.assertEqual(n.filter_for_device_model,'iPhone18,1');self.assertEqual(n.filter_for_device_os_version,'26.2');self.assertTrue(n.compress_pngs);self.assertEqual(n.enable_on_demand_resources,'yes')

    def test_all_target_devices_parse(self):
        n=parser().parse_args(['--compile','out',*[x for d in ('iphone','ipad','tv','watch','mac','vision') for x in ('--target-device',d)]])
        self.assertEqual(len(n.target_device),6)

    def test_no_arguments_returns_64_ex_usage(self):
        err = io.StringIO()
        with redirect_stderr(err):
            rc = main([])
        self.assertEqual(rc, 64)
        self.assertIn("Error: No arguments specified", err.getvalue())

    def test_compile_without_argument(self):
        out = io.BytesIO()
        with redirect_stdout(out):
            rc = main(["--compile"])
        self.assertEqual(rc, 1)
        self.assertIn(b"Unknown argument '--compile'", out.getvalue())

    def test_compile_without_inputs(self):
        out = io.BytesIO()
        with redirect_stdout(out):
            rc = main(["--compile", "out"])
        self.assertEqual(rc, 1)
        self.assertIn(b"Not enough arguments provided; where is the input document to operate on?", out.getvalue())

    def test_unknown_option(self):
        out = io.BytesIO()
        with redirect_stdout(out):
            rc = main(["--compile", "out", "--arena-invalid-option"])
        self.assertEqual(rc, 1)
        self.assertIn(b"Unknown argument '--arena-invalid-option'", out.getvalue())

    def test_human_readable_unknown_option(self):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = main(["--output-format", "human-readable-text", "--arena-invalid-option"])
        self.assertEqual(rc, 1)
        self.assertIn("/* com.apple.actool.errors */\nerror: Unknown argument '--arena-invalid-option'.", out.getvalue())

if __name__=='__main__':unittest.main()
