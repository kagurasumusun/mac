import base64,json,plistlib,tempfile,unittest
from pathlib import Path
from actool_linux.compiler import CompileOptions,compile_catalogs
from actool_linux.diagnostics import result_plist,unknown_argument_plist,version_plist
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')
def info():return {'info':{'author':'xcode','version':1}}
class DiagnosticContractTests(unittest.TestCase):
 def test_malformed_is_notice_with_empty_results(self):
  with tempfile.TemporaryDirectory() as td:
   c=Path(td)/'A.xcassets';d=c/'Bad.imageset';d.mkdir(parents=True);(d/'Contents.json').write_text('{bad')
   r=compile_catalogs([c],CompileOptions((lambda q:(q.mkdir(parents=True,exist_ok=True),q)[1])(Path(td)/'out'),platform='iphoneos',minimum_deployment_target='15.0'))
   p=plistlib.loads(result_plist(r.diagnostics,r.outputs,include_compilation_results=True))
   self.assertEqual(p['com.apple.actool.compilation-results']['output-files'],[])
   self.assertEqual(p['com.apple.actool.notices'][0]['description'],'The Contents.json describing the "Bad.imageset" is not valid JSON.')
 def test_missing_and_unsupported_slots_are_ignored(self):
  for unsupported in (False,True):
   with tempfile.TemporaryDirectory() as td:
    c=Path(td)/'A.xcassets';d=c/'A.imageset';d.mkdir(parents=True)
    if unsupported:(d/'a.png').write_bytes(PNG)
    entry={'idiom':'invalid' if unsupported else 'universal','scale':'1x','filename':'a.png' if unsupported else 'gone.png'}
    (d/'Contents.json').write_text(json.dumps({'images':[entry],**info()}))
    r=compile_catalogs([c],CompileOptions((lambda q:(q.mkdir(parents=True,exist_ok=True),q)[1])(Path(td)/'out'),platform='iphoneos',minimum_deployment_target='15.0'))
    self.assertTrue(r.ok);self.assertEqual(r.outputs,[]);self.assertEqual(r.diagnostics,[])
 def test_duplicate_slot_compiles_deterministically(self):
  with tempfile.TemporaryDirectory() as td:
   c=Path(td)/'A.xcassets';d=c/'Dup.imageset';d.mkdir(parents=True)
   for n in ('a.png','b.png'):(d/n).write_bytes(PNG)
   (d/'Contents.json').write_text(json.dumps({'images':[{'idiom':'universal','scale':'1x','filename':'a.png'},{'idiom':'universal','scale':'1x','filename':'b.png'}],**info()}))
   r=compile_catalogs([c],CompileOptions((lambda q:(q.mkdir(parents=True,exist_ok=True),q)[1])(Path(td)/'out'),platform='iphoneos',minimum_deployment_target='15.0'))
   self.assertTrue(r.ok);self.assertTrue(((lambda q:(q.mkdir(parents=True,exist_ok=True),q)[1])(Path(td)/'out')/'Assets.car').is_file())
 def test_invalid_scale_is_silently_ignored(self):
  with tempfile.TemporaryDirectory() as td:
   c=Path(td)/'A.xcassets';d=c/'Odd.imageset';d.mkdir(parents=True);(d/'a.png').write_bytes(PNG)
   (d/'Contents.json').write_text(json.dumps({'images':[{'idiom':'universal','scale':'4x','filename':'a.png'}],**info()}))
   r=compile_catalogs([c],CompileOptions((lambda q:(q.mkdir(parents=True,exist_ok=True),q)[1])(Path(td)/'out'),platform='iphoneos',minimum_deployment_target='15.0'))
   self.assertTrue(r.ok);self.assertEqual(r.outputs,[]);self.assertEqual(r.diagnostics,[])
 def test_missing_requested_appicon_is_deferred_error(self):
  with tempfile.TemporaryDirectory() as td:
   c=Path(td)/'A.xcassets';d=c/'Plain.imageset';d.mkdir(parents=True);(d/'a.png').write_bytes(PNG)
   (d/'Contents.json').write_text(json.dumps({'images':[{'idiom':'universal','scale':'1x','filename':'a.png'}],**info()}))
   partial=Path(td)/'partial.plist'
   r=compile_catalogs([c],CompileOptions((lambda q:(q.mkdir(parents=True,exist_ok=True),q)[1])(Path(td)/'out'),platform='iphoneos',minimum_deployment_target='15.0',app_icon='NoSuchIcon',partial_info_plist=partial))
   self.assertFalse(r.ok);self.assertEqual([p.name for p in r.outputs],['Assets.car','partial.plist'])
   self.assertEqual(r.diagnostics[0].message,'None of the input catalogs contained a matching stickers icon set, app icon set, or icon stack named  "NoSuchIcon".')
 def test_root_array_is_apple_notice(self):
  with tempfile.TemporaryDirectory() as td:
   c=Path(td)/'A.xcassets';d=c/'Schema.imageset';d.mkdir(parents=True);(d/'Contents.json').write_text('[]')
   r=compile_catalogs([c],CompileOptions((lambda q:(q.mkdir(parents=True,exist_ok=True),q)[1])(Path(td)/'out'),platform='iphoneos',minimum_deployment_target='15.0'))
   self.assertTrue(r.ok);self.assertEqual(r.diagnostics[0].severity,'notice')
   self.assertEqual(r.diagnostics[0].message,'The Contents.json describing "Schema.imageset" must start with a top level dictionary.')
 def test_missing_icon_and_launch_are_ordered_errors(self):
  with tempfile.TemporaryDirectory() as td:
   c=Path(td)/'A.xcassets';d=c/'Plain.imageset';d.mkdir(parents=True);(d/'a.png').write_bytes(PNG)
   (d/'Contents.json').write_text(json.dumps({'images':[{'idiom':'universal','scale':'1x','filename':'a.png'}],**info()}));partial=Path(td)/'partial.plist'
   r=compile_catalogs([c],CompileOptions((lambda q:(q.mkdir(parents=True,exist_ok=True),q)[1])(Path(td)/'out'),platform='iphoneos',minimum_deployment_target='15.0',app_icon='NoIcon',launch_image='NoLaunch',partial_info_plist=partial))
   self.assertFalse(r.ok);self.assertEqual([p.name for p in r.outputs],['partial.plist','Assets.car'])
   self.assertEqual([d.severity for d in r.diagnostics],['error','error']);self.assertIn('NoIcon',r.diagnostics[0].message);self.assertIn('NoLaunch',r.diagnostics[1].message)
 def test_unknown_and_version_plists(self):
  self.assertIn(b"Unknown argument '--bad'.",unknown_argument_plist('--bad'))
  self.assertIn(b'Not enough arguments provided',unknown_argument_plist('--bad',include_missing_input=True))
  self.assertEqual(plistlib.loads(version_plist())['com.apple.actool.version']['bundle-version'],'24765')
if __name__=='__main__':unittest.main()
