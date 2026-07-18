#!/usr/bin/env python3
import binascii,json,struct,subprocess,sys,zlib,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from actool_linux.bom import BOMStore
from actool_linux.car import CARFile
def c(k,d):return struct.pack('>I',len(d))+k+d+struct.pack('>I',binascii.crc32(k+d)&0xffffffff)
def png(w,h,vals):
 raw=b''.join(b'\0'+b''.join(struct.pack('>HH',*vals[y*w+x]) for x in range(w)) for y in range(h));return b'\x89PNG\r\n\x1a\n'+c(b'IHDR',struct.pack('>IIBBBBB',w,h,16,4,0,0,0))+c(b'IDAT',zlib.compress(raw))+c(b'IEND',b'')
root=Path('/tmp/deepmap-ga16');shutil.rmtree(root,ignore_errors=True);root.mkdir();rows=[]
for w,h in [(1,1),(2,1),(2,2)]:
 cat=root/f'{w}x{h}/A.xcassets';item=cat/'Probe.imageset';out=root/f'{w}x{h}/out';item.mkdir(parents=True);out.mkdir();(cat/'Contents.json').write_text(json.dumps({'info':{'author':'xcode','version':1}}));vals=[((0x1234+i*0x2222)&65535,(0xffff-i*0x3333)&65535) for i in range(w*h)];(item/'p.png').write_bytes(png(w,h,vals));(item/'Contents.json').write_text(json.dumps({'images':[{'filename':'p.png','idiom':'universal','scale':'1x'}],'info':{'author':'xcode','version':1}}));subprocess.run(['xcrun','actool','--compile',str(out),'--platform','macosx','--minimum-deployment-target','13.0',str(cat)],check=True,capture_output=True);r=CARFile(BOMStore.from_path(out/'Assets.car')).renditions[0].csi;rows.append({'w':w,'h':h,'values':vals,'format':r.pixel_format,'flags':r.flags,'payload':r.rendition_data.hex()})
print(json.dumps(rows,indent=2))
