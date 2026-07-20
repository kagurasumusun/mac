# Codebase Architecture & Workspace Topology

This document details the software architecture, memory management model, Rayon thread pool scheduling, and Cargo Workspace structure of `Apple-Toolsets`.

---

## 1. Workspace Layout

The project is structured as a Cargo Workspace containing tool packages:

```
Apple-Toolsets/
├── Cargo.toml               # Root Workspace ([workspace] members = ["actool"])
├── .gitignore               # Excludes /target
│
├── actool/                  # Apple Asset Catalog Compilation Tool Package
│   ├── Cargo.toml           # Package configuration
│   └── src/                 # 100% Pure Rust Architecture
│       ├── lib.rs           # Re-exports for 1:1 API Parity
│       ├── main.rs / bin/   # Executable binaries
│       ├── core/            # Low-level BOMStore, CARHeader, CSI & B-Tree binary core
│       ├── codecs/          # Rayon parallel LZFSE, CBCK, DMP2 & ASTC codecs
│       ├── safety/          # ISO/CIE 11664-6, HAS 80dB SNR & AutoSafe guards
│       ├── assets/          # Sprite Atlases, Layer Stacks, PBR 3D, Audio
│       └── tools/           # Compiler, CAREditor API, Mount & Repair
│
├── tests/
│   └── actool/              # Tool-specific integration tests (integration_tests.rs)
├── docs/                    # Source files for official mdBook site
└── scripts/                 # Utility evaluation scripts
```

---

## 2. Domain Submodules Breakdown

### 2.1 Core Domain (`actool/src/core/`)
- **`bom.rs`**: Parser for BOMStore 32-byte headers, block indexes, and variables tables.
- **`bomwriter.rs`**: Big-endian BOMStore binary allocator and builder.
- **`car.rs`**: Read-only wrapper for 436-byte `CARHEADER` and `KEYFORMAT` attributes.
- **`carwriter.rs`**: Core CAR assembler and multi-level B-Tree builder.
- **`csi.rs`**: Fixed 184-byte CSI header parser (`ISTC`/`CTSI`) and TLV stream builder.
- **`tree.rs`**: Parser for `b"tree"` descriptors and 12-byte B-Tree node headers.
- **`facet_hash_lookup.rs`**: 16-bit polynomial hash calculator and 100% exact lookup table.
- **`zero_code_db.rs`**: Serializer and deserializer for Bezel, Glyph, and Effect databases.

### 2.2 Codecs Domain (`actool/src/codecs/`)
- **`lzfse.rs`**: Pure Rust LZFSE pass-through encoder and stream decompressor.
- **`cbck.rs`**: MLEC Mode 3 Codec 4/11 CBCK chunk compressor using Rayon threads.
- **`dmp2mini.rs`**: Deepmap v1, v2, v3 (Mini ISA), and v4 palette codecs.
- **`astc_native.rs`**: 128-bit native ASTC GPU-direct hardware block encoder.
- **`ultrahd.rs`**: 2D spatial grid tiling for 4K, 8K, and 16K image assets.
- **`planar_delta_lzfse.rs`**: 4-plane color channel separation + 1D delta prediction + LZFSE.
- **`smart_cbck.rs`**: Entropy-analyzing, dirty-alpha cleaning smart CBCK encoder.

### 2.3 Safety Domain (`actool/src/safety/`)
- **`ciede2000.rs`**: ISO/CIE 11664-6:2014 CIEDE2000 ($\Delta E_{00}$) JND color difference calculator.
- **`quality_metrics.rs`**: PSNR, SSIM, and Sobel edge-preservation metrics.
- **`autosafe.rs`**: 4-gate safety barriers and automatic dirty alpha protection.
- **`psychoacoustics.rs`**: 80dB SNR HAS auditory noise floor threshold evaluator.

### 2.4 Assets Domain (`actool/src/assets/`)
- **`atlas.rs` / `packed.rs`**: Sprite atlas packing and linked rendition (`INLK`, Layout 1003) generation.
- **`appicons.rs`**: Platform-aware AppIcon size and scale ranking.
- **`imagestack.rs`**: tvOS/visionOS multi-layer icon and image stack compositor.
- **`model3d.rs`**: PBR ORM map consolidation and 2-channel tangent normal map packing.

### 2.5 Tools Domain (`actool/src/tools/`)
- **`compiler.rs`**: High-level asset catalog (`.xcassets`) compilation driver.
- **`editor.rs`**: Interactive, non-destructive CAR modification API (`CAREditor`).
- **`mount.rs`**: Virtual storage directory mounting and syncing engine.
- **`repair.rs`**: Signature-based corrupted CAR auto-repair recovery engine.

---

## 3. Parallel Execution & Memory Efficiency

1. **Rayon Work Stealing**:
   KCBC chunking, 4-plane delta encoding, and 2D spatial tiles execute in parallel using lock-free data channels across available CPU cores.
2. **Zero-Copy Slicing**:
   Slices (`&[u8]`) are passed directly throughout the pipeline to avoid unnecessary heap reallocations.
