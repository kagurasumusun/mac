# mini-workbench

Reverse-engineering workbench for the multi-swatch mini-RLE grammar used
inside `dmp2` deepmap payloads of `ZZZZPackedAsset-*` atlas renditions
(v4-mini color, v3-mini GA). These scripts compare Apple `actool` oracle
CARs against ground-truth painted planes derived from LINK rects (TLV1010),
the dmp2 palette (BGRA) and the probe-suite source PNGs.

Everything here is clean-room analysis of *observable outputs* of Apple
actool on synthetic inputs we generated; no Apple code is involved.

## Status (2026-07-17) — see MINI_ISA_NOTES.md at repo root

Solved pieces: bottom-up stream order, bottom-2-rows paint + LR halo,
BGRA palette index resolution (incl. multi-scale imagesets), leading-run
rules (first `fX` = X+9 / first `f0 V` = V+25), continuation `f0 V` = V+16,
`38 XX` row-copy LZ (dist=W, len=XX), `4N`=hi-count / `5N`=lo-count reps,
bare `fX` = zeros X+2, `eN` literals (+row-end pad at stream tail).

Open: `6N`/`f9`/`f3` row-program groups (c02/c05/m8 tall swatches), pair
token `40 U V` (m5; reverse-emit candidate), `c8`/`ce`/`30`/`fe`, section
markers `68 01 NN` beyond the first, GA multi-swatch sub-grammar.

## Files

- `mini_align.py` — loaders: probe PNG reader, `load_atlas_case` CAR →
  (W, H, palette, version, stream, LINK rects).
- `mini_corpus.py` — dumps every mini-stream atlas case across all local
  Apple corpora into `mini_corpus.json`, resolving each rect's palette
  index/GA value from source PNGs (slot/scale aware).
- `mini_fit2.py` — exact-cover aligner: per-token modes with (mostly)
  fixed families + paint grid; finds decodes consistent with painted plane.
- `mini_c02.py` — strict constrained cover for one case (broad families).
- `mini_trace.py` — per-token trace + target plane dump + first-mismatch
  report for eyeballing.
- `mini_joint.py` — earlier joint solver (superseded by mini_fit2/c02).
- `compat_stats.py` — batch diff_cars classification of all Apple-oracle
  corpora vs our outputs (exact / hash16-only / payload / struct counts).

## Expected corpus layout (paths are hardcoded for the analysis machine)

```
/home/user/work/probe5-out, probe6-out, probe3-out      Apple oracle CARs
/home/user/work/ap2-out, atlasprobe-apple-out           m1..m8 / n1..n8 oracles
/home/user/work/{probe5,probe6,probe3,atlas-probe2,atlas-probe}-suite   sources
/home/user/work/{ours-fresh5,ours-probe6-v2,ours-probe3-v2,ours-cars}   our CARs
```

Run: `python3 tools/mini-workbench/mini_corpus.py` then
`python3 tools/mini-workbench/mini_trace.py m5_trio hi`.
