#!/usr/bin/env python3
"""Probe Xcode's observable CBCK/deepmap adoption around raw-byte boundaries."""
from __future__ import annotations
import argparse,binascii,concurrent.futures,json,os,plistlib,struct,subprocess,tempfile,zlib
from pathlib import Path
CASES=((511,511),(512,512),(513,513),(1024,340),(1024,341),(1024,342),(1024,682),(2048,171),(2048,172))
PLATFORMS={"iphoneos":"15.0","appletvos":"15.0","watchos":"8.0","xros":"1.0","macosx":"13.0"}
def chunk(k,d):return struct.pack('>I',len(d))+k+d+struct.pack('>I',binascii.crc32(k+d)&0xffffffff)
def png(w,h):
 # Deterministic opaque RGBA with enough variation to prevent constant-image special cases.
 rows=bytearray()
 for y in range(h):
  rows.append(0)
  for x in range(w):rows.extend(((x*17+y*3)&255,(x*5+y*11)&255,(x^y)&255,255))
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(bytes(rows),6))+chunk(b'IEND',b'')
def run(args,env,timeout=90):
 try:p=subprocess.run(args,env=env,capture_output=True,text=True,timeout=timeout);return p.returncode,p.stdout,p.stderr
 except subprocess.TimeoutExpired as e:return 124,e.stdout or '',(e.stderr or '')+' timeout'
def job(args):
 app,platform,target,w,h,root=args;env=os.environ.copy();env['DEVELOPER_DIR']=str(app/'Contents/Developer');case=root/f'{app.stem}-{platform}-{w}x{h}';item=case/'A.xcassets'/'Probe.imageset';out=case/'out';item.mkdir(parents=True);out.mkdir();(item/'p.png').write_bytes(png(w,h));(item/'Contents.json').write_text(json.dumps({'images':[{'filename':'p.png','idiom':'universal','scale':'1x'}],'info':{'author':'xcode','version':1}}))
 cmd=['xcrun','actool','--compile',str(out),'--platform',platform,'--minimum-deployment-target',target,str(case/'A.xcassets')];rc,stdout,stderr=run(cmd,env)
 row={'xcode_app':str(app),'platform':platform,'width':w,'height':h,'raw_bgra_bytes':w*h*4,'raw_rows_at_0x155555':0x155555//(w*4),'build_exit':rc,'build_stdout':stdout,'build_stderr':stderr}
 car=out/'Assets.car'
 if rc or not car.is_file():row['status']='build-failed';return row
 rc,stdout,stderr=run(['xcrun','--sdk',platform,'assetutil','--info',str(car)],env);row.update(assetutil_exit=rc,assetutil_stderr=stderr)
 try:
  records=json.loads(stdout);asset=next(x for x in records if x.get('Name')=='Probe');row.update(status='pass',compression=asset.get('Compression'),encoding=asset.get('Encoding'),size_on_disk=asset.get('SizeOnDisk'))
 except Exception as e:row.update(status='info-failed',parse_error=repr(e),assetutil_stdout=stdout)
 return row
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=Path('cbck-threshold-matrix.json'));ap.add_argument('--workers',type=int,default=6);ap.add_argument('--xcode-app',action='append',type=Path);ap.add_argument('--platform',action='append',choices=tuple(PLATFORMS));ns=ap.parse_args();apps=ns.xcode_app or sorted(Path('/Applications').glob('Xcode*.app'));platforms={p:PLATFORMS[p] for p in ns.platform} if ns.platform else PLATFORMS
 with tempfile.TemporaryDirectory(prefix='cbck-threshold-') as td:
  jobs=[(app,p,t,w,h,Path(td)) for app in apps for p,t in platforms.items() for w,h in CASES]
  with concurrent.futures.ThreadPoolExecutor(max_workers=ns.workers) as pool:rows=list(pool.map(job,jobs))
 rows.sort(key=lambda r:(r['xcode_app'],r['platform'],r['width'],r['height']));ns.output.write_text(json.dumps({'schema':1,'boundary':hex(0x155555),'rows':rows},indent=2)+'\n');counts={}
 for r in rows:counts[r['status']]=counts.get(r['status'],0)+1
 print(json.dumps({'rows':len(rows),'statuses':counts},sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
