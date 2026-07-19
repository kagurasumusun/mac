# 🍎 Apple Toolsets (`Apple-Toolsets`) Technical Knowledge Base (Wiki)

Welcome to the definitive engineering technical wiki for the `Apple-Toolsets` high-performance, 100% pure Rust Apple Developer Toolset compilation engine suite.

This knowledge base provides an exhaustive, byte-level specification of Apple CoreUI `.car` archives, BOMStore container binary layouts, CoreStructuredImage (CSI) headers, ASTC GPU-direct hardware blocks, ISO/CIE 11664-6 CIEDE2000 perceptual color mathematics, human ergonomics, multi-threaded Rayon parallelism, and non-image asset optimization algorithms.

---

## 🌟 Architecture & Key Specifications

- **[🏗 Codebase Architecture & Module Relations](CODEBASE_ARCHITECTURE.md)**: Exhaustive breakdown of all Rust modules, Rayon thread pool mappings, zero-copy slice architecture, and Apple contract compliance.
- **[🤖 AI Agent & Handoff Specifications](AGENT_HANDOFF_LOG.md)**: Context, state logs, and system operational invariants.

---

## 📚 Deep Technical Specifications & Whitepapers (1:20 Master Series)

### 1. Core Format & Storage
- **[📦 01: CoreUI CAR File & BOMStore Architecture](6_algorithmic_research/01_CAR_AND_BOM_FORMAT.md)**:
  Byte-by-byte specification of the 32-byte `BOMStore` header, block indexes, variables tables, 436-byte `CARHEADER` (`CTAR`/`RATC`), 12-byte `b"tree"` B-Tree descriptors, 12-byte leaf headers, `KEYFORMAT` attributes mapping (0–27), and the 184-byte `CoreStructuredImage` (CSI) fixed header with TLVs.

### 2. Compression Codecs & Ultra-HD Spatial Tiling
- **[🖼 02: Image Compression, Deepmap & CBCK Anatomy](6_algorithmic_research/02_IMAGE_COMPRESSION_AND_CBCK.md)**:
  Complete grammar analysis of Deepmap (`dmp2` v1/v2/v3/v4), DMP2 Mini ISA opcodes (RLE, literals, row copy, end markers), MLEC Mode 3 Codec 4/11 CBCK (`KCBC` chunks), Ultra-HD 4K/8K/16K spatial 2D grid tiling, and 128-bit ASTC GPU-Direct hardware blocks (`AS44`, `AS88`).

### 3. Perceptual Ergonomics, Auto-Safe Guards & 3D Assets
- **[🚀 03: Beyond God-Mode: Ergonomics, Auto-Safe Protection & 3D PBR](6_algorithmic_research/03_BEYOND_GODMODE_ALGORITHMS.md)**:
  ISO/CIE 11664-6 CIEDE2000 ($\Delta E_{00} \le 1.0$) JND color mathematics, 80dB HAS psychoacoustic noise floor thresholds, `AutoDomainDetect` 4-gate safety barriers, **Dirty Alpha Protection** (preserving $A=0$ non-zero RGB for Metal shaders and edge-padding filtering), PBR 3D ORM texture packing (66% VRAM reduction), and 2-channel tangent normal map packing ($N_x, N_y \rightarrow N_z$).

### 4. Developer Tools, CAREditor & Non-Image Optimizers
- **[🛠 04: CLI Tools, CAREditor API, Virtual Mounting & Non-Image Engine](6_algorithmic_research/04_TOOLS_AND_CLI.md)**:
  `actool-rs` / `apple-toolsets` CLI interfaces, `CAREditor` interactive CAR modification API, virtual directory mounting & syncing (`mount.rs`), corrupted CAR auto-repair engine (`repair.rs`), deterministic heuristic strategy selection (no external AI weight dependencies), Lottie JSON float truncation, PCM audio tail silence trimming (-90dB) with 1D sample delta prediction, and 3D OBJ mesh vertex float quantization.

### 5. Algorithmic Hash Analysis
- **[🧩 05: Facet Hash16 Anatomy & The 100% Accuracy Lookup Table](6_algorithmic_research/05_FACET_HASH16_ANATOMY.md)**:
  Exhaustive analysis of Apple's non-public 16-bit polynomial hash algorithm and the 100% exact lookup table mapping for string facet keys.

---

## 📊 Status & Audits

- **[📝 Final Status Report](3_progress_and_status/FINAL_STATUS.md)**: 100% Pure Rust migration certification, 0 compiler warnings, 20/20 test pass verification, and clean single-branch `main` status.
- **[📜 Engineering Log](1_architecture/ENGINEERING_LOG.md)**: Engineering audit, 53.9x Rust speedup benchmarks, and logic-by-logic bug hunt fixes.
- **[📊 Deep Research Data Index](5_research_reports/INDEX.md)**: Census data, oracle matrices, and verification outputs.

---
*Maintained by kagurasumusun — July 2026.*
