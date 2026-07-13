#!/usr/bin/env python3
"""Capture Apple actool contracts for corrupt payloads and malformed entries."""
from __future__ import annotations
import base64,hashlib,json,os,plistlib,shlex,shutil,subprocess
from pathlib import Path
ACTOOL=shlex.split(os.environ.get('ACTOOL_COMMAND','xcrun actool'))
def cap(name,cat,root,args=()):
 out=root/(name+'-out');out.mkdir();cmd=[*ACTOOL,'--compile',str(out),'--platform','iphoneos','--minimum-deployment-target','15.0',*args,str(cat)];p=subprocess.run(cmd,capture_output=True)
 try:parsed=plistlib.loads(p.stdout)
 except Exception:parsed=None
 return {'name':name,'command':cmd,'exit_code':p.returncode,'stdout_b64':base64.b64encode(p.stdout).decode(),'stderr_b64':base64.b64encode(p.stderr).decode(),'stdout_sha256':hashlib.sha256(p.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(p.stderr).hexdigest(),'parsed':parsed}
def info():return {'info':{'author':'xcode','version':1}}
def main():
 root=Path('/tmp/actool-corrupt');shutil.rmtree(root,ignore_errors=True);root.mkdir();rows=[]
 def asset(cat,name,suffix,key,entries):
  d=root/cat/(name+suffix);d.mkdir(parents=True);(d/'Contents.json').write_text(json.dumps({key:entries,**info()}));return root/cat,d
 for label,data in [('corrupt-png',b'not png'),('truncated-png',b'\x89PNG\r\n\x1a\n')]:
  c,d=asset(label+'.xcassets','Bad','.imageset','images',[{'idiom':'universal','scale':'1x','filename':'bad.png'}]);(d/'bad.png').write_bytes(data);rows.append(cap(label,c,root))
 c,d=asset('invalid-color.xcassets','Bad','.colorset','colors',[{'idiom':'universal','color':{'color-space':'srgb','components':{'red':'2','green':'0','blue':'0','alpha':'1'}}}]);rows.append(cap('invalid-color-range',c,root))
 c,d=asset('missing-color.xcassets','Bad','.colorset','colors',[{'idiom':'universal','color':{'color-space':'srgb','components':{'red':'1','alpha':'1'}}}]);rows.append(cap('missing-color-components',c,root))
 c,d=asset('bad-uti.xcassets','Blob','.dataset','data',[{'idiom':'universal','filename':'x.bin','universal-type-identifier':'arena.invalid uti'}]);(d/'x.bin').write_bytes(b'x');rows.append(cap('invalid-uti',c,root))
 c=root/'invalid-utf8.xcassets';d=c/'Bad.imageset';d.mkdir(parents=True);(d/'Contents.json').write_bytes(b'\xff\xfe{');rows.append(cap('invalid-utf8',c,root))
 c,d=asset('bad-appicon-size.xcassets','AppIcon','.appiconset','images',[{'idiom':'universal','platform':'ios','size':'bogus','filename':'bad.png'}]);(d/'bad.png').write_bytes(b'not png');rows.append(cap('appicon-invalid-size',c,root,('--app-icon','AppIcon','--output-partial-info-plist',str(root/'partial.plist'))))
 # Two catalogs with the same named image asset.
 cats=[]
 for i in (1,2):
  c,d=asset(f'dup{i}.xcassets','Same','.imageset','images',[{'idiom':'universal','scale':'1x','filename':'a.png'}]);(d/'a.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='));cats.append(c)
 out=root/'duplicate-name-out';out.mkdir();cmd=[*ACTOOL,'--compile',str(out),'--platform','iphoneos','--minimum-deployment-target','15.0',*[str(c) for c in cats]];p=subprocess.run(cmd,capture_output=True)
 try:parsed=plistlib.loads(p.stdout)
 except Exception:parsed=None
 rows.append({'name':'duplicate-name-across-catalogs','command':cmd,'exit_code':p.returncode,'stdout_b64':base64.b64encode(p.stdout).decode(),'stderr_b64':base64.b64encode(p.stderr).decode(),'stdout_sha256':hashlib.sha256(p.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(p.stderr).hexdigest(),'parsed':parsed})
 print(json.dumps({'schema':1,'rows':rows},indent=2))
if __name__=='__main__':main()
