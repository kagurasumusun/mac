#!/usr/bin/env python3
"""Generic exact-cover aligner for mini streams (v4 color, 1-byte units).

Each token's emission length/mode is resolved by DP against a candidate
painted plane. Paint model is searched: rows [y+dy0, y+h+dy1] (dy0 in
{0,1,h-1}, dy1 in {0,1}), cols [x+dx0, x+w+dx1] (dx0,dx1 in {-1,0,1}).
Stream may be flipped bottom-up.

Op token families:
  68 01 XX    section intro (skipped, position transparent)
  eN          N literal bytes
  fX          zeros, len = X + b (b resolved per token; reported)
  f0 V        zeros, len = V + b
  38 XX       LZ copy dist=W*unit, len XX(+0..2)
  4N/5N/6N V  emit V x count(lo|hi|+1)
  40 U V      emit U x a then V x b (a,b resolved)
  30 U        ? (raw candidates)
  fe/fa/f8    zeros X+b handled by fX rule
  06          end
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def load_cases():
    return json.loads(Path("/home/user/work/mini_corpus.json").read_text())


def paint(W, H, rects, dx0, dx1, dy0, dy1, flip):
    px = [0] * (W * H)
    for r in rects:
        v = r["val"]
        if v is None:
            return None
        x0 = max(0, r["x"] + dx0)
        x1 = min(W, r["x"] + r["w"] + dx1)
        s0 = r["y"] + (r["h"] - 1 if dy0 == "h-1" else dy0)
        y0 = max(0, s0)
        y1 = min(H, r["y"] + r["h"] + dy1)
        for yy in range(y0, y1):
            for xx in range(x0, x1):
                px[yy * W + xx] = v
    if flip:
        rows = [px[i * W:(i + 1) * W] for i in range(H)]
        rows.reverse()
        px = [b for row in rows for b in row]
    return px


def tokenize(stream: bytes):
    toks = []
    i, n = 0, len(stream)
    while i < n:
        b = stream[i]
        if b == 0x68 and i + 2 < n and stream[i + 1] == 0x01:
            toks.append(("intro", stream[i + 2], stream[i:i + 3].hex()))
            i += 3
        elif b == 0x38:
            toks.append(("lz", stream[i + 1], stream[i:i + 2].hex()))
            i += 2
        elif b == 0xF0:
            toks.append(("f0", stream[i + 1], stream[i:i + 2].hex()))
            i += 2
        elif 0xF1 <= b <= 0xFE:
            toks.append(("fX", b & 0x0F, stream[i:i + 1].hex()))
            i += 1
        elif 0xE1 <= b <= 0xEC:
            ln = b & 0x0F
            toks.append(("lit", stream[i + 1:i + 1 + ln].hex(), stream[i:i + 1 + ln].hex()))
            i += 1 + ln
        elif b in (0x46, 0x56, 0x66, 0x4E, 0x5E, 0x6E):
            toks.append(("rep", ((b >> 4) & 7, b & 0x0F, stream[i + 1]), stream[i:i + 2].hex()))
            i += 2
        elif b == 0x40:
            toks.append(("pair", (stream[i + 1], stream[i + 2]), stream[i:i + 3].hex()))
            i += 3
        elif b == 0x30:
            toks.append(("t30", stream[i + 1], stream[i:i + 2].hex()))
            i += 2
        elif b in (0xC8, 0xCE):
            toks.append((f"t{b:02x}", stream[i + 1], stream[i:i + 2].hex()))
            i += 2
        elif b == 0x06:
            toks.append(("end", None, "06"))
            break
        else:
            toks.append(("raw", b, f"{b:02x}"))
            i += 1
    return toks


def cover(px, toks, W, unit=1):
    total = len(px)
    best = []
    row = W * unit

    def rec(ti, pos, assign):
        if ti >= len(toks) or toks[ti][0] == "end":
            if pos == total:
                best.append(list(assign))
            return len(best) > 200
        kind, arg, raw = toks[ti]
        stop = False
        if kind == "intro":
            stop = rec(ti + 1, pos, assign)
        elif kind == "lit":
            bs = list(bytes.fromhex(arg))
            if px[pos:pos + len(bs)] == bs:
                stop = rec(ti + 1, pos + len(bs), assign + [(kind, raw, pos, len(bs), "lit")])
        elif kind == "f0":
            for b in range(0, 90):
                ln = arg + b
                if pos + ln > total:
                    break
                if not any(px[pos:pos + ln]):
                    if rec(ti + 1, pos + ln, assign + [(kind, raw, pos, ln, f"0x{ln}=V+{b}")]):
                        return True
        elif kind == "fX":
            for b in range(0, 90):
                ln = arg + b
                if pos + ln > total:
                    break
                if not any(px[pos:pos + ln]):
                    if rec(ti + 1, pos + ln, assign + [(kind, raw, pos, ln, f"0x{ln}=X+{b}")]):
                        return True
        elif kind == "lz":
            for dl in (0, 1, 2):
                ln = arg + dl
                if pos + ln > total or pos - row < 0:
                    continue
                ok = True
                for k in range(ln):
                    if px[pos + k] != px[pos - row + k]:
                        ok = False
                        break
                if ok:
                    if rec(ti + 1, pos + ln, assign + [(kind, raw, pos, ln, f"lz d{row} l{ln}")]):
                        return True
        elif kind == "rep":
            hi, lo, v = arg
            for cnt in (lo, hi, lo + 1, hi + 1, lo + 2, hi + 2):
                if cnt <= 0 or pos + cnt > total:
                    continue
                if all(x == v for x in px[pos:pos + cnt]):
                    if rec(ti + 1, pos + cnt,
                             assign + [(kind, raw, pos, cnt, f"v{v}x{cnt}(hi{hi},lo{lo})")]):
                        return True
        elif kind == "pair":
            u, v = arg
            for a in range(1, 9):
                for b in range(1, 9):
                    seq = [u] * a + [v] * b
                    if pos + a + b > total:
                        continue
                    if px[pos:pos + a + b] == seq:
                        if rec(ti + 1, pos + a + b,
                               assign + [(kind, raw, pos, a + b, f"{u}x{a}+{v}x{b}")]):
                            return True
        elif kind in ("t30", "tc8", "tce"):
            # unknown: try zeros len arg+b, or rep of arg value, or lit single
            for b in range(0, 20):
                ln = b
                if pos + ln <= total and not any(px[pos:pos + ln]):
                    if rec(ti + 1, pos + ln, assign + [(kind, raw, pos, ln, f"?0x{ln}")]):
                        return True
            for cnt in range(1, 20):
                if pos + cnt <= total and all(x == arg for x in px[pos:pos + cnt]):
                    if rec(ti + 1, pos + cnt,
                           assign + [(kind, raw, pos, cnt, f"?v{arg}x{cnt}")]):
                        return True
        elif kind == "raw":
            if pos < total and px[pos] == arg:
                stop = rec(ti + 1, pos + 1, assign + [(kind, raw, pos, 1, "rawlit")])
        return stop

    rec(0, 0, [])
    return best


def solve_case(rec, maxsol=3):
    W, H, rects = rec["W"], rec["H"], rec["rects"]
    stream = bytes.fromhex(rec["stream"])
    toks = tokenize(stream)
    sols = []
    for flip in (1, 0):
        for dx0 in (-1, 0):
            for dx1 in (0, 1):
                for dy0 in (0, 1, "h-1"):
                    for dy1 in (0, 1):
                        px = paint(W, H, rects, dx0, dx1, dy0, dy1, flip)
                        if px is None:
                            continue
                        covs = cover(px, toks, W)
                        for c in covs[:2]:
                            sols.append((flip, dx0, dx1, dy0, dy1, c))
                        if len(sols) >= maxsol:
                            return sols
    return sols


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for rec in load_cases():
        if rec["ver"] != 4:
            continue
        if only and only not in rec["case"]:
            continue
        sols = solve_case(rec)
        print(f"== {rec['case']} {rec['W']}x{rec['H']}  ({len(sols)} sols)")
        for flip, dx0, dx1, dy0, dy1, cov in sols[:2]:
            print(f"   PAINT flip={flip} dx[{dx0},{dx1}] dy[{dy0},{dy1}]")
            for kind, raw, pos, ln, desc in cov:
                print(f"     {pos:4d} +{ln:4d}  {kind:5s} {raw:26s} {desc}")


if __name__ == "__main__":
    main()
