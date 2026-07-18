#!/usr/bin/env python3
from __future__ import annotations
import binascii,json,struct,subprocess,sys,zlib,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from actool_linux.bom import BOMStore
from actool_linux.car import CARFile
def c(k,d):return struct.pack('>I',len(d))+k+d+struct.pack('>I',binascii.crc32(k+d)&0xffffffff)
def png(w,h,p):
 raw=b''.join(b'\0'+bytes(p[y*w*4:(y+1)*w*4]) for y in range(h))
 return b'\x89PNG\r\n\x1a\n'+c(b'IHDR',struct.pack('>IIBBBBB',w,h,8,6,0,0,0))+c(b'IDAT',zlib.compress(raw))+c(b'IEND',b'')
def main():
 root=Path('/tmp/deepmap-rgba');shutil.rmtree(root,ignore_errors=True);root.mkdir();rows=[]
 for w,h in [(1,1),(2,1),(2,2)]:
  cat=root/f'{w}x{h}/A.xcassets';item=cat/'Probe.imageset';out=root/f'{w}x{h}/out';item.mkdir(parents=True);out.mkdir();(cat/'Contents.json').write_text(json.dumps({'info':{'author':'xcode','version':1}}))
  p=[]
  for i in range(w*h):p += [(11+i*37)&255,(23+i*29)&255,(41+i*17)&255,(255-i*31)&255]
  (item/'p.png').write_bytes(png(w,h,p));(item/'Contents.json').write_text(json.dumps({'images':[{'filename':'p.png','idiom':'universal','scale':'1x'}],'info':{'author':'xcode','version':1}}))
  subprocess.run(['xcrun','actool','--compile',str(out),'--platform','macosx','--minimum-deployment-target','13.0',str(cat)],check=True,capture_output=True)
  r=CARFile(BOMStore.from_path(out/'Assets.car')).renditions[0].csi
  rows.append({'w':w,'h':h,'pixels':bytes(p).hex(),'format':r.pixel_format,'flags':r.flags,'colorspace':r.color_space_id,'payload':r.rendition_data.hex()})
 print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
