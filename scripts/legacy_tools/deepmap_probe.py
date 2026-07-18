#!/usr/bin/env python3
"""Generate deterministic GA8 PNG fixtures and dump per-size Apple dmp2 payloads."""
from __future__ import annotations
import argparse,binascii,json,struct,subprocess,sys,zlib,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from actool_linux.bom import BOMStore
from actool_linux.car import CARFile

def chunk(k,d): return struct.pack('>I',len(d))+k+d+struct.pack('>I',binascii.crc32(k+d)&0xffffffff)
def png(w,h,p):
 rows=[b'\0'+bytes(p[y*w*2:(y+1)*w*2]) for y in range(h)]
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,4,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(rows)))+chunk(b'IEND',b'')
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--work',type=Path,default=Path('/tmp/deepmap-probe')); ns=ap.parse_args()
 if ns.work.exists(): shutil.rmtree(ns.work)
 ns.work.mkdir(); rows=[]
 for w,h in [(1,1),(2,1),(1,2),(2,2),(3,2),(10,10)]:
  root=ns.work/f'{w}x{h}'; cat=root/'A.xcassets'; item=cat/'Probe.imageset'; out=root/'out'; item.mkdir(parents=True); out.mkdir()
  (cat/'Contents.json').write_text(json.dumps({'info':{'author':'xcode','version':1}}))
  pixels=[]
  for i in range(w*h): pixels += [(i*37+11)&255,(255-i*29)&255]
  (item/'p.png').write_bytes(png(w,h,pixels)); (item/'Contents.json').write_text(json.dumps({'images':[{'filename':'p.png','idiom':'universal','scale':'1x'}],'info':{'author':'xcode','version':1}}))
  subprocess.run(['xcrun','actool','--compile',str(out),'--platform','macosx','--minimum-deployment-target','13.0',str(cat)],check=True,capture_output=True)
  car=CARFile(BOMStore.from_path(out/'Assets.car')); r=car.renditions[0]
  rows.append({'width':w,'height':h,'pixels_hex':bytes(pixels).hex(),'csi_width':r.csi.width,'csi_height':r.csi.height,'payload_hex':r.csi.rendition_data.hex()})
 print(json.dumps(rows,indent=2))
if __name__=='__main__': main()
