#!/usr/bin/env python3
"""Trace decode under current rule-set and diff vs target plane.

Rules (v4-mini multi-swatch hypothesis H1):
  first zero-run:  L0>=25 -> f0 V=L0-25 ; else fX=L0-9 (X=L0-9)
  cont zero-run:   f0 V=L-16 (long) ; bare fX = X+2 ; literal eN (+pad to
                   end-of-line at stream end)
  rep  hN V:       emit V x N... count=lo for 5x/6x, hi for 4x?? TRACED
  pair 40 U V:     emit U x4, V x4
  lz 38 XX:        dist=W, len=XX
Paint: flip=1, dx=[-1,1], dy=[h-1,1]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/user/work")
from mini_fit2 import paint, tokenize  # noqa: E402


def loads():
    return json.loads(Path("/home/user/work/mini_corpus.json").read_text())


def trace(stream, W, total, rules):
    toks = tokenize(stream)
    out = bytearray()
    events = []
    first_zero = True
    for kind, arg, raw in toks:
        pos = len(out)
        if kind == "intro":
            events.append((pos, 0, raw, "SECTION"))
            continue
        if kind == "end":
            break
        if kind == "lit":
            bs = bytes.fromhex(arg)
            pad = rules.get("eol_pad", False)
            out += bs
            note = f"lit[{len(bs)}]"
            if pad:
                m = len(out) % W
                if m:
                    out += b"\x00" * (W - m)
                    note += f"+pad2row(+{W - m})"
            events.append((pos, len(out) - pos, raw, note))
        elif kind == "f0":
            bias = 25 if first_zero else 16
            out += b"\x00" * (arg + bias)
            events.append((pos, arg + bias, raw, f"0x{arg + bias} (V+{bias}{' first' if first_zero else ''})"))
            first_zero = False
        elif kind == "fX":
            bias = 9 if first_zero else 2
            out += b"\x00" * (arg + bias)
            events.append((pos, arg + bias, raw, f"0x{arg + bias} (X+{bias}{' first' if first_zero else ''})"))
            first_zero = False
        elif kind == "lz":
            for _ in range(arg):
                out.append(out[-W] if len(out) >= W else 0)
            events.append((pos, arg, raw, f"lz d{W} l{arg}"))
        elif kind == "rep":
            hi, lo, v = arg
            cnt = rules["rep"](hi, lo)
            out += bytes([v]) * cnt
            events.append((pos, cnt, raw, f"v{v}x{cnt} (hi{hi},lo{lo})"))
        elif kind == "pair":
            u, v = arg
            p, q = rules["pair"](u, v)
            out += bytes([u]) * p + bytes([v]) * q
            events.append((pos, p + q, raw, f"{u}x{p}+{v}x{q}"))
        else:
            events.append((pos, 0, raw, f"UNKNOWN-{kind}"))
            return bytes(out), events, True
    return bytes(out), events, False


def show(name, rules, dy0="h-1", dy1=1, dx=(-1, 1), flip=1, maxrow=60):
    r = {c["case"]: c for c in loads()}.get(name)
    if not r:
        print("no case", name)
        return
    W, H = r["W"], r["H"]
    stream = bytes.fromhex(r["stream"])
    px = paint(W, H, r["rects"], dx[0], dx[1], dy0, dy1, flip)
    out, events, bad = trace(stream, W, len(px), rules)
    print(f"== {name} {W}x{H} flip={flip} dx={dx} dy=({dy0},{dy1}) "
          f"emitted {len(out)} / target {len(px)}  {'TOKERR' if bad else ''}")
    ok = True
    for pos, ln, raw, note in events:
        seg_ok = out[pos:pos + ln] == px[pos:pos + ln] if ln else None
        if seg_ok is False:
            ok = False
        print(f"  {pos:4d} +{ln:4d} {raw:26s} {note:34s} {'OK' if seg_ok else ('--' if seg_ok is None else 'MISMATCH')}")
    if len(out) != len(px) or not ok:
        # first byte-level divergence
        for i in range(min(len(out), len(px))):
            if out[i] != px[i]:
                print(f"  first byte mismatch at pos {i}: out={out[i]} px={px[i]}")
                break
        print("  target rows (flipped-stream order):")
        for rr in range(H):
            row = px[rr * W:(rr + 1) * W]
            print(f"    S{rr:2d} " + "".join(" . " if v == 0 else f"{v:2d} " for v in row))


REP_LO = lambda hi, lo: lo
REP_HI = lambda hi, lo: hi
PAIR44 = lambda u, v: (4, 4)

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "m5_trio"
    rep = sys.argv[2] if len(sys.argv) > 2 else "hi"
    rules = {"rep": REP_HI if rep == "hi" else REP_LO, "pair": PAIR44, "eol_pad": True}
    show(name, rules)
