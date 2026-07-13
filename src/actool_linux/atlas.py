"""Packed CoreUI atlas metadata and deterministic shelf packer."""
from __future__ import annotations
from dataclasses import dataclass
import struct, zlib

from .carwriter import AssetRendition, _csi_png_deepmap, _fixed, build_assets_car


@dataclass(frozen=True)
class AtlasKeyToken:
    attribute: int
    value: int

@dataclass(frozen=True)
class AtlasLink:
    x: int
    y: int
    width: int
    height: int
    tokens: tuple[AtlasKeyToken, ...]
    variant: str = "generic"
    header_u16: int = 0
    header_u32: int = 0


def parse_atlas_link(raw: bytes) -> AtlasLink:
    """Parse CoreUI TLV 1010 (INLK), supporting both observed public variants."""
    if len(raw) < 26 or raw[:4] != b"KLNI":
        raise ValueError("invalid atlas link magic or truncated header")
    version, x, y, width, height = struct.unpack_from("<5I", raw, 4)
    if version != 0 or not width or not height:
        raise ValueError("unsupported atlas link header")
    tokens = []
    if raw[24:26] == b"\0\0":
        if (len(raw) - 26) % 4:
            raise ValueError("invalid atlas token alignment")
        for off in range(26, len(raw), 4):
            attribute, value = struct.unpack_from("<2H", raw, off)
            if attribute == value == 0:
                break
            if attribute > 27:
                raise ValueError("atlas token attribute is out of range")
            tokens.append(AtlasKeyToken(attribute, value))
        else:
            raise ValueError("atlas token list has no terminator")
        return AtlasLink(x, y, width, height, tuple(tokens))
    if len(raw) < 34 or (len(raw) - 30) % 4:
        raise ValueError("invalid atlas token alignment")
    header_u16 = struct.unpack_from("<H", raw, 24)[0]
    header_u32 = struct.unpack_from("<I", raw, 26)[0]
    for off in range(30, len(raw), 4):
        attribute, value = struct.unpack_from("<2H", raw, off)
        if attribute == value == 0:
            break
        if attribute > 27:
            raise ValueError("atlas token attribute is out of range")
        tokens.append(AtlasKeyToken(attribute, value))
    else:
        raise ValueError("atlas token list has no terminator")
    return AtlasLink(x, y, width, height, tuple(tokens), variant="explicit", header_u16=header_u16, header_u32=header_u32)


def build_atlas_link(link: AtlasLink) -> bytes:
    if min(link.x, link.y) < 0 or not 0 < link.width <= 65535 or not 0 < link.height <= 65535:
        raise ValueError("invalid atlas rectangle")
    out = bytearray(b"KLNI" + struct.pack("<5I", 0, link.x, link.y, link.width, link.height))
    if link.variant == "generic":
        out += b"\0\0"
        for token in link.tokens:
            if not 0 < token.attribute <= 27 or not 0 <= token.value <= 65535:
                raise ValueError("invalid atlas key token")
            out += struct.pack("<2H", token.attribute, token.value)
        out += b"\0\0\0\0"
        return bytes(out)
    if link.variant == "explicit":
        out += struct.pack("<HI", link.header_u16, link.header_u32)
        for token in link.tokens:
            if not 0 < token.attribute <= 27 or not 0 <= token.value <= 65535:
                raise ValueError("invalid atlas key token")
            out += struct.pack("<2H", token.attribute, token.value)
        out += b"\0\0\0\0"
        return bytes(out)
    raise ValueError(f"unsupported atlas link variant: {link.variant}")


def _linked_csi(filename: str, link: AtlasLink, scale: int) -> bytes:
    h = bytearray(184); h[:4] = b"ISTC"
    struct.pack_into("<5I", h, 4, 1, 4, link.width, link.height, scale * 100)
    h[24:28] = b" 8AG"  # little-endian GA8
    struct.pack_into("<I2H", h, 32, 0, 1003, 0); h[40:168] = _fixed(filename, 128)
    tlvs = b"".join((
        struct.pack("<2I5I",1001,20,1,0,0,link.width,link.height),
        struct.pack("<2I7I",1003,28,1,0,0,0,0,link.width,link.height),
        struct.pack("<2I",1010,len(build_atlas_link(link))) + build_atlas_link(link),
        struct.pack("<2I8s",1004,8,b"\0\0\0\0\0\0\x80?"), struct.pack("<2II",1006,4,1)))
    struct.pack_into("<4I",h,168,len(tlvs),1,0,0)
    return bytes(h)+tlvs


def _png_rgba(width: int, height: int, pixels: bytes) -> bytes:
    def chunk(t: bytes,d: bytes): return struct.pack(">I",len(d))+t+d+struct.pack(">I",zlib.crc32(t+d)&0xffffffff)
    rows=b"".join(b"\0"+pixels[y*width*4:(y+1)*width*4] for y in range(height))
    return b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",width,height,8,6,0,0,0))+chunk(b"IDAT",zlib.compress(rows,9))+chunk(b"IEND",b"")


def build_packed_atlas_car(
    images: dict[str, bytes],
    *,
    scale: int = 1,
    max_width: int = 1024,
    max_height: int = 1024,
    sort_by: str = "name",
    platform: str = "macosx",
    target: str = "13.0",
    deployment_token: int = 5,
) -> bytes:
    """Shelf-pack PNGs into bounded pages using configurable sorting heuristics and emit layout-1003/1004 records.

    Installed Apple atlas fixtures consistently carry INLK token attribute 25
    with value 5; that observable default is used here.
    """ 
    from .carwriter import _decode_png_8bit
    if not images: raise ValueError("atlas needs at least one image")
    if not 0 <= deployment_token <= 65535:
        raise ValueError("invalid atlas deployment token")
    decoded=[]
    for name,data in images.items():
        w,h,ct,pix,_=_decode_png_8bit(data)
        if ct==6: rgba=pix
        elif ct==4: rgba=b"".join(bytes((g,g,g,a)) for g,a in zip(pix[::2],pix[1::2]))
        elif ct==2: rgba=b"".join(bytes((r,g,b,255)) for r,g,b in zip(pix[::3],pix[1::3],pix[2::3]))
        else: raise ValueError("indexed atlas input is not enabled")
        if w>max_width or h>max_height: raise ValueError("atlas item exceeds page bounds")
        decoded.append((name,w,h,rgba))

    if sort_by == "name":
        decoded.sort(key=lambda x: x[0])
    elif sort_by in ("height", "height_desc"):
        decoded.sort(key=lambda x: (-x[2], -x[1], x[0]))
    elif sort_by in ("width", "width_desc"):
        decoded.sort(key=lambda x: (-x[1], -x[2], x[0]))
    elif sort_by in ("area", "area_desc"):
        decoded.sort(key=lambda x: (-x[1]*x[2], -x[2], x[0]))
    elif sort_by in ("max_dim", "max_dim_desc"):
        decoded.sort(key=lambda x: (-max(x[1], x[2]), -x[2], x[0]))
    else:
        raise ValueError(f"unsupported atlas sorting heuristic: {sort_by}")

    # Each placement carries a 1-based page dimension used by INLK tokens.
    x=y=row_h=0; page=1; placements=[]
    for name,w,h,pix in decoded:
        if x and x+w>max_width: x=0; y+=row_h; row_h=0
        if y+h>max_height:
            page+=1; x=y=row_h=0
        placements.append((page,name,x,y,w,h,pix)); x+=w; row_h=max(row_h,h)
    records=[]
    for page_dimension in range(1,page+1):
        page_items=[p for p in placements if p[0]==page_dimension]
        aw=max(px+w for _,_,px,_,w,_,_ in page_items); ah=max(py+h for _,_,_,py,_,h,_ in page_items)
        canvas=bytearray(aw*ah*4)
        for _,_,px,py,w,h,pix in page_items:
            for row in range(h): canvas[((py+row)*aw+px)*4:((py+row)*aw+px+w)*4]=pix[row*w*4:(row+1)*w*4]
        page_name=f"ZZZZPackedAsset-1.0.{page_dimension}-gamut0"
        page_png=_png_rgba(aw,ah,bytes(canvas)); page_csi=bytearray(_csi_png_deepmap(page_png,page_name,scale=scale))
        struct.pack_into("<H",page_csi,36,1004); struct.pack_into("<I",page_csi,8,0)
        records.append(AssetRendition(page_name,bytes(page_csi),181,scale=scale,element=9,identifier_override=0,dimension1=page_dimension,atlas_linked=True,deployment_target=deployment_token))
    for page_dimension,name,px,py,w,h,_ in placements:
        tokens=(AtlasKeyToken(24,0),AtlasKeyToken(1,9),AtlasKeyToken(2,181),AtlasKeyToken(8,page_dimension),AtlasKeyToken(12,scale),AtlasKeyToken(25,deployment_token))
        link=AtlasLink(px,py,w,h,tokens)
        records.append(AssetRendition(name,_linked_csi(name+".png",link,scale),181,scale=scale,atlas_linked=True,deployment_target=deployment_token))
    return build_assets_car(records,platform=platform,target=target)
