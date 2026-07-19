import plistlib,unittest
from pathlib import Path
from actool_linux.diagnostics import result_plist
from actool_linux.model import Diagnostic

class DiagnosticsTests(unittest.TestCase):
 def test_actool_result_plist_shape(self):
  raw=result_plist([Diagnostic('error','bad input',Path('/tmp/A.xcassets')),Diagnostic('warning','missing slot')],[Path('/tmp/out/Assets.car')])
  x=plistlib.loads(raw)
  self.assertEqual(x['com.apple.actool.errors'][0],{'description':'bad input','source-path':'/tmp/A.xcassets'})
  self.assertEqual(x['com.apple.actool.warnings'][0]['description'],'missing slot')
  self.assertEqual(x['com.apple.actool.compilation-results']['output-files'],['/tmp/out/Assets.car'])
 def test_deterministic_bytes(self):
  d=[Diagnostic('notice','hello')];self.assertEqual(result_plist(d,[]),result_plist(d,[]))
 def test_xcode_26_5_version_shape(self):
  from actool_linux.diagnostics import version_plist
  self.assertEqual(plistlib.loads(version_plist()),{'com.apple.actool.version':{'bundle-version':'24765','short-bundle-version':'26.5'}})
 def test_missing_input_notice_contract(self):
  from actool_linux.compiler import CompileOptions,compile_catalogs
  r=compile_catalogs([Path('/tmp/does-not-exist.xcassets')],CompileOptions(Path('/tmp/o')))
  self.assertEqual([(d.severity,d.message,d.failure_reason) for d in r.diagnostics],[
   ('notice','Failed to read file attributes for "/tmp/does-not-exist.xcassets"','No such file or directory'),
   ('notice','Compiling requires passing "--minimum-deployment-target [value]".',None),
   ('notice','Compiling requires passing "--platform [platform-name]".',None)])
 def test_no_input_contract_text(self):
  from actool_linux.compiler import CompileOptions,compile_catalogs
  import tempfile
  with tempfile.TemporaryDirectory() as tmp:
   r=compile_catalogs([],CompileOptions(Path(tmp)/'out'))
   self.assertEqual(r.diagnostics[0].message,'Not enough arguments provided; where is the input document to operate on?')

if __name__=='__main__':unittest.main()
