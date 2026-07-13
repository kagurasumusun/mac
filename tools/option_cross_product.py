#!/usr/bin/env python3
"""Bounded actool option/diagnostic cross-product over every installed Xcode.

Records raw bytes (base64), hashes, parsed XML plists, normalized paths, exit code,
and ordering.  Work is parallel and each process has a hard timeout.
"""
from __future__ import annotations
import argparse,base64,concurrent.futures,hashlib,json,os,plistlib,shlex,subprocess,tempfile
from pathlib import Path
ACTOOL=shlex.split(os.environ.get("ACTOOL_COMMAND","xcrun actool"))
PLATFORMS={"macosx":"13.0","iphoneos":"15.0","iphonesimulator":"15.0","appletvos":"15.0","appletvsimulator":"15.0","watchos":"8.0","watchsimulator":"8.0","xros":"1.0","xrsimulator":"1.0"}
def replace(x,old):
 if isinstance(x,str):return x.replace(old,"<ROOT>")
 if isinstance(x,list):return [replace(v,old) for v in x]
 if isinstance(x,dict):return {k:replace(v,old) for k,v in x.items()}
 return x
def execute(job):
 app,name,command,root=job;env=os.environ.copy();env["DEVELOPER_DIR"]=str(app/"Contents/Developer")
 try:p=subprocess.run(command,env=env,capture_output=True,timeout=45);rc=p.returncode;out=p.stdout;err=p.stderr;timeout=False
 except subprocess.TimeoutExpired as e:rc=124;out=e.stdout or b"";err=e.stderr or b"";timeout=True
 try:parsed=plistlib.loads(out);normalized=replace(parsed,str(root))
 except Exception:parsed=normalized=None
 return {"xcode_app":str(app),"case":name,"command":command,"exit_code":rc,"timeout":timeout,"stdout_b64":base64.b64encode(out).decode(),"stderr_b64":base64.b64encode(err).decode(),"stdout_sha256":hashlib.sha256(out).hexdigest(),"stderr_sha256":hashlib.sha256(err).hexdigest(),"parsed":parsed,"normalized":normalized}
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--output",type=Path,default=Path("option-cross-product.json"));ap.add_argument("--workers",type=int,default=8);ap.add_argument("--xcode-app",action="append",type=Path);ns=ap.parse_args()
 with tempfile.TemporaryDirectory(prefix="actool-options-") as td:
  root=Path(td);empty=root/"Empty.xcassets";empty.mkdir();out=root/"out";out.mkdir();missing=root/"missing.xcassets"
  apps=ns.xcode_app or sorted(Path("/Applications").glob("Xcode*.app"));jobs=[]
  for app in apps:
   base=list(ACTOOL)
   fixed={
    "unknown-option":base+["--arena-invalid-option"],
    "no-input":base+["--compile",str(out),"--output-format","xml1"],
    "missing-input":base+["--compile",str(out),"--output-format","xml1",str(missing)],
    "version":base+["--version","--output-format","xml1"],
   }
   for name,cmd in fixed.items():jobs.append((app,name,cmd,root))
   for platform,target in PLATFORMS.items():
    prefix=base+["--compile",str(out),"--output-format","xml1","--platform",platform,"--minimum-deployment-target",target]
    variants={
     "baseline":[],"warnings-no":["--warnings","no"],"errors-no":["--errors","no"],"notices-no":["--notices","no"],
     "all-diagnostics-no":["--warnings","no","--errors","no","--notices","no"],
     "compress-no":["--compress-pngs","no"],"odr-yes":["--enable-on-demand-resources","yes"],
     "product-type":["--product-type","com.apple.product-type.application"],"development-region":["--development-region","ja"],
     "device-filter":["--filter-for-device-model","iPhone18,1","--filter-for-device-os-version","26.5"],
    }
    for variant,args in variants.items():jobs.append((app,f"{platform}:{variant}",prefix+args+[str(empty)],root))
  with concurrent.futures.ThreadPoolExecutor(max_workers=ns.workers) as pool:rows=list(pool.map(execute,jobs))
 ns.output.write_text(json.dumps({"schema":1,"rows":rows},indent=2)+"\n");counts={}
 for r in rows:counts[str(r["exit_code"])]=counts.get(str(r["exit_code"]),0)+1
 print(json.dumps({"rows":len(rows),"exit_codes":counts},sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
