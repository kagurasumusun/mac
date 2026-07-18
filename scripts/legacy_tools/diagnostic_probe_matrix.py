#!/usr/bin/env python3
"""Capture raw and path-normalized actool diagnostic contracts.

This is an observable-I/O probe: it stores commands, raw stdout/stderr, hashes,
parsed plists, and a second deterministic plist with the probe root replaced by
<ROOT>.  No Apple implementation code is read or redistributed.
"""
from __future__ import annotations
import argparse,base64,hashlib,json,os,plistlib,shlex,shutil,subprocess,tempfile
from pathlib import Path

ACTOOL=shlex.split(os.environ.get("ACTOOL_COMMAND","xcrun actool"))
PNG=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
def _replace(value,old,new):
 if isinstance(value,str):return value.replace(old,new)
 if isinstance(value,list):return [_replace(x,old,new) for x in value]
 if isinstance(value,dict):return {k:_replace(v,old,new) for k,v in value.items()}
 return value
def capture(name,cmd,root):
 p=subprocess.run(cmd,capture_output=True)
 try: parsed=plistlib.loads(p.stdout)
 except Exception: parsed=None
 normalized=_replace(parsed,str(root),"<ROOT>") if parsed is not None else None
 normalized_bytes=plistlib.dumps(normalized,fmt=plistlib.FMT_XML,sort_keys=False) if normalized is not None else b""
 return {"name":name,"command":cmd,"exit_code":p.returncode,
  "stdout_b64":base64.b64encode(p.stdout).decode(),"stderr_b64":base64.b64encode(p.stderr).decode(),
  "stdout_sha256":hashlib.sha256(p.stdout).hexdigest(),"stderr_sha256":hashlib.sha256(p.stderr).hexdigest(),
  "parsed":parsed,"normalized":normalized,"normalized_stdout_sha256":hashlib.sha256(normalized_bytes).hexdigest()}
def run(name,cat,root,args=()):
 out=root/(name+"-out");out.mkdir(exist_ok=True)
 cmd=[*ACTOOL,"--compile",str(out),"--platform","iphoneos","--minimum-deployment-target","15.0",*args,str(cat)]
 return capture(name,cmd,root)
def info():return {"info":{"author":"xcode","version":1}}
def make_set(root,catalog,set_name,entries,*,body=None):
 d=root/catalog/set_name;d.mkdir(parents=True,exist_ok=True)
 data=body if body is not None else {"images":entries,**info()}
 (d/"Contents.json").write_text(json.dumps(data))
 return root/catalog,d
def probe(root):
 rows=[]
 c=root/"malformed.xcassets";d=c/"Bad.imageset";d.mkdir(parents=True);(d/"Contents.json").write_text("{bad");rows.append(run("malformed",c,root))
 c,d=make_set(root,"missing.xcassets","Missing.imageset",[{"idiom":"universal","scale":"1x","filename":"gone.png"}]);rows.append(run("missing-image",c,root))
 c,d=make_set(root,"duplicate.xcassets","Dup.imageset",[{"idiom":"universal","scale":"1x","filename":"a.png"},{"idiom":"universal","scale":"1x","filename":"b.png"}]);(d/"a.png").write_bytes(PNG);(d/"b.png").write_bytes(PNG);rows.append(run("duplicate-slot",c,root))
 c,d=make_set(root,"idiom.xcassets","Odd.imageset",[{"idiom":"arena-invalid","scale":"1x","filename":"a.png"}]);(d/"a.png").write_bytes(PNG);rows.append(run("unsupported-idiom",c,root))
 # Invalid slot attributes are useful warning/notice ordering oracles.
 for label,entry in (("invalid-scale",{"idiom":"universal","scale":"4x","filename":"a.png"}),("invalid-size",{"idiom":"universal","scale":"1x","size":"bogus","filename":"a.png"})):
  c,d=make_set(root,label+".xcassets","Odd.imageset",[entry]);(d/"a.png").write_bytes(PNG);rows.append(run(label,c,root))
 # Two malformed sets reveal deterministic diagnostic ordering.
 c=root/"ordering.xcassets"
 for n in ("Z.imageset","A.imageset"):
  d=c/n;d.mkdir(parents=True);(d/"Contents.json").write_text("{bad")
 rows.append(run("malformed-ordering",c,root))
 # Additional malformed-schema and warning-order cases (schema 3 probes).
 for label,body in (
  ("root-array",[]),
  ("images-not-array",{"images":"bad",**info()}),
  ("entry-not-object",{"images":[1],**info()}),
  ("missing-info",{"images":[{"idiom":"universal","scale":"1x","filename":"a.png"}]}),
 ):
  c,d=make_set(root,label+".xcassets","Schema.imageset",[],body=body)
  if label=="missing-info":(d/"a.png").write_bytes(PNG)
  rows.append(run(label,c,root))
 # Incorrect AppIcon dimensions and empty role set.
 c,d=make_set(root,"appicon.xcassets","AppIcon.appiconset",[{"idiom":"universal","platform":"ios","size":"1024x1024","filename":"tiny.png"}]);(d/"tiny.png").write_bytes(PNG)
 rows.append(run("appicon-partial-required",c,root,("--app-icon","AppIcon")))
 rows.append(run("appicon-dimensions",c,root,("--app-icon","AppIcon","--output-partial-info-plist",str(root/"partial.plist"))))
 c,d=make_set(root,"appicon-empty.xcassets","AppIcon.appiconset",[]);rows.append(run("appicon-role-shortage",c,root,("--app-icon","AppIcon","--output-partial-info-plist",str(root/"empty-partial.plist"))))
 # Requested-but-absent role warnings.
 c,d=make_set(root,"plain.xcassets","Plain.imageset",[{"idiom":"universal","scale":"1x","filename":"a.png"}]);(d/"a.png").write_bytes(PNG)
 rows.append(run("missing-appicon-name",c,root,("--app-icon","NoSuchIcon","--output-partial-info-plist",str(root/"missing-icon-partial.plist"))))
 rows.append(run("missing-icon-launch-order",c,root,("--app-icon","NoSuchIcon","--launch-image","NoSuchLaunch","--output-partial-info-plist",str(root/"missing-both-partial.plist"))))
 rows.append(capture("unknown-option",[*ACTOOL,"--arena-invalid-option"],root))
 rows.append(capture("unknown-option-after-compile",[*ACTOOL,"--compile",str(root/"unknown-out"),"--arena-invalid-option",str(c)],root))
 return {"schema":3,"probe_root":str(root),"rows":rows}
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--root",type=Path);ap.add_argument("--output",type=Path);a=ap.parse_args()
 owned=a.root is None;root=a.root or Path(tempfile.mkdtemp(prefix="actool-diagnostic-"))
 if root.exists() and not owned:shutil.rmtree(root)
 root.mkdir(parents=True,exist_ok=True)
 try:
  result=probe(root);text=json.dumps(result,indent=2)+"\n"
  if a.output:a.output.write_text(text)
  else:print(text,end="")
 finally:
  if owned:shutil.rmtree(root)
if __name__=="__main__":main()
