#!/usr/bin/env python3
import binascii,json,os,struct,subprocess,tempfile,zlib,shutil
from pathlib import Path
def c(k,d):return struct.pack('>I',len(d))+k+d+struct.pack('>I',binascii.crc32(k+d)&0xffffffff)
def png(n,alpha):
 pl=bytes.fromhex('ff000000ff000000ffffff00');tr=bytes([255,128,255,64]) if alpha else b''; rows=[]
 for y in range(n):
  idx=[(x+y)%4 for x in range(n)]; packed=bytearray()
  for x in range(0,n,4):
   v=0
   for j in range(4):v|=(idx[x+j] if x+j<n else 0)<<(6-2*j)
   packed.append(v)
  rows.append(b'\0'+packed)
 out=b'\x89PNG\r\n\x1a\n'+c(b'IHDR',struct.pack('>IIBBBBB',n,n,2,3,0,0,0))+c(b'PLTE',pl)
 if tr:out+=c(b'tRNS',tr)
 return out+c(b'IDAT',zlib.compress(b''.join(rows)))+c(b'IEND',b'')
apps=['/Applications/Xcode_16.0.app','/Applications/Xcode_16.4.app','/Applications/Xcode_26.3.app']; rows=[]
root=Path('/tmp/palette-probe');shutil.rmtree(root,ignore_errors=True);root.mkdir()
for app in apps:
 env=os.environ.copy();env['DEVELOPER_DIR']=app+'/Contents/Developer'
 for n in (2,16,64,256):
  for alpha in (False,True):
   base=root/(Path(app).stem+f'-{n}-{alpha}');cat=base/'A.xcassets';item=cat/'P.imageset';out=base/'out';item.mkdir(parents=True);out.mkdir();(item/'p.png').write_bytes(png(n,alpha));(item/'Contents.json').write_text(json.dumps({'images':[{'filename':'p.png','idiom':'universal','scale':'1x'}],'info':{'author':'xcode','version':1}}))
   p=subprocess.run(['xcrun','actool','--compile',str(out),'--platform','macosx','--minimum-deployment-target','13.0',str(cat)],env=env,capture_output=True,text=True)
   if p.returncode:rows.append({'xcode':app,'size':n,'alpha':alpha,'status':'build-failed'});continue
   q=subprocess.run(['xcrun','--sdk','macosx','assetutil','--info',str(out/'Assets.car')],env=env,capture_output=True,text=True)
   try:a=json.loads(q.stdout)[1];rows.append({'xcode':app,'size':n,'alpha':alpha,'compression':a.get('Compression'),'encoding':a.get('Encoding'),'disk':a.get('SizeOnDisk')})
   except Exception:rows.append({'xcode':app,'size':n,'alpha':alpha,'status':'info-failed'})
print(json.dumps(rows,indent=2))
