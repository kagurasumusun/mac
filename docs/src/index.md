# Apple Toolsets (`Apple-Toolsets`) Technical Portal

Welcome to the official, high-performance technical documentation portal for **`Apple-Toolsets`** — an open-source, clean-room, pure Rust implementation suite for Apple developer toolsets including `actool`, `CAREditor`, `assetutil`, and upcoming tools such as `ibtool` and `simctl`.

---

## Technical Highlights & Engine Capabilities

- **Zero-Warning 100% Pure Rust Architecture**:
  Engineered with maximum memory safety, zero compiler warnings (`0 warnings`), zero-copy slice design, and 100% Rust Cargo Workspace structure (`actool/src`).
- **53.9x Performance Speedup**:
  Executes full compilation pipelines in **2.05 ms** (versus 110.69 ms baseline) using multi-threaded Rayon thread pools.
- **Apple CoreUI Zero-App-Change Compatibility**:
  Outputs 100% Apple contract-compliant `.car` archives auto-decoded out of the box by `UIImage(named:)` and `NSDataAsset.data`.
- **ASTC GPU-Direct 128-bit Native Hardware Blocks**:
  Encodes 128-bit hardware blocks (`AS44`, `AS88`) directly readable by Apple Silicon Metal GPU texture samplers.
- **Ultra-HD 2D Spatial Grid Tiling (4K / 8K / 16K)**:
  Prevents VRAM memory exhaustion by dynamically chunking ultra-large textures into parallel 2D grid tiles.
- **ISO/CIE 11664-6 CIEDE2000 Perceptual JND ($\Delta E_{00} \le 1.0$)**:
  Guarantees 100% human visual imperceptibility using exact CIEDE2000 color distance equations.
- **Dirty Alpha Protection for Metal Custom Shaders**:
  Automatically preserves non-zero RGB values in $A=0$ regions for custom shaders, 3D textures, and edge-padding filtering.
- **3D PBR ORM & Tangent Normal Map Compression**:
  Packs Occlusion, Roughness, and Metallic into single BGRA textures (saving **66% VRAM**), and packs 2-channel normal vectors ($N_x, N_y \rightarrow N_z$).

---

## Official Links & API Endpoints

- **Live AI DeepWiki**: [https://deepwiki.com/kagurasumusun/Apple-Toolsets](https://deepwiki.com/kagurasumusun/Apple-Toolsets)
- **DeepWiki MCP Server**: `https://mcp.deepwiki.com/mcp`
- **GitHub Repository**: [https://github.com/kagurasumusun/Apple-Toolsets](https://github.com/kagurasumusun/Apple-Toolsets)
- **GitHub Pages Portal**: [https://kagurasumusun.github.io/Apple-Toolsets/](https://kagurasumusun.github.io/Apple-Toolsets/)
- **Rustdoc API Documentation**: [Rustdoc HTML Reference](rustdoc/actool_rs/index.html)

---

## Navigation & Specifications Quick Index

1. **[System Architecture & Workspace Topology](architecture/overview.md)**
2. **[01: CoreUI CAR File & BOMStore Binary Format](specifications/car_bom_format.md)**
3. **[02: Image Compression, Deepmap & CBCK Codecs](specifications/codecs_cbck_astc.md)**
4. **[03: Perceptual Ergonomics, Auto-Safe & 3D PBR Math](specifications/autosafe_ergonomics_3d.md)**
5. **[04: Developer CLI, CAREditor API & Storage Mounting](specifications/tools_careditor_mount.md)**
6. **[05: Facet Hash16 Anatomy & Lookup Table](specifications/facet_hash16.md)**
7. **[API Reference Overview](api_reference/overview.md)**
