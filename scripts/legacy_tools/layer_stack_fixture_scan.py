#!/usr/bin/env python3
"""Locate observable CoreUI Layer Stack/Icon Layer Stack renditions in installed CARs."""
from __future__ import annotations
import argparse,concurrent.futures,json,subprocess
from pathlib import Path
def inspect(path):
 try:p=subprocess.run(['xcrun','--sdk','macosx','assetutil','--info',str(path)],capture_output=True,text=True,timeout=20)
 except subprocess.TimeoutExpired:return {'path':str(path),'status':'timeout'}
 if p.returncode:return {'path':str(path),'status':'failed'}
 try:rows=json.loads(p.stdout)
 except Exception:return {'path':str(path),'status':'invalid-json'}
 hits=[r for r in rows if isinstance(r,dict) and ('Layer Stack' in str(r.get('AssetType','')) or r.get('Layer') is not None)]
 return {'path':str(path),'status':'hit' if hits else 'clean','hits':hits[:100]}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=Path('layer-stack-fixtures.json'));ap.add_argument('--workers',type=int,default=10);ap.add_argument('--limit',type=int,default=600);ap.add_argument('roots',nargs='+',type=Path);a=ap.parse_args();paths=[]
 for root in a.roots:
  try:paths.extend(root.rglob('Assets.car'))
  except OSError:pass
 paths=sorted(set(paths))[:a.limit]
 with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:rows=list(pool.map(inspect,paths))
 a.output.write_text(json.dumps({'schema':1,'paths':len(paths),'rows':rows},indent=2)+'\n');print(json.dumps({'paths':len(paths),'hits':sum(r['status']=='hit' for r in rows)}))
if __name__=='__main__':main()
