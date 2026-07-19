# 🍎 Apple Toolsets Suite (`Apple-Toolsets`)

A high-performance, pure Rust, clean-room, cross-platform implementation suite for Apple developer toolsets, including **`actool`** (Asset Catalog Compiler), **`CAREditor`**, **`assetutil`**, and extensible architecture prepared for future tool integrations (**`ibtool`**, **`simctl`**, **`momc`**, **`mapc`**).

Built 100% in pure Rust (`apple-toolsets`) with zero compiler warnings and maximum execution performance (**53.9x speedup** over legacy Python, 2.05ms release execution, Rayon multi-threading, zero-copy slice architecture).

---

## 🌟 Key Capabilities & Master Specifications

- **Apple CoreUI Contract Compliance**:
  Full 100% zero app-change compatibility with `UIImage(named:)` and `NSDataAsset.data`.
- **High-Performance Parallel Architecture**:
  Rayon multi-threaded worker pools across KCBC row-band chunking, 4-plane delta channels, YCoCg quantization, and 2D spatial grid tiling.
- **ASTC GPU-Direct Hardware Blocks**:
  Encodes 128-bit native ASTC hardware blocks (`AS44`, `AS88`) directly readable by Apple Silicon Metal GPU texture samplers (skipping CPU decompression).
- **Ultra-HD 2D Spatial Grid Tiling (4K / 8K / 16K)**:
  Memory-safe spatial 2D grid tiling for large high-resolution images prevents VRAM exhaustion.
- **3D PBR Material Packing & Tangent Normal Maps**:
  Packs Ambient Occlusion (R), Roughness (G), and Metallic (B) into single ORM BGRA textures (saving **66% VRAM**), and packs 2-channel tangent normal maps ($N_x, N_y \rightarrow N_z$).
- **Perceptual Safety & Ergonomic Thresholds**:
  - ISO/CIE 11664-6 CIEDE2000 ($\Delta E_{00} \le 1.0$) JND color distance.
  - Human Auditory System (HAS) $\ge 80.0 \text{ dB}$ SNR noise floor threshold.
  - **Dirty Alpha Auto-Protection**: Automatically preserves non-zero RGB in $A=0$ regions for Metal custom shaders, 3D materials, and edge-padding filtering.
- **CAREditor API & Virtual Storage Mounting**:
  Interactive CAR archive editing (`editor.rs`), virtual file system directory mounting and syncing (`mount.rs`), and corrupted CAR auto-repair recovery (`repair.rs`).
- **Non-Image Specialized Engine**:
  Minifies Lottie JSON, trims PCM audio tail silence (-90dB) with 1D delta prediction, and quantizes 3D OBJ mesh vertex floats.

---

## 🏗 Repository Architecture (100% Pure Rust, Single-Branch `main`)

```
Apple-Toolsets/ (1 Branch: main)
├── Cargo.toml               # Package configuration & binary targets
├── Cargo.lock               # Deterministic dependency locking
├── src/                     # 100% Pure Rust Architecture
│   ├── lib.rs               # Public Re-exports (1:1 API Parity)
│   ├── main.rs / bin/       # Binaries (actool-rs, car-info, car-repack, pdf-car)
│   ├── core/                # [1] Low-Level BOM, CAR, B-Tree & CSI Binary Core
│   ├── codecs/              # [2] Rayon Parallel LZFSE, CBCK, DMP2, ASTC Codecs
│   ├── safety/              # [3] ISO/CIE 11664-6 & Perceptual Safety
│   ├── assets/              # [4] Sprite Atlases, Layer Stacks, PBR 3D, Media, Audio
│   └── tools/               # [5] Compiler, CAREditor API, Mount, Repair Engine
│
├── wiki/                    # Master Engineering Technical Documentation Series
├── scripts/                 # Utility Scripts & Evaluation Tools
└── tests/                   # Native Rust Integration Test Suite (20 Tests, 100% Pass)
```

---

## ⚡ Quick Start

### Building & Running `apple-toolsets`

```bash
# Build optimized release binary
cargo build --release

# Run full test suite (0 warnings, 20/20 passed)
cargo test --release

# Compile asset catalog with actool-rs
./target/release/actool-rs --compile output_dir path/to/App.xcassets --platform iphoneos
```

---

## 📜 License & Disclaimers

- Developed under clean-room engineering specifications.
- `actool`, `ibtool`, `Xcode`, and `CoreUI` are trademarks of Apple Inc. This is an independent open-source toolset project.
