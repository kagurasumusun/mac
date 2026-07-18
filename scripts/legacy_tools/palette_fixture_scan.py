#!/usr/bin/env python3
"""Search installed Apple CARs for an observable legacy palette-img rendition."""
from __future__ import annotations
import argparse,concurrent.futures,json,subprocess
from pathlib import Path
def inspect(path):
 try:p=subprocess.run(['xcrun','--sdk','macosx','assetutil','--info',str(path)],capture_output=True,text=True,timeout=20)
 except subprocess.TimeoutExpired:return {'path':str(path),'status':'timeout'}
 if p.returncode:return {'path':str(path),'status':'failed','stderr':p.stderr[-1000:]}
 try:rows=json.loads(p.stdout)
 except Exception:return {'path':str(path),'status':'invalid-json'}
 hits=[r for r in rows if isinstance(r,dict) and str(r.get('Compression','')).lower()=='palette-img']
 return {'path':str(path),'status':'hit' if hits else 'clean','hits':hits}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=Path('palette-fixture-scan.json'));ap.add_argument('--workers',type=int,default=8);ap.add_argument('--limit',type=int,default=500);ap.add_argument('roots',nargs='*',type=Path);ns=ap.parse_args();roots=ns.roots or [Path('/System/Library'),Path('/Applications')]
 paths=[]
 for root in roots:
  try:paths.extend(root.rglob('Assets.car'))
  except OSError:pass
 paths=sorted(set(paths))[:ns.limit]
 with concurrent.futures.ThreadPoolExecutor(max_workers=ns.workers) as pool:rows=list(pool.map(inspect,paths))
 ns.output.write_text(json.dumps({'schema':1,'paths':len(paths),'rows':rows},indent=2)+'\n');counts={}
 for r in rows:counts[r['status']]=counts.get(r['status'],0)+1
 print(json.dumps(counts,sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
