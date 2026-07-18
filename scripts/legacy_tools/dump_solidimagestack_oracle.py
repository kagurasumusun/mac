from __future__ import annotations
import binascii, json, struct, subprocess, tempfile, zlib
from pathlib import Path

from actool_linux.bom import BOMStore
from actool_linux.car import CARFile


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

with tempfile.TemporaryDirectory() as td:
    root = Path(td)/'Assets.xcassets'
    stack = root/'AppIcon.solidimagestack'
    write_json(stack/'Contents.json', {'layers':[{'filename':'Front.solidimagestacklayer'},{'filename':'Middle.solidimagestacklayer'},{'filename':'Back.solidimagestacklayer'}], **info()})
    for name,color,alpha in [('Front',(255,0,0),200),('Middle',(0,255,0),180),('Back',(0,0,255),255)]:
        layer = stack/f'{name}.solidimagestacklayer'
        img = layer/'Content.imageset'
        img.mkdir(parents=True)
        # make 512x512 @2x = 256pt canvas, with transparent gutter for front/middle only
        if name == 'Back':
            data = png(512,512,*color,a=alpha)
        else:
            data = png(512,512,*color,a=alpha)
        (img/'content.png').write_bytes(data)
        write_json(layer/'Contents.json', info())
        write_json(img/'Contents.json', {'images':[{'idiom':'vision','scale':'2x','filename':'content.png'}], **info()})
    compile_out = Path(td)/'out'; compile_out.mkdir()
    proc = subprocess.run(['xcrun','actool','--compile',str(compile_out),'--platform','xros','--minimum-deployment-target','1.0',str(root)], capture_output=True, text=True)
    car = compile_out/'Assets.car'
    out = {'rc':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr,'car_exists':car.exists()}
    if car.exists():
        parsed = CARFile(BOMStore.from_path(str(car)))
        out['our_parser'] = [
            {
                'name': r.csi.name,
                'layout': r.csi.layout,
                'pixel_format': r.csi.pixel_format,
                'flags': r.csi.flags,
                'width': r.csi.width,
                'height': r.csi.height,
                'key': r.key,
                'tlvs': [{'tag': t.tag, 'len': len(t.value), 'hex': t.value[:96].hex()} for t in r.csi.tlvs],
                'payload_len': len(r.csi.rendition_data),
                'payload_hex': r.csi.rendition_data[:128].hex(),
            }
            for r in parsed.renditions
        ]
        ai = subprocess.run(['xcrun','assetutil','-I',str(car)], capture_output=True, text=True)
        out['assetutil'] = json.loads(ai.stdout)
    print(json.dumps(out, indent=2))
