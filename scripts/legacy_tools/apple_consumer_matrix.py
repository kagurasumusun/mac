#!/usr/bin/env python3
"""Open one Linux-generated CAR with assetutil from every installed Xcode/SDK."""
from __future__ import annotations
import argparse, json, os
from pathlib import Path
import subprocess

SDKS = ("macosx", "iphoneos", "appletvos", "watchos", "xros")
def run(cmd, env):
    try:
        p=subprocess.run(cmd,env=env,text=True,capture_output=True,timeout=20)
        return p.returncode,p.stdout,p.stderr
    except subprocess.TimeoutExpired: return 124,"","timeout"
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("car",type=Path); ap.add_argument("--output",type=Path,default=Path("consumer-matrix.json")); ns=ap.parse_args()
    rows=[]
    for app in sorted(Path('/Applications').glob('Xcode*.app')):
        env=os.environ.copy(); env['DEVELOPER_DIR']=str(app/'Contents/Developer')
        vr,vo,ve=run(['xcodebuild','-version'],env)
        for sdk in SDKS:
            sr,so,se=run(['xcrun','--sdk',sdk,'--show-sdk-path'],env)
            row={'xcode_app':str(app),'xcode':vo,'sdk':sdk}
            if sr: row['status']='sdk-unavailable'; row['error']=se; rows.append(row); continue
            rc,out,err=run(['xcrun','--sdk',sdk,'assetutil','--info',str(ns.car.resolve())],env)
            row.update(exit_code=rc,stderr=err)
            if rc==0:
                try:
                    parsed=json.loads(out); row['status']='pass'; row['summary']=parsed[0]; row['assets']=parsed[1:]
                except json.JSONDecodeError: row['status']='invalid-json'
            else: row['status']='failed'
            rows.append(row)
    ns.output.write_text(json.dumps({'schema':1,'car':str(ns.car),'rows':rows},indent=2,sort_keys=True))
    from collections import Counter
    print(dict(Counter(r['status'] for r in rows))); print(ns.output)
    return 0 if any(r['status']=='pass' for r in rows) else 1
if __name__=='__main__': raise SystemExit(main())
