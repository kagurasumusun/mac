#!/usr/bin/env python3
"""Generate observable tvOS/visionOS layered-asset oracles with Apple actool."""
from __future__ import annotations
import argparse,binascii,json,plistlib,struct,subprocess,zlib,shutil,hashlib
from pathlib import Path
def chunk(k,d):return struct.pack('>I',len(d))+k+d+struct.pack('>I',binascii.crc32(k+d)&0xffffffff)
def png(w,h,r,g,b):
 row=b'\0'+bytes((r,g,b,255))*w;raw=row*h
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b'')
def write_json(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x))
def info():return {'info':{'author':'xcode','version':1}}
def layer(d,name,w,h,color,idiom):
 d.mkdir(parents=True);fn=name+'.png';(d/fn).write_bytes(png(w,h,*color));write_json(d/'Contents.json',{'images':[{'idiom':idiom,'scale':'1x','filename':fn}],**info()})
def run(cmd):
 p=subprocess.run(cmd,capture_output=True);parsed=None
 try:parsed=plistlib.loads(p.stdout)
 except Exception:pass
 return {'command':cmd,'exit_code':p.returncode,'stdout':p.stdout.decode('utf-8','replace'),'stderr':p.stderr.decode('utf-8','replace'),'parsed':parsed}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path('/tmp/compositor-oracle'));ap.add_argument('--output',type=Path,default=Path('compositor-oracle.json'));a=ap.parse_args();shutil.rmtree(a.root,ignore_errors=True);a.root.mkdir();report={}
 # tvOS brand assets with primary stack and both Top Shelf roles.
 cat=a.root/'TV.xcassets';brand=cat/'App Icon & Top Shelf Image.brandassets';stack=brand/'App Icon.imagestack'
 write_json(brand/'Contents.json',{'assets':[{'idiom':'tv','role':'primary-app-icon','filename':'App Icon.imagestack'},{'idiom':'tv','role':'top-shelf-image','filename':'Top Shelf Image.imageset'},{'idiom':'tv','role':'top-shelf-image-wide','filename':'Top Shelf Image Wide.imageset'}],**info()})
 write_json(stack/'Contents.json',{'layers':[{'filename':'Front.imagestacklayer'},{'filename':'Back.imagestacklayer'}],**info()});layer(stack/'Front.imagestacklayer','front',1280,768,(20,180,240),'tv');layer(stack/'Back.imagestacklayer','back',1280,768,(240,80,20),'tv')
 for name,w in [('Top Shelf Image',1920),('Top Shelf Image Wide',2320)]:
  d=brand/(name+'.imageset');d.mkdir();fn='image.png';(d/fn).write_bytes(png(w,720,40,160,80));write_json(d/'Contents.json',{'images':[{'idiom':'tv','scale':'1x','filename':fn}],**info()})
 out=a.root/'tv-out';out.mkdir();partial=a.root/'tv-partial.plist';r=run(['xcrun','actool','--compile',str(out),'--platform','appletvos','--minimum-deployment-target','15.0','--app-icon','App Icon','--output-partial-info-plist',str(partial),str(cat)]);report['tv']=r
 car=out/'Assets.car'
 if car.exists():
  q=subprocess.run(['xcrun','--sdk','appletvos','assetutil','--info',str(car)],capture_output=True,text=True);report['tv'].update(car_sha256=hashlib.sha256(car.read_bytes()).hexdigest(),car_path=str(car),assetutil_exit=q.returncode,assetutil=json.loads(q.stdout) if q.returncode==0 else q.stdout)
 # visionOS stack, observable public catalog structure.
 cat=a.root/'Vision.xcassets';stack=cat/'VisionIcon.imagestack';write_json(stack/'Contents.json',{'layers':[{'filename':'Front.imagestacklayer'},{'filename':'Back.imagestacklayer'}],**info()});layer(stack/'Front.imagestacklayer','front',1024,1024,(20,180,240),'vision');layer(stack/'Back.imagestacklayer','back',1024,1024,(240,80,20),'vision')
 out=a.root/'vision-out';out.mkdir();r=run(['xcrun','actool','--compile',str(out),'--platform','xros','--minimum-deployment-target','1.0',str(cat)]);report['vision']=r;car=out/'Assets.car'
 if car.exists():
  q=subprocess.run(['xcrun','--sdk','xros','assetutil','--info',str(car)],capture_output=True,text=True);report['vision'].update(car_sha256=hashlib.sha256(car.read_bytes()).hexdigest(),car_path=str(car),assetutil_exit=q.returncode,assetutil=json.loads(q.stdout) if q.returncode==0 else q.stdout)
 a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:{'exit':v['exit_code'],'car':v.get('car_path')} for k,v in report.items()}));
if __name__=='__main__':main()
