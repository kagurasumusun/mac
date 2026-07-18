#!/usr/bin/env python3
"""Joint solver: shared opcode meaning map x paint model, EXACT decode required.

Search dimensions
  paint: halo in {four, lrb(left/right/bottom), lrt, none} x flip in {0,1}
  fX (X>0): zeros X+first_bias (first) / X+cont_bias (later)
  f0 V:     zeros V+cont_bias  |  copy-line V+cont_bias  |  zeros V+2
  copy-token 38 XX: lz-distance XX | line-copy (pad to boundary + copy XX)
  4N/5N/6N V: emit V {nibble, nibble+1, fixed} times
  eN: literal N bytes (incl. e7/e8/e9 end-of-image zeros)
Cases n1, n5, m1 must ALL decode EXACTLY (0 mismatch, exact length) with one
shared map. Prints all exact solutions.
"""
import itertools
import sys

sys.path.insert(0, "/home/user/mac-repo/src")
sys.path.insert(0, "/home/user/work")
from mini_align import load_atlas_case  # noqa: E402

CASES = [
    ("n1", "/home/user/work/ap2-out/n1_1x1x2/Assets.car", {"A.png": 2, "B.png": 1}),
    ("n5", "/home/user/work/ap2-out/n5_4x4x2/Assets.car", {"A.png": 2, "B.png": 1}),
    ("m1", "/home/user/work/atlasprobe-apple-out/m1_pair2x2/Assets.car", {"A.png": 2, "B.png": 1}),
]


def paint(W, H, rends, values, halo, flip):
    px = [0] * (W * H)
    for r, v in zip(rends, values):
        x, y, w, h = r["x"], r["y"], r["w"], r["h"]
        x0 = x - 1 if halo in ("four", "lrb", "lrt", "lr") else x
        x1 = x + w + 1 if halo in ("four", "lrb", "lrt", "lr") else x + w
        if halo == "four":
            y0, y1 = y - 1, y + h + 1
        elif halo == "lrb":
            y0, y1 = y, y + h + 1
        elif halo == "lrt":
            y0, y1 = y - 1, y + h
        else:  # none
            x0, x1, y0, y1 = x, x + w, y, y + h
        x0 = max(0, x0); y0 = max(0, y0)
        x1 = min(W, x1); y1 = min(H, y1)
        for yy in range(y0, y1):
            for xx in range(x0, x1):
                px[yy * W + xx] = v
    if flip:
        out = [0] * (W * H)
        for yy in range(H):
            out[yy * W:(yy + 1) * W] = px[(H - 1 - yy) * W:(H - yy) * W]
        return out
    return px


def parse(stream, total, *, first_bias, cont_mode, copy_mode, n_map):
    out = bytearray()
    i, first_t = 0, True
    while i < len(stream) and len(out) < total:
        b = stream[i]
        if b == 0x68 and i + 2 < len(stream) and stream[i + 1] == 1:
            i += 3
            continue
        if b == 0x38:
            xx = stream[i + 1]
            if copy_mode == "lz":
                if not out or xx > len(out):
                    return None
                for _ in range(xx):
                    out.append(out[-xx])
            else:  # line: zero-fill to W? caller passes W via copy_mode tuple
                return None
            i += 2
            continue
        if b == 0xF0:
            v = stream[i + 1]
            if cont_mode[0] == "zeros16":
                out += b"\x00" * (v + 16)
            elif cont_mode[0] == "zeros2":
                out += b"\x00" * (v + 2)
            elif cont_mode[0] == "copyline":
                dist = cont_mode[1]
                for _ in range(v + 16):
                    out.append(out[-dist])
            i += 2
            continue
        if 0xF1 <= b <= 0xFE:
            bias = cont_mode[2] if not first_t else first_bias
            out += b"\x00" * ((b & 0x0F) + bias)
            first_t = False
            i += 1
            continue
        if 0x40 <= b < 0x70 and (b >> 4) in n_map:
            out += bytes([stream[i + 1]]) * n_map[b >> 4]
            i += 2
            continue
        if 0xE1 <= b <= 0xEC:
            n = b & 0x0F
            payload = stream[i + 1:i + 1 + n]
            if cont_mode[0] == "end_fills" or True:
                out += payload
                i += 1 + n
                # zero-pad within the stream trailing area only
                while i < len(stream) and stream[i] == 0 and len(out) < total:
                    out.append(0)
                    i += 1
            continue
        if b == 0x06:
            break
        return None
    if len(out) != total:
        return None
    return bytes(out)


def main():
    loaded = []
    for name, car, cols in CASES:
        W, H, pal, ver, stream, rends = load_atlas_case(car, None, False)
        values = [cols[r["name"]] for r in rends]
        loaded.append((name, W, H, stream, rends, values, pal))

    solutions = []
    for halo in ("four", "lrb", "lrt", "none"):
        for flip in (0, 1):
            models = []
            for name, W, H, stream, rends, values, pal in loaded:
                models.append((name, paint(W, H, rends, values, halo, flip)))
            for first_bias in (8, 9, 10, 2):
                for cont_zeros_bias, zero16 in ((16, True), (2, False), (9, True)):
                    for copy_mode in ("lz",):
                        for n4, n5, n6 in itertools.product((4, 0), (5, 6, 7, 0), (6, 0)):
                            if not n4 and not n5 and not n6:
                                continue
                            n_map = {k: v for k, v in ((4, n4), (5, n5), (6, n6)) if v}
                            ok_all = True
                            for (name, W, H, stream, rends, values, pal), (_, model) in zip(loaded, models):
                                got = parse(stream, len(model),
                                            first_bias=first_bias,
                                            cont_mode=("zeros16" if zero16 else "zeros2", None, cont_zeros_bias),
                                            copy_mode=copy_mode, n_map=n_map)
                                if got is None or list(got) != model:
                                    ok_all = False
                                    break
                            if ok_all:
                                solutions.append((halo, flip, first_bias, cont_zeros_bias, zero16, n_map))
                                print("EXACT:", halo, "flip", flip, "fb", first_bias, "cb", cont_zeros_bias, "z16", zero16, n_map)
    if not solutions:
        print("no exact solution in the searched subspace")


if __name__ == "__main__":
    main()
