#!/usr/bin/env python3
"""Constrained exact-cover for one mini-stream case with broad per-token
mode families. Prints ALL consistent assignments (aggregated)."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "/home/user/work")
from mini_fit2 import paint, tokenize  # noqa: E402


def loads():
    return json.loads(Path("/home/user/work/mini_corpus.json").read_text())


def solve(rec, flip=1, dx=(-1, 1), dy0="h-1", dy1=1, maxsol=8):
    W, H = rec["W"], rec["H"]
    stream = bytes.fromhex(rec["stream"])
    toks = tokenize(stream)
    target = paint(W, H, rec["rects"], dx[0], dx[1], dy0, dy1, flip)
    total = len(target)
    sols = []

    def rec_f(ti, pos, out, assign):
        if len(sols) >= maxsol:
            return
        if ti >= len(toks) or toks[ti][0] == "end":
            if pos == total and bytes(out) == target:
                sols.append(assign)
            return
        kind, arg, raw = toks[ti]
        opts = []  # (nextpos, newout_tail, desc)
        if kind == "intro":
            rec_f(ti + 1, pos, out, assign)
            return
        if kind == "lit":
            bs = list(bytes.fromhex(arg))
            opts.append((bs, f"lit{len(bs)}"))
            # with pad-to-row-end
            m = (pos + len(bs)) % W
            if m:
                opts.append((bs + [0] * (W - m), f"lit{len(bs)}+pad{W - m}"))
        elif kind == "f0":
            for b, tag in ((25, "first25"), (16, "c16"), (15, "c15"), (14, "c14")):
                opts.append(([0] * (arg + b), f"0x{arg}+{b}{tag}"))
        elif kind == "fX":
            opts.append(([0] * (arg + 2), f"0x{arg}+2"))
            opts.append(([0] * (arg + 9), f"0x{arg}+9f"))
            for dl in (2, 9):
                ln = arg + dl
                if pos >= W:
                    opts.append((None, f"lz({W},{ln})"))  # special: apply from out
        elif kind == "lz":
            opts.append((None, f"lz({W},{arg})"))
            opts.append((None, f"lz({W},{arg + 1})"))
        elif kind == "rep":
            hi, lo, v = arg
            for cnt in sorted({lo, hi, (lo + hi), lo + 4, hi + 4, lo + 2, hi + 2} | {v2 for v2 in (18, 14, 10, 9, 8, 7, 6, 5, 4, 3) if 0 < v2}):
                opts.append(([v] * cnt, f"v{v}x{cnt}({raw[:2]})"))
        elif kind == "pair":
            u, v = arg
            for pa in range(1, 9):
                for pb in range(1, 9):
                    opts.append(([u] * pa + [v] * pb, f"{u}x{pa}+{v}x{pb}"))
                    opts.append(([v] * pa + [u] * pb, f"{v}x{pa}+{u}x{pb}"))
        else:
            return
        for tail, desc in opts:
            if tail is None:  # lz from history
                ln = int(desc.split(",")[1].rstrip(")"))
                if pos + ln > total or pos < W:
                    continue
                seg = [out[pos - W + k] for k in range(ln)]
            else:
                seg = tail
                ln = len(seg)
            if pos + ln > total:
                continue
            if bytes(seg) != target[pos:pos + ln]:
                continue
            rec_f(ti + 1, pos + ln, out + bytes(seg), assign + [(raw, desc, pos, ln)])
    rec_f(0, 0, bytearray(), [])
    return target, sols


def main():
    name = sys.argv[1]
    rec = {c["case"]: c for c in loads()}[name]
    target, sols = solve(rec)
    print(f"{name}: {len(sols)} solutions")
    for s in sols[:6]:
        print("  ---")
        for raw, desc, pos, ln in s:
            print(f"   {pos:4d} +{ln:4d} {raw:22s} {desc}")


if __name__ == "__main__":
    main()
