# 02: Image Compression Codecs, Deepmap & CBCK Anatomy

This document covers Deepmap `dmp2` v1–v4, DMP2 Mini ISA opcodes, CBCK `MLEC/KCBC` chunking, Ultra-HD 2D spatial grid tiling, and 128-bit native ASTC GPU-direct hardware blocks.

---

## Architecture Pipeline Diagram

![Image Compression & Ultra-HD Spatial Tiling Pipeline](../images/cbck_ultrahd_pipeline.png)

---

## 1. Deepmap (`dmp2`) Grammars & Mini ISA Opcodes

Apple CoreUI uses four `dmp2` grammars based on image complexity and size:

1. **`v1_raw`**: Uncompressed pixel pass-through for images $\le 8$ pixels.
2. **`v2_lzfse`**: Direct LZFSE frame for general continuous-tone graphics.
3. **`v3_mini`**: Compact ISA opcodes (`0x68` intro, `0xF0` zero runs, `0xE1` literals, `0x38` row copy, `0x06` tail).
4. **`v4_palette`**: 8-bit index color palette mapping with reserved Swatch 0 for transparent pixels.

---

## 2. CBCK (`MLEC/KCBC`) Chunking

Large assets and atlases are split into independent row-band chunks using `KCBC` headers under an `MLEC` envelope (Mode 3, Codec 4/11). The maximum raw chunk size cap is `0x155555` bytes (~1.39 MB).

```
+-------------------------------------------------------------------------+
| MLEC Container Header (16 Bytes)                                        |
| Magic: b"MLEC", Mode: 3 (u32), Codec: 4/11 (u32), Chunk Count: N (u32)  |
+-------------------------------------------------------------------------+
| KCBC Chunk 1 (16B Header + LZFSE Stream)                                |
| Magic: b"KCBC", Y Offset (u16), Rows (u16), Raw Len (u32), Comp Len...  |
+-------------------------------------------------------------------------+
```

---

## 3. Ultra-HD 2D Spatial Grid Tiling (4K / 8K / 16K)

For 4K/8K/16K resolutions, 1D row bands are upgraded to 2D spatial grid tiles:
- **4K Tier** ($\ge 3840 \times 2160$): $256 \times 256$ pixel grid tiles.
- **8K Tier** ($\ge 7680 \times 4320$): $512 \times 512$ pixel grid tiles.
- **16K Tier** ($\ge 15360 \times 8640$): $1024 \times 1024$ pixel grid tiles.

---

## 4. ASTC GPU-Direct 128-bit Hardware Blocks (`AS44`, `AS88`)

Native ASTC blocks (`0x5CB05C00` header magic) are loaded directly into Apple Silicon Metal VRAM without CPU decompression. Each $N \times M$ grid cell forms a 16-byte (128-bit) hardware descriptor with mode headers (`0xFC`), endpoint colors, and a 2-bit weight grid.
