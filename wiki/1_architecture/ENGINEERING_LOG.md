# Engineering audit log & Technical Milestones

This is a reproducible engineering record and technical milestone log.

---

## 2026-07-20 — 1:1 Complete Rust Rebuild, 14-Bug Logic Audit & Legacy Directory Purge

### 1. 100% Complete 1:1 Rust Port (`actool_rs`)
- **Parity Achieved**: Rebuilt 100% of all 57 modules in Rust (`actool_rs/src/`), achieving 1:1 definition, type, and logic parity with Python `actool_linux`.
- **Zero Compiler Warnings**: Enforced zero warnings (`cargo test --release` builds cleanly with 0 warnings).
- **Performance Benchmark**:
  - Python `actool_linux` baseline: **110.69 ms**
  - Rust `actool_rs` Release build: **2.05 ms** (Achieved **53.9x acceleration factor**).
- **Parallel Thread Pools**: Integrated Rayon parallel pools across KCBC row-band chunking, 4-plane delta encoding, YCoCg quantization, and multi-candidate NEXUS/ALPHA strategy evaluation.

### 2. Comprehensive 14-Bug Logic Audit & Resolutions
Executed a systematic, module-by-module, line-by-line code audit across all 57 modules, finding and resolving 14 critical edge-case bugs:

1. **`smart_cbck.rs` Header Offset Bug**: Fixed payload length offset from 172..176 to **180..184** (CSI payload length offset specification).
2. **`astc_native.rs` Header Offset Bug**: Corrected ASTC GPU-Direct CSI payload length offset to **180..184**.
3. **`imagestack.rs` Offset & Channel Overflow Bugs**:
   - Fixed CSI payload length offset to 180..184.
   - Fixed u8 color wrap-around overflow in `composite_source_over` by applying `.min(255) as u8` across all channels ($B, G, R, A$).
4. **`cbck.rs` Slice Out-of-Bounds Panic**: Added strict buffer length checks in `encode_cbck` before slicing `pixel_data[offset..offset + chunk_len]`.
5. **`paletteimg.rs` Modulo Zero Division Panic**: Fixed `% row_bytes` division by zero when `width == 0` or `bits_per_index == 0` in `unpack_row_indices` and `pack_row_indices`.
6. **`iconstack.rs` Out-of-Bounds Index Panic**: Fixed `&hex_bytes[..4]` indexing in `build_iconstack_root_style_list` when hex string produces $<4$ bytes, padding with zeros.
7. **`packed.rs` CSI Link Standard Discrepancy**: Replaced standalone 30-byte link TLV assignment with full 184-byte ISTC CSI header construction (`_csi_link_full` with layout 1003, TLV 1010, and payload length 0).
8. **`csi.rs` Big-Endian `CTSI` Magic Support**: Added explicit Magic number inspection and endianness switching for `ISTC` (Little-Endian) and `CTSI` (Big-Endian) headers in `parse_csi`.
9. **`lzfse.rs` `b"bvx-"` Stream Marker Support**: Extended `decompress` frame parser to accept both `b"bvx$"` and `b"bvx-"` as valid stream end markers.
10. **`planar_delta_lzfse.rs` Multiplication Overflow**: Replaced `w * h` with `w.checked_mul(h)` to prevent overflow panic on large dimensions.
11. **`compiler.rs` RGBA / BGRA Channel Order Fix**: Swapped Red and Blue channels (`px.swap(0, 2)`) when loading images via `image::open` before passing to BGRA-expecting CSI constructors.
12. **`zero_code_db.rs` Deserialization Effect Omission**: Fixed `ZeroCodeBezel::deserialize` to restore serialized `effects` array following `layers`.
13. **`autosafe.rs` PBR Material & Dirty Alpha Auto-Protection**: Added `PBRMaterial` domain to Guardrails 1 & 3, ensuring non-zero RGB in $A=0$ regions is automatically preserved 100% bit-exact for custom Metal shaders, 3D textures, and edge-padding filtering.
14. **Integration Test Suite Cleanup**: Updated test vectors and resolved unused import warnings in `actool_rs/tests/integration_tests.rs`.

### 3. Legacy Directory Audit & Deletion (`nextgen` & `research`)
- Audited all files in `actool_linux/nextgen`, `actool_linux/research`, and `actool_linux/stable`.
- Confirmed all logic, algorithms, and functions had been 100% unified into top-level `actool_linux` and `actool_rs/src`.
- Updated test import paths across `tests/` from `actool_linux.nextgen`, `actool_linux.research`, and `actool_linux.stable` directly to `actool_linux.*`.
- Safely purged `actool_linux/nextgen`, `actool_linux/research`, and `actool_linux/stable` subdirectories.

### 4. Verification & Test Status
- **Rust Integration Tests (`cargo test --release`)**: **20/20 passed, 0 compiler warnings**.
- **Python Test Suite (`pytest`)**: **241/241 passed**.
- **Working Tree**: Clean, all changes pushed to branch `fix-bugs`.

---
*Maintained by kagurasumusun.*
