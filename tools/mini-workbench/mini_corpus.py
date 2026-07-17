#!/usr/bin/env python3
"""Dump every mini-stream atlas case across all local Apple corpora.

For each atlas rendition whose dmp2 stream is a 'mini' stream (not LZFSE,
not raw-v1), print: case, WxH, pal entries, ver, rects, and stream hex.
Also resolve each rendition's palette index / GA value from the source PNG
when the probe suite dir can be found.
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, "/home/user/mac-repo/src")
sys.path.insert(0, "/home/user/work")
from mini_align import load_atlas_case, read_png_rgba  # noqa: E402

CORPORA = [
    ("/home/user/work/ap2-out", "/home/user/work/atlas-probe2"),
    ("/home/user/work/atlasprobe-apple-out", "/home/user/work/atlas-probe-suite"),
    ("/home/user/work/probe5-out", "/home/user/work/probe5-suite"),
    ("/home/user/work/probe6-out", "/home/user/work/probe6-suite"),
]


def find_png(suiteroot: Path, case: str, name: str):
    for cdir in (suiteroot / f"{case}.xcassets", suiteroot / case):
        if cdir.is_dir():
            hits = sorted(cdir.glob(f"**/{name}"))
            if hits:
                return hits[0]
    stem = Path(name).stem
    for hit in sorted(suiteroot.glob(f"*/{stem}.imageset/{name}")):
        return hit
    return None


def png_ga(path: Path):
    w, h, ch, px = read_png_rgba(path)
    if ch == 2:
        return px[0], px[1]
    if ch == 4:
        return px[0], px[3]
    if ch == 3:
        return px[0], 255
    raise ValueError


def main():
    out = []
    for outroot_s, suiteroot_s in CORPORA:
        outroot, suiteroot = Path(outroot_s), Path(suiteroot_s)
        if not outroot.is_dir():
            continue
        for card in sorted(outroot.rglob("Assets.car")):
            case = card.parent.name
            try:
                W, H, pal, ver, stream, rends = load_atlas_case(str(card), None, False)
            except Exception as e:
                print(f"# {case}: load fail {e}")
                continue
            if stream[:4] == b"LZFSE" or (ver == 4 and len(stream) > 512):
                continue  # LZFSE palettes handled elsewhere
            # resolve values (slot-aware for scale-variant imagesets)
            import json as _json
            vals = {}
            suite_case_pngs = {}  # imageset dir -> {name: (w,h,color)}
            for r in rends:
                key = (r["w"], r["h"], r["name"])
                png = find_png(suiteroot, case, r["name"])
                v = None
                cands = []
                casedir = None
                for cand in (suiteroot / f"{case}.xcassets", suiteroot / case):
                    if cand.is_dir():
                        casedir = cand
                        break
                if casedir and png:
                    files = sorted({p for p in casedir.glob(f"**/{r['name']}")})
                elif png:
                    files = [png]
                else:
                    files = []
                if files:
                    for f in files:
                        try:
                            w, h, ch, px = read_png_rgba(f)
                            if ch == 4:
                                rgba = bytes(px[:4])
                            elif ch == 3:
                                rgba = bytes(px[:3]) + b"\xff"
                            else:
                                rgba = bytes([px[0], px[0], px[0], px[1]])
                            cands.append((w, h, rgba))
                        except Exception:
                            pass
                for (w, h, rgba) in cands:
                    if ver == 4 and (w, h) == (r["w"], r["h"]) and pal:
                        bgra = bytes([rgba[2], rgba[1], rgba[0], rgba[3]])
                        for i, p in enumerate(pal):
                            if bytes(p) == bgra:
                                v = i
                                break
                    elif ver != 4 and (w, h) == (r["w"], r["h"]):
                        if ch == 2:
                            v = (px[0], px[1])
                        elif ch == 4:
                            v = (px[0], px[3])
                        else:
                            v = (px[0], 255)
                        break
                vals[r["name"] + f"@{r['x']},{r['y']}"] = v
                r["val"] = v
            rec = dict(case=case, car=str(card), W=W, H=H, ver=ver,
                       pal=[bytes(p).hex() for p in pal] if pal else None,
                       rects=[dict(r) for r in rends],
                       stream=stream.hex())
            out.append(rec)
            print(f"== {case} v{ver} {W}x{H} pal={len(pal) if pal else '-'} "
                  f"stream={stream.hex()}")
            for r in rends:
                print(f"   {r['name']} @({r['x']},{r['y']}) {r['w']}x{r['h']} val={r['val']}")
    Path("/home/user/work/mini_corpus.json").write_text(json.dumps(out, indent=1))
    print(f"\nwrote {len(out)} cases to mini_corpus.json")


if __name__ == "__main__":
    main()
