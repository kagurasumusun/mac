"""dmp2 "mini" grammars observed in Apple-produced cars (small deepmap comp).

Apple switches dmp2 payload grammar by payload size for near-uniform
sources. All rules below were extracted purely from observable artefacts
(Apple actool outputs; probe suites hp9/hp10 + probe5/probe6 corpus). No
Apple code was consulted.

Observed grammar families (all sharing the dmp2 (v,1,10,bpp) w,h header):

* v1 "raw": ``dmp2 01 01 0a bpp, w, h, pixels`` — no length field, pixels
  begin at offset 12 and run to the end of the frame.
* v3-mini (1-swatch color): ``e4 BGRA ff 38 04 <run tokens> e3 GRA ff 06
  00*7`` where the run tokens cover the byte count 4*px: first token value
  = bytes-33 (cap 255), each continuation = remaining-16 (cap 255).
  Probed range: 9..128 px (36..512 raw bytes). Frame body length L ==
  len(stream incl. the 06 + 7 trailing zeros).
* v3-mini (GA): ``98 02 g a <run tokens> e1 a 06 00*7``; tokens cover the
  byte count 2*px: first = bytes-25 (cap 255), continuations = rem-16
  (cap 255). Verified up to 3200 bytes (40x40). Mode (MLEC) stays 2 for
  opaque, 0 for translucent (gt_ oracles).
* v4-mini (1-swatch palette variant of the v4 grammar): same frame header
  as v4 palette (count=1, bpp=4, one swatch) but the LZFSE stream is
  replaced by ``68 01 00 <run tokens> <end> 06 00*7`` with PIXEL-based
  tokens: first token covers value+27 pixels for even totals, value+26
  for odd totals (probed: u16 256px -> f0 e5, c039 17x15 255px -> f0 e5),
  continuations cover value+16 (value cap 255), and a trailing remainder
  of 3..15 pixels on odd totals is emitted as a bare short token ``fX``
  covering X+2 (probed: u17 17x17 289px -> ``f0 ff f6``). End marker:
  npix even -> ``e2 00 00`` (6 sizes probed), npix % 4 == 3 -> ``e1 00``
  (probed: 255px), npix % 4 == 1 -> ``e3 00 00 00`` (probed: 289px); the
  mod-4 correlation is a two-point fit, extrapolation beyond the probed
  odd sizes 255/289 is inferred. Probed total range: 144..2304 px uniform
  color (u12..u48 oracles; 4096px u64 moves to the v4 LZFSE form). A
  remainder of 2 after the greedy split (or rem==1) cannot use the bare
  form (``f0``/``f1`` are ambiguous); we rebalance the previous long token
  instead — no Apple oracle for that split, stream stays decodable
  (documented inference).

Multi-swatch mini opcodes (e7/e8 intros, 38/28/f1/f2/f3 pattern tokens)
exist for small 2-3-swatch sources (chk04 oracle, k_/t_ probes) but their
token grammar is not fully decoded -> documented gap; we keep emitting the
(accepted) v4-LZFSE form there.

Boundary table (probed endpoints; conservative activation ranges):
  color v1-raw: px <= 8            (8 px v1, 9 px v3-mini)
  color v3-mini: 36B <= B <= 512B  (9..128 px)
  color v4-mini: px >= 144         (144..2304 px probed; 4096 px -> LZFSE)
  GA v1-raw: B <= 8                (4 px), GA v3-mini probed 32B..3200B
  Larger sources fall back to the LZFSE frames (v2/v3/v4) — Apple too.

Emitted substitutes for ranges not yet probed remain the LZFSE frames,
which assetutil/CoreUI accept everywhere (parity gap = payload bytes only).
"""
from __future__ import annotations

import struct

V3_MINI_TAIL = b"\x06" + b"\x00" * 7


def _mini_run(total: int, first_bias: int, cont_bias: int = 16, cap: int = 255,
              allow_bare: bool = False, bare_bias: int = 2) -> bytes:
    """Apple mini-RLE ``f0`` token run, emitted under a coverage model.

    Token coverage: the first long token ``f0 V`` covers V+first_bias
    units; each continuation ``f0 V`` covers V+cont_bias; values cap at
    ``cap`` (coverage cap+bias). The greedy split reproduces every probed
    Apple stream. A trailing remainder of 3..15 units may be emitted as a
    bare short token ``fX`` covering X+bare_bias (probed: v4-mini odd
    289px remainder 8 -> ``f6``) when ``allow_bare``; remainders of 1-2
    (ambiguous with the long form) are instead rebalanced into the
    previous long token split (unprobed, keeps the stream decodable).
    """
    covs: list[int] = []
    rem = total
    while rem > cap + (first_bias if not covs else cont_bias):
        c = cap + (first_bias if not covs else cont_bias)
        covs.append(c)
        rem -= c
    bare = 0
    if rem > 0:
        if rem >= cont_bias or not covs:
            covs.append(rem)
        elif allow_bare and rem > bare_bias:
            bare = rem
        else:
            # Rebalance: shrink the previous long token so the tail is a
            # 16-unit continuation (``f0 00``). Coverage is preserved.
            merged = covs.pop() + rem
            covs.append(merged - cont_bias)
            covs.append(cont_bias)
    out = bytearray()
    for i, c in enumerate(covs):
        out += bytes((0xF0, c - (first_bias if i == 0 else cont_bias)))
    if bare:
        out.append(0xF0 | (bare - bare_bias))
    return bytes(out)


def _run_read(data: bytes, offset: int, first_bias: int, cont_bias: int = 16,
              bare_bias: int = 2) -> tuple[int, int]:
    """Inverse of _mini_run. Returns (units_covered, next_offset).

    Accepts the long ``f0 V`` forms plus one trailing bare ``fX`` token
    (X >= 1) covering X+bare_bias units."""
    total = 0
    first = True
    while offset + 2 <= len(data) and data[offset] == 0xF0:
        total += data[offset + 1] + (first_bias if first else cont_bias)
        first = False
        offset += 2
    if offset < len(data) and 0xF1 <= data[offset] <= 0xFE:
        total += (data[offset] & 0x0F) + bare_bias
        offset += 1
    return total, offset


# v4-mini end markers (module docstring records the probe evidence).
_V4_END = {
    0: b"\xe2\x00\x00",
    1: b"\xe3\x00\x00\x00",
    2: b"\xe2\x00\x00",
    3: b"\xe1\x00",
}


def _header(version: int, bpp: int, width: int, height: int) -> bytes:
    return b"dmp2" + bytes((version, 1, 10, bpp)) + struct.pack("<HH", width, height)


# ---------------------------------------------------------------- v1 raw

def v1_raw(width: int, height: int, raw: bytes, bpp: int) -> bytes:
    return _header(1, bpp, width, height) + raw


# ------------------------------------------------------ v3-mini (color)

def v3_mini_color(width: int, height: int, bgra: bytes) -> bytes:
    """``bgra`` is the single premultiplied pixel (4 bytes)."""
    npix = width * height
    stream = (b"\xe4" + bgra + b"\x38\x04"
              + _mini_run(4 * npix, 33)
              + b"\xe3" + bgra[1:4] + V3_MINI_TAIL)
    return _header(3, 4, width, height) + struct.pack("<I", len(stream)) + stream


# --------------------------------------------------------- v3-mini (GA)

def v3_mini_ga(width: int, height: int, ga: bytes) -> bytes:
    """``ga`` is the single premultiplied pixel (gray, alpha)."""
    npix = width * height
    stream = (b"\x98\x02" + ga
              + _mini_run(2 * npix, 25)
              + b"\xe1" + ga[1:2] + V3_MINI_TAIL)
    return _header(3, 2, width, height) + struct.pack("<I", len(stream)) + stream


# ------------------------------------------------------------ v4-mini

def v4_mini(width: int, height: int, bgra: bytes) -> bytes:
    """1-swatch variant of the v4 palette grammar with mini-RLE stream.

    Odd pixel counts use a first-token bias of 26 (probed c039/u17), a
    bare short token for remainders 3..15, and the ``npix % 4`` end marker
    table (_V4_END); see the module docstring for probe evidence."""
    npix = width * height
    odd = npix & 1
    stream = (b"\x68\x01\x00"
              + _mini_run(npix, 26 if odd else 27, allow_bare=bool(odd))
              + _V4_END[npix & 3] + V3_MINI_TAIL)
    return (b"dmp2" + bytes((4, 1, 10, 4)) + struct.pack("<HHHH", width, height, 1, 4)
            + bgra + struct.pack("<I", len(stream)) + stream)


# ------------------------------------------------------------ decoders

def decode_mini(dmp2: bytes, width: int, height: int, bpp: int) -> bytes | None:
    """Decode the 1-swatch mini frames above. Returns premultiplied pixels
    (BGRA or GA) or None for anything outside the understood forms."""
    npix = width * height
    version = dmp2[4] if len(dmp2) >= 12 else None
    if version == 3:
        (slen,) = struct.unpack_from("<I", dmp2, 12)
        stream = dmp2[16:16 + slen]
        if len(stream) != slen or len(stream) < 12 or not stream.endswith(V3_MINI_TAIL):
            return None
        if bpp == 4:
            if stream[:1] != b"\xe4" or stream[5:7] != b"\x38\x04":
                return None
            bgra = bytes(stream[1:5])
            covered, off = _run_read(stream, 7, 33)
            if covered != 4 * npix:
                return None
            if stream[off:off + 1] != b"\xe3" or bytes(stream[off + 1:off + 4]) != bgra[1:4]:
                return None
            return bytes(bgra) * npix
        if bpp == 2:
            if stream[:2] != b"\x98\x02":
                return None
            ga = bytes(stream[2:4])
            covered, off = _run_read(stream, 4, 25)
            if covered != 2 * npix:
                return None
            if stream[off:off + 1] != b"\xe1" or stream[off + 1:off + 2] != ga[1:2]:
                return None
            return bytes(ga) * npix
        return None
    if version == 4 and bpp == 4:
        count, bppv = struct.unpack_from("<HH", dmp2, 12)
        if (count, bppv) != (1, 4):
            return None
        bgra = dmp2[16:20]
        (slen,) = struct.unpack_from("<I", dmp2, 20)
        stream = dmp2[24:24 + slen]
        if len(stream) != slen or not stream.endswith(V3_MINI_TAIL) or stream[:3] != b"\x68\x01\x00":
            return None
        body = stream[3:-8]
        covered, off = _run_read(body, 0, 26 if npix & 1 else 27)
        rest = body[off:]
        if covered == npix and rest == _V4_END[npix & 3]:
            return bytes(bgra) * npix
        return None
    return None
