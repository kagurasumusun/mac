from __future__ import annotations
import binascii, json, plistlib, shutil, struct, subprocess, tempfile, zlib
from pathlib import Path

def chunk(k,d):
    return struct.pack('>I', len(d)) + k + d + struct.pack('>I', binascii.crc32(k+d) & 0xffffffff)

def png(w,h,r,g,b,a=255):
    row = b'\0' + bytes((r,g,b,a))*w
    raw = row*h
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w,h,8,6,0,0,0)) + chunk(b'IDAT', zlib.compress(raw,9)) + chunk(b'IEND', b'')

def write_json(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj))

def info(): return {'info':{'author':'xcode','version':1}}

def main():
    out = {}
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)/'Assets.xcassets'
        stack = root/'AppIcon.solidimagestack'
        write_json(stack/'Contents.json', {'layers':[{'filename':'Front.solidimagestacklayer'},{'filename':'Middle.solidimagestacklayer'},{'filename':'Back.solidimagestacklayer'}], **info()})
        for name,color in [('Front',(255,0,0)),('Middle',(0,255,0)),('Back',(0,0,255))]:
            layer = stack/f'{name}.solidimagestacklayer'
            img = layer/'Content.imageset'
            img.mkdir(parents=True)
            (img/'content.png').write_bytes(png(128,128,*color))
            write_json(layer/'Contents.json', info())
            write_json(img/'Contents.json', {'images':[{'idiom':'vision','scale':'2x','filename':'content.png'}], **info()})
        compile_out = Path(td)/'out'; compile_out.mkdir()
        proc = subprocess.run(['xcrun','actool','--compile',str(compile_out),'--platform','xros','--minimum-deployment-target','1.0',str(root)], capture_output=True, text=True)
        out['rc'] = proc.returncode
        out['stdout'] = proc.stdout
        out['stderr'] = proc.stderr
        out['files'] = sorted(str(p.relative_to(td)) for p in Path(td).rglob('*'))
        car = compile_out/'Assets.car'
        out['car_exists'] = car.exists()
        if car.exists():
            info_proc = subprocess.run(['xcrun','assetutil','-I',str(car)], capture_output=True, text=True)
            out['assetutil_rc'] = info_proc.returncode
            try:
                out['assetutil'] = json.loads(info_proc.stdout)
            except Exception:
                out['assetutil_stdout'] = info_proc.stdout
                out['assetutil_stderr'] = info_proc.stderr
    print(json.dumps(out, indent=2))

if __name__ == '__main__':
    main()
