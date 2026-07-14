# Engineering audit log

This is a reproducible engineering record, not a private chain-of-thought transcript.

## 2026-07-12 — CoreUI/BOM/CAR baseline

- Identified BOMStore container, block index, named variables and leaf trees.
- Implemented bounds checks, CARHEADER, KEYFORMAT, FACETKEYS, CSI/TLV parsing.
- Repacked an Apple CAR on Linux; Apple `assetutil` accepted it.

## Independent renditions

- RAWD data: `assetutil` and `NSDataAsset` passed.
- JPEG RAWD: `assetutil` and `NSImage` passed.
- HEIF RAWD: ISO BMFF `ftyp`/`ispe` parser; `assetutil` and `NSImage` passed.
- COLR sRGB and Display P3: `assetutil` and `NSColor` passed.
- Mixed multi-asset CAR: data/JPEG/color loaded in one AppKit process.

## Multi-Xcode matrix

- 20 installed Xcode app bundles/aliases, five SDK families, 100 rows.
- Apple actool oracle: 60 passes; failures were mostly old-runtime build mismatch; two xros timeouts.
- Linux mixed CAR consumer matrix: 100/100 `assetutil` passes across Xcode 16/26 and macOS/iOS/tvOS/watchOS/visionOS SDKs.
- actool contract: common help hash in observed installs; unknown/no-input exit 1.

## PDF/vector

Observed Xcode preserved-vector asset as three renditions:

1. PDF vector: pixel format `PDF `, layout 9, flags 4, rendition part 42.
2. GA8/deepmap2 bitmap fallback at 1×, image part 181.
3. GA8/deepmap2 bitmap fallback at 2×, image part 181.

A Linux vector-only CAR passed `assetutil` but not AppKit lookup. After adding part-42 PDF plus part-181 GA8 deepmap fallbacks at scale 1/2, the Linux CAR passed `assetutil` and AppKit (`NSImage`, TIFF length 29820). Optional scale 3 was then added and recognized by iOS SDK `assetutil` alongside scales 1/2 and vector. The dedicated `actool-pdf-car` command accepts pre-rasterized fallback PNGs.

## PNG/deepmap2 verified GA8 subset

Input constraint: non-interlaced, 8-bit grayscale-alpha PNG. General width/height supported with PNG filters 0–4.

Observed and reproduced rendition:

- CSI pixel format `GA8 `, layout 12, flags 16.
- `MLEC` envelope version 2.
- inner codec magic `dmp2`.
- little-endian width/height in dmp2 header.
- pixel bytes are premultiplied grayscale and alpha: `(gray * alpha + 127) // 255`.
- oracle matches recorded for 1×1, 2×1, 1×2, 2×2, 3×2 and 10×10.

Exact payload for black/opaque fixture:

```text
4d4c4543020000000b0000001e00000001000000020000000e00000000000000
646d703201010a020100010000ff
```

Validation:

- Apple `assetutil`: `Compression=deepmap2`, `Encoding=Gray`, 1×1.
- AppKit `NSImage(named:)`: 1×1 and TIFF representation generated.

RGBA rule was subsequently identified: premultiply each RGB channel, store bytes in BGRA order, use dmp2 bpp=4 and CSI format ARGB. Opaque RGB uses B,G,R,FF and CLEM mode 2. Indexed PNG depth 1/2/4/8 is expanded via PLTE/tRNS to ARGB dmp2. 16-bit GA uses the high byte of each sample before GA8 premultiplication. Oracle and AppKit passed these paths at 2×2. Palette probe: Xcode 16.0/16.4/26.3, sizes 2/16/64/256, opaque/tRNS — all 24 outputs were deepmap2/ARGB; no installed Xcode emitted legacy palette-img.

Large indexed dmp2 payloads contain palette metadata followed by an LZFSE `bvx2` stream. The stream was decompressed on Linux to the full 65536-byte index plane. The optional `lzfse>=0.4` writer backend emits palette BGRA + compressed index streams. Apple validation on macOS 26.4 / Xcode 26.5: `bvx2` at offset 68, `assetutil` reported deepmap2/ARGB 64×64 SizeOnDisk 630, and AppKit `NSImage(named:)` loaded it with TIFF length 31268.

## Git push

Repeated `git push origin main` attempts returned HTTP 403 for `github-actions[bot]`. The workflow token needs `permissions: contents: write` or another write-capable credential.

## 2026-07-13 — Adam7 and same-facet multi-scale deepmap milestone

### Implementation
- Added bounds-checked Adam7 pass reconstruction for supported PNG inputs.
- Each pass is independently unfiltered with PNG filters 0–4; empty passes are omitted as required by the PNG specification.
- Interlaced 8-bit RGB/GA/RGBA, 16-bit GA, and indexed 1/2/4/8-bit inputs now feed the existing verified deepmap2 writer.
- Generalized `build_assets_car` so several renditions can share one facet name and stable identifier.
- Added 1x/2x/3x scale selection to PNG/JPEG/HEIF rendition constructors and synchronized CSI scale and rendition key scale.
- Duplicate CoreUI rendition keys and inconsistent facet parts are rejected.

### Reproducible tests
- Linux unit suite: `PYTHONPATH=src python -m unittest discover -s tests -q` → 36 tests, OK.
- Apple host: macOS 26.4 (25E246), Xcode 26.5 (17F42).
- Linux-generated mixed CAR contained Adam7 3×3 and a single `Logo` facet with 1× and 2× deepmap renditions.
- `xcrun --sdk macosx assetutil --info` recognized all three as `Compression: deepmap2`, with Logo scale values 1 and 2.
- AppKit main-bundle consumer output:
  - `APPLE_CONSUMER_PASS Adam7 3 3 6796`
  - `APPLE_CONSUMER_PASS Logo 1 1 9458`

### Boundary
This validates CAR parsing and AppKit consumption on the stated Apple host. It does not yet establish byte-identical actool output, idiom/appearance selection, legacy palette-img, packed atlas, or Simulator coverage.

## 2026-07-13 — Multi-level BOM B+ tree and AppIcon oracle

### Multi-level tree oracle
- Generated 5,000 independent image facets with Xcode 26.5 `actool` on macOS 26.4.
- Apple output: 2.6 MiB CAR; RENDITIONS root type 0 with 15 separators and 16 children; FACETKEYS root type 0 with 18 separators and 19 children.
- Confirmed internal representation: header `>HHII`, then N `(child block, separator key block)` pairs, then one final child `u32`. Therefore N keys partition N+1 children.
- Implemented recursive traversal with depth limit, cycle/shared-node detection, block bounds checks, separator resolution, final-child validation and descriptor path-count validation.
- Parsed the Apple oracle completely: `APPLE_MULTILEVEL_PASS 5001 5000 5001 A00000 A04999`.
- Unit suite now has 38 passing tests, including a synthetic internal-node fixture and cycle rejection.

### iOS AppIcon oracle
- Compiled a modern universal 1024×1024 AppIcon for `iphoneos`, target 15.0.
- actool emitted `Assets.car`, `AppIcon60x60@2x.png`, `AppIcon76x76@2x~ipad.png`, and partial-info plist entries for phone/iPad.
- AppIcon key format adds scale(12), idiom(15), subtype(16), dimension2(9), identifier(17), element(1), and part(2).
- Idiom IDs observed: phone=1, pad=2. Image part=220; auxiliary MSIS part=218. Facet part=220.
- 1024 image CSI: ARGB layout 12; rendition starts MLEC mode 3, codec 4, CBCK, followed by an LZFSE `bvx2` stream. This differs from the existing deepmap2 codec and remains oracle-gated until CBCK semantics are independently reproduced.
- Partial plist includes `CFBundleIconName=AppIcon`, phone `AppIcon60x60`, and iPad `AppIcon60x60`/`AppIcon76x76`.

## 2026-07-13 — iOS idiom and dark-appearance writer

- Built an Xcode 26.5 oracle containing universal 1×/2×, iPhone, iPad, and dark variants.
- Observed iOS image KEYFORMAT `(appearance=7, localization=13, scale=12, idiom=15, subtype=16, identifier=17, element=1, part=2)`.
- Observed values: universal=0, phone=1, pad=2; any appearance=0, `UIAppearanceDark`=1.
- APPEARANCEKEYS is a variable-key tree mapping `UIAppearanceAny`→little-endian u16 0 and `UIAppearanceDark`→u16 1.
- Extended `AssetRendition` and `png_rendition` with checked idiom and appearance selectors. The writer dynamically emits the iOS key format and APPEARANCEKEYS registry.
- Apple `assetutil` recognized the independent output's `Appearances` registry, universal/phone/pad idioms, dark rendition, and all payloads as deepmap2.
- Unit suite: 39 tests OK.

## 2026-07-13 — CBCK reverse engineering and independent AppIcon writer

### Oracle structure
Xcode 26.5's 1024×1024 opaque RGB AppIcon produced MLEC mode 3 / codec 4. The payload is:

```text
"MLEC" + u32(mode=3) + u32(codec=4) + u32(chunkCount)
repeat chunkCount:
    "KCBC"                 # reversed FourCC CBCK
    u32 reserved0 = 0
    u32 reserved1 = 0
    u32 rowCount
    u32 compressedLength
    independent LZFSE stream (bvx2 ... bvx$)
```

The oracle had four streams at offsets 36, 1031, 2026 and 3021. Row counts were 341, 341, 341 and 1; each full chunk decompresses to `1024 * 341 * 4 = 1,396,736` premultiplied BGRA bytes. Total reconstructed bytes are 4,194,304. Source RGB `20 60 a0` reconstructed as BGRA `a0 60 20 ff`.

### Implementation
- Added bounds-checked PNG → premultiplied BGRA conversion.
- Added chunked CBCK writer with independent optional-`lzfse` streams and an inferred Xcode chunk cap of `0x155555` raw bytes.
- Added MLEC mode 3 / codec 4 envelope.
- Added modern iOS AppIcon builder with phone/pad part-220 CBCK renditions, part-218 MSIS auxiliary renditions, dimension2 keys, and facet part 220.
- Added a 9-attribute AppIcon KEYFORMAT including `kCRThemeDimension2Name`.

### Verification
- 40 unit tests pass with LZFSE enabled.
- Local 1024 fixture: four chunks `[341,341,341,1]`, reconstructed 4,194,304 bytes, exact BGRA first pixel `a06020ff`.
- Apple Xcode 26.5 `assetutil` accepted the independently generated CAR and reported both phone and pad renditions as `Compression: lzfse`, `Encoding: ARGB`, 1024×1024, plus both MSIS records.
- An iOS 26.2 Simulator consumer test app was built and signed, but CoreSimulator boot stalled in this runner; no Simulator consumer pass is claimed for this milestone.

## 2026-07-13 — CBCK parser and iOS Simulator consumer validation

- Added a standalone bounds-checked `parse_cbck` reader with MLEC mode/codec checks, chunk-count limits, KCBC magic checks, row and compressed-length validation, trailing-byte rejection, and independent LZFSE decompression.
- Parsed the Apple AppIcon oracle into 4 chunks `[341,341,341,1]` and reconstructed all 4,194,304 BGRA bytes.
- Added `cbck_png_rendition` for ordinary part-181 image assets, allowing CBCK itself to be tested separately from AppIcon's special lookup semantics.
- Built, signed, installed and launched an arm64 UIKit app in the iOS 26.2 iPhone 17 Pro Simulator. `UIImage imageNamed:@"CBCKImage"` loaded the independent 1024×1024 CBCK CAR and wrote: `CBCK_SIM_PASS 1024 1024`.
- `UIImage imageNamed:@"AppIcon"` returned nil for both the Apple oracle and independent AppIcon CAR, confirming that AppIcon is not a valid ordinary named-image consumer test. The ordinary CBCK rendition is the positive decoder test.
- Test suite: 43 tests OK.

## 2026-07-13 — Integrated AppIcon CLI and high-contrast appearance

### AppIcon CLI
- `actool-linux ... --app-icon AppIcon --output-partial-info-plist ...` now consumes a modern single-source AppIcon set and emits all of: `Assets.car`, `AppIcon60x60@2x.png`, `AppIcon76x76@2x~ipad.png`, and the partial plist.
- Added deterministic pure-Python RGBA PNG resizing/encoding for 120×120 and 152×152 compatibility sidecars.
- Partial plist now includes `CFBundleIconName`, phone `AppIcon60x60`, and iPad `AppIcon60x60`/`AppIcon76x76` arrays.
- Apple verification: `sips` reported exact 120×120 and 152×152 dimensions; `plutil` accepted all icon dictionaries; `assetutil` accepted the CAR's phone/pad 1024×1024 ARGB/LZFSE and MSIS records.

### High contrast
- Xcode oracle maps `UIAppearanceHighContrastAny` to appearance ID 2 and uses a registry containing Any=0 and HighContrastAny=2.
- Generalized APPEARANCEKEYS allocation for arbitrary enabled Any/Dark/HighContrast records.
- `png_rendition(..., appearance="high-contrast")` emits ID 2.
- Apple assetutil recognized the independent registry and rendition as `UIAppearanceHighContrastAny`.
- Unit suite: 45 tests OK.

## 2026-07-13 — Legacy palette capability audit

The Xcode macOS AssetRuntime CoreUI binary was inspected only through observable `strings` output; no binary or private implementation is redistributed. Xcode 26.3 and current Xcode 26.5 both retain all of the following evidence:

```text
palette-img
allowsPaletteImageCompression
setAllowsPaletteImageCompression:
_allowsPaletteImageCompression
allowsDeepmap2ImageCompression
setAllowsDeepmap2ImageCompression:
CUIUncompressDeepmap2ImageData
CBCK
lzfse
kCoreThemeCompressionTypeLossless/Lossy/None/GPUOptimized...
```

Conclusion: current CoreUI still contains legacy `palette-img` recognition and a palette-compression enable/disable capability, so legacy consumer compatibility has not been completely removed. However, 24 controlled indexed-PNG actool builds across Xcode 16.0/16.4/26.3 all selected deepmap2, and the current `actool --help` exposes no palette toggle. Thus the legacy encoder path is retained but not proven reachable through the public actool CLI. Writer implementation remains oracle-gated until an actual palette-img CSI fixture is obtained.

Added `tools/coreui_capabilities.py`, which records binary path, size, SHA-256, matched observable capability strings, and explicit legacy evidence as reproducible JSON without copying framework contents.

## 2026-07-13 — Multi-level B+ tree writer

Implemented deterministic arbitrary-depth BOM B+ tree emission using reserved/stable block IDs. Verified layout details against the 5,000-facet Apple oracle:

- leaf: header, N value/key pairs, reserved u32, inline keys, padding;
- internal: header with N separators, N `(child,max-key)` pairs, final N+1 child u32, inline separator keys (no reserved u32), padding;
- each separator is the maximum key of its left child;
- forward/backward leaf links are emitted;
- upper levels are recursively grouped when necessary.

Large catalogs now switch to true multi-level RENDITIONS and FACETKEYS trees. BITMAPKEYS retains a large leaf because its numeric internal-key semantics differ. A 140-facet/140-rendition independently generated CAR had non-leaf roots for both main trees. Xcode 26.5 `assetutil` returned RC=0, all 140 names, and zero CoreUI size warnings. Unit suite: 46 tests OK.

## 2026-07-13 — Numeric BITMAPKEYS and localization writer

### Numeric BITMAPKEYS
Apple's 5,000-facet oracle showed numeric internal nodes use 63 `(child,numeric-separator)` pairs, a final child u32, no inline separator bytes, and fixed 1024-byte nodes. Leaves contain `(value block,numeric key)` pairs and links. Implemented this separate numeric path. A 140-facet CAR now has internal roots for RENDITIONS, FACETKEYS and BITMAPKEYS; Xcode 26.5 assetutil returned RC=0, all 140 names and zero warnings.

### Localization
Located a real LOCALIZATIONKEYS oracle in the macOS SFSymbols CoreGlyphs CAR. It is a variable-length tree mapping BCP-47-like tags (`ar`, `ja`, `zh-Hans`, `zh-Hant`, etc.) to little-endian u16 IDs. Added localization names to AssetRendition, deterministic collision-checked IDs, LOCALIZATIONKEYS emission for small and large catalogs, and `png_rendition(..., localization="ja")`. Apple assetutil recognized the independent registry and displayed localized `ja` and `ar` rendition names. Test suite: 47 tests OK.

## 2026-07-13 — SVG preserved vector and automatic fallbacks

Xcode 26.5 oracle established SVG vector CSI: part 42, pixel format `SVG `, layout 9, flags 4, RAWD payload; fallback part 181 renditions use deepmap2, flags 276, scales 1/2/3 and intrinsic raster sizes. Implemented validated SVG preservation, optional CairoSVG rasterization, automatic 1x/2x/3x deepmap fallbacks, direct API and catalog compiler integration. Apple assetutil recognized the independent part-42 rendition as Vector and all fallback dimensions/compression. AppKit main-bundle consumer loaded it: `SVG_APPKIT_PASS 10 20 50600`. Added optional `svg` and `all` dependencies. 48 tests OK.

## 2026-07-13 — Launch image CLI

Xcode 26.5 oracle showed legacy launch-image catalogs do not produce Assets.car for the tested iPhone 7.0 portrait 2x entry; they emit `Launch-700@2x.png` as an external sidecar. Added `--launch-image`, set discovery/diagnostics, minimum-system-version/scale/idiom filename mapping, and exact source preservation. Apple and Linux outputs had identical SHA-256 `1abf95e1...c32eddf`; `cmp` returned `LAUNCH_BYTE_PASS`. iPad `~ipad` naming and 1x/2x/3x suffix rules are implemented. 49 tests OK.

## 2026-07-13 — Cross-platform idioms and thinning selector

- Oracle observation: Xcode 26.5 watchOS ordinary image keys use idiom numeric ID 5 and include deployment-target key variants.
- Implemented checked CoreUI idiom mapping: universal=0, phone=1, pad=2, tv=3, car=4, watch=5, marketing=6, mac=7, vision=8.
- Implemented `ThinningOptions` / `thin_renditions` with idiom, scale, appearance, and localization selection, retaining universal/Any/unlocalized fallbacks by default.
- Added deterministic EXTENDED_METADATA thinning-argument emission.
- Linux test result: 52 tests, OK.
- Apple Xcode 26.5 `assetutil -I` result for independently written nine-idiom CAR: exit 0; labels recognized as `universal`, `phone`, `pad`, `tv`, `car`, `watch`, `marketing`, `mac`, and `vision`.
- Focused remote tests: 3 tests, OK. Full bare-system remote suite had expected optional-dependency failures because that Python lacks lzfse/cairosvg; these are environment failures, not regressions.

## 2026-07-13 — Symbol vector CAR writer

- Parsed the 153 MiB macOS CoreGlyphs `Assets.car`: 8,303 facets and 174,290 renditions.
- Observed symbol vectors use part 59, pixel format `SVG `, CSI layout 1017, flags 4, glyph-weight/glyph-size key attributes, and TLVs 1018/1019. Packed raster fallbacks use GA8 layouts 1003/1004.
- Added the complete 16-field symbol KEYFORMAT and symbol fields to the rendition intermediate representation.
- Added `symbol_rendition` / `build_symbol_car`, layout-1017 CSI, neutral bounded metrics, symbol-info TLV, and `.symbolset` `symbols` discovery/compiler integration.
- Apple Xcode 26.5 `assetutil -I` accepts the independent CAR and reports `AssetType: Vector Glyph` for `Glyph`.
- Local suite: 53 tests, OK; focused remote symbol test: OK.

## 2026-07-13 — Packed atlas writer and INLK metadata

- Parsed CoreGlyphs layout-1003 linked records and layout-1004 `ZZZZPackedAsset` pages.
- Reverse engineered TLV 1010: `KLNI`, version, x/y/width/height, reserved u16, `(attribute,value)` u16 tokens, zero terminator. Oracle bytes round-trip exactly.
- Implemented bounds-checked parser/writer, deterministic shelf packing, RGBA page composition, empty linked CSI records, and shared deepmap atlas page generation.
- Apple Xcode 26.5 `assetutil -I` accepts the independent output: `One`/`Two` are `Image`; the shared page is `PackedImage` at 8x4 pixels.
- Suite: 55 tests OK; focused remote atlas tests: 2 OK.

## 2026-07-13 — Multi-weight symbols and platform AppIcons

- Added SF Symbols template expansion for nine weights (`Ultralight`..`Black`) and S/M/L sizes. Groups such as `Regular-M` and `Bold-L` become distinct part-59 layout-1017 Vector Glyph renditions.
- Added platform AppIcon idiom selection: iOS phone+pad, tvOS tv, watchOS watch, macOS mac, visionOS vision, including simulator aliases.
- Apple Xcode 26.5 `assetutil` accepted all independently generated CARs. tv/watch/mac/vision each report `Icon Image` with `lzfse` plus `MultiSized Image` under the correct idiom. A two-weight template reports two `Vector Glyph` renditions.
- Local suite: 57 tests OK.

## 2026-07-13 — Layered icons, watch complication keys, sidecar manifests

- Added layer-key renditions and `build_layered_icon_car` for tvOS and visionOS; Xcode 26.5 assetutil reports two Image records with idiom tv/vision and Layer 1/2.
- Added watch complication subtype renditions; assetutil reports watch idiom with Subtype 1/2.
- Added compatibility sidecar manifests: 13 iOS/iPad PNGs, 9 watchOS PNGs, and 10 macOS PNGs. tvOS/visionOS remain layered in CAR and are intentionally not flattened.
- Local suite: 62 tests OK.

## 2026-07-13 — Fast-path runtime inventory and CLI contracts

- Added `tools/simulator_runtime_matrix.py`: inventories every runtime and optionally creates/boots/cleans one compatible device per runtime, persisting partial JSON after every attempt.
- Current Xcode 26.5 host inventory: 12 available runtimes — iOS 26.2/26.4.1/26.5, tvOS 26.2/26.4/26.5, watchOS 26.2/26.4/26.5, visionOS 26.2/26.4.1/26.5.
- Full boot pass was deferred after Simulator shutdown exceeded 30 seconds, per user request to postpone slow work. The inventory result is verified; display-consumer claims were not upgraded.
- Added CLI parsing and writer integration for target-device, device model/OS filters, product type, development region, PNG compression, and on-demand-resource switches. Single target-device selection is connected to deterministic thinning and records arguments in EXTENDED_METADATA.
- Suite: 64 tests OK.

## 2026-07-13 — Explicit depth/family focused Apple verification

On fresh macOS 26.4 / Xcode 26.5 (17F42), the latest source ZIP was transferred by SCP and seven dependency-free focused tests passed. Independently generated CARs were accepted by `assetutil -I`:

```text
Depth: vision, Layer 1, Dimension2 10
Depth: vision, Layer 2, Dimension2 20
Comp: watch, Subtype 4 (graphicCircular), Dimension2 2 (foreground)
Comp: watch, Subtype 7 (graphicRectangular), Dimension2 3 (mask)
```

This verifies serialization and Apple CoreUI key recognition. It does not prove that private compositor semantics use the same family/role/depth registry.

## 2026-07-13 — Optional-dependency-stable test suite

Tests that require `lzfse` or `cairosvg` now use explicit unittest skips when those optional packages are absent. Minimal environments therefore test the dependency-free CAR core instead of reporting false regressions. Current minimal result: 64 tests OK, 6 skipped. Full optional-dependency environment previously ran all 64 without skips.

## 2026-07-13 — Byte-identical no-input diagnostic

Added `--output-format xml1` and Apple-style result plist serialization. Xcode 26.5 oracle and actool-linux now emit byte-identical output for compile-with-no-input when platform and deployment target are supplied.

```text
SHA-256 both: d9b8569f9181e8b46f658048b5df5043d977568dcf0aec455004a283c9091f8f
cmp exit: 0
Description: Not enough arguments provided; where is the input document to operate on?
```

This is one exact contract; the full diagnostics corpus remains incomplete.

## 2026-07-13 — Four byte-identical Xcode 26.5 CLI contracts

Added Apple XML result-plist output, version output, failure-reason fields, and missing-input preflight notices. Four complete stdout plist files now compare byte-for-byte with Xcode 26.5:

```text
no input:        d9b8569f9181e8b46f658048b5df5043d977568dcf0aec455004a283c9091f8f
--version:       e325b8dd7f9a54f2fa97fb4653de29e921b55bc76fc68702d5c39373925c4493
missing catalog: 1a4abd16bb6775a1bb2eaf67de208780882a35d1baba04887ac842edda64fbc8
missing platform:7b3457836d8b694d40e4eceb3fcdbf3e78eb140164e000bf2ead61f43588681c
```

Each `cmp` returned 0. The full malformed-catalog/option cross-product remains incomplete.

## 2026-07-13 — Diagnostic corpus expansion and all observed version plists

Installed optional `lzfse>=0.4` and `cairosvg>=2.7`; full suite runs without skips. Added an Xcode 26.5 oracle probe for malformed JSON, missing images, duplicate slots, unsupported idioms, AppIcon preflight/dimensions/empty roles, unknown options, stderr, exit codes, and output ordering.

The following additional stdout plists are byte-identical to Xcode 26.5 (`cmp=0`):

```text
unknown option:           e9a0dc0fd720cbfad80c970ac78d4266a9519a930a700c348d027bb654a7a098
malformed Contents.json:  406a10175a028f6bd776b0063033f74c85ec4f01d7f2733992b8941f56ad6f7a
missing image:            7795bc89043b7ec4f7a0c6503155701dcd88bfa65cda377ec85dd512dd6961b6
unsupported idiom:        7795bc89043b7ec4f7a0c6503155701dcd88bfa65cda377ec85dd512dd6961b6
AppIcon partial required: d5e45974c720842cca3c60e4ed33dfc4a09d7db1896c88dbdbf2e6fcbd2d0540
```

Combined with prior work, nine focused Xcode 26.5 contracts are byte-identical. Duplicate slots now compile deterministically; malformed/ignored content follows Apple's notice/empty-results ordering. AppIcon actual-size validation emits Apple's generic no-applicable-content error once partial-info output is supplied.

Generated `xcode-actool-version-matrix.json` from 20 installed aliases. `--version --output-format xml1 --compatibility-xcode-version VERSION` is byte-identical for all ten distinct observed releases: 16.0-16.4, 26.0.1, 26.1.1, 26.2, 26.3, and 26.5. Current suite: 74 tests OK, no skips.

## 2026-07-13 — Path-normalized diagnostics and catalog slot integration

Expanded `tools/diagnostic_probe_matrix.py` to preserve raw stdout/stderr bytes and SHA-256 while also producing a deterministic `<ROOT>`-normalized plist. The Xcode 26.5 probe now covers duplicate slots, invalid scale/size fields, two-error ordering, fixed-path AppIcon dimensions/empty roles, and a requested-but-absent AppIcon.

Observed and implemented:

- Invalid image scale `4x` is silently dropped; result is an empty compilation-results list.
- An arbitrary `size` field on an ordinary image set is ignored.
- Malformed sets are ordered lexically (`A.imageset`, then `Z.imageset`).
- Empty AppIcon roles exit 0 and list only the partial plist.
- A missing requested AppIcon is a deferred error: unrelated `Assets.car` and the partial plist are still produced, in that order.
- Exact Xcode message contains two spaces before the quoted missing icon name.
- Ordinary PNG catalog compilation now propagates the declared 1x/2x/3x scale and idiom into CAR keys; JPEG/HEIF propagate scale.

Seven additional fixed-path result plists compare byte-for-byte, bringing the focused Xcode 26.5 total to 16. New raw SHA-256 values:

```text
duplicate slot:       219bf71fe262b330738a69ec66302b66ccb9e466bce1a844f18ef021e3d259f6
invalid scale:        7795bc89043b7ec4f7a0c6503155701dcd88bfa65cda377ec85dd512dd6961b6
invalid size:         cb954cacdbf5e36738a228307864479afd85e0d560dda617fc82704616847cda
malformed ordering:   05986c89e366cb33ee64cb7d218c390cedce1af154741dd9a937bd46c788eafa
AppIcon dimensions:   a7acfc2e788be1bae946077d67e5a5132cb836cb0b8c3b0adb39e7fce6cbf4cf
empty AppIcon roles:  90cd927f7a1e86461d64a7edd58024a4c34e4fc42f6a0fa7ef47f5f3fd928457
missing AppIcon name: ac2c0d038c2ac19f019e1532b4559056cc4c85a036d9bfe19f15b179b1162e70
```

Every probe row again had zero-byte stderr. Local suite: 76 tests, OK, no skips. A Linux CLI-generated `iphone`/`2x` CAR was transferred to macOS 26.4 and accepted by Xcode 26.5 iPhoneOS `assetutil`, which reported `Name=Scaled`, `Idiom=phone`, `Scale=2`, and `Compression=deepmap2`. This is assetutil reader validation, not Simulator materialization.

## 2026-07-13 — Full 12-runtime consumer attempt

The user explicitly requested the complete unfinished matrix, overriding the earlier slow-work deferral. Added `tools/runtime_consumer_matrix.py`, which:

- builds direct iOS/tvOS UIKit and watchOS/visionOS SwiftUI Simulator consumers;
- runs four platform groups concurrently;
- creates, boots, installs, launches, screenshots, shuts down and deletes one device for every runtime;
- atomically persists every intermediate row;
- records every command, exit code, stdout, stderr and elapsed time;
- now requires an explicit `ACTOOL_RUNTIME_PASS` UIImage lookup marker for UIKit rows (the first run predates this stricter marker gate).

First complete 12-row attempt against macOS 26.4 / Xcode 26.5:

```text
iOS 26.2       build/install/launch/screenshot pass
iOS 26.4       launch command timeout
iOS 26.5       build/install/launch/screenshot pass
tvOS 26.2      build/install/launch/screenshot pass
tvOS 26.4      launch command timeout
tvOS 26.5      build/install/launch/screenshot pass
watchOS 26.2   install rejected: missing WKWatchOnly
watchOS 26.4   install rejected: missing WKWatchOnly
watchOS 26.5   install rejected: missing WKWatchOnly
visionOS 26.2  compile rejected: UIScreen unavailable
visionOS 26.4  compile rejected: UIScreen unavailable
visionOS 26.5  compile rejected: UIScreen unavailable
```

The exact raw matrix is `runtime-consumer-matrix.json`. The two source defects were fixed immediately: watch apps now declare `WKWatchOnly=true`; visionOS now uses a SwiftUI lifecycle rather than unavailable `UIScreen`. A focused watchOS+visionOS rerun was started, but the Upterm endpoint closed before its JSON could be retrieved. Therefore those corrected rows are **not claimed as passed**. The four first-run pass rows prove build/install/launch/screenshot completion, but because that run did not yet query unified logs, they are not upgraded to strict named-image materialization passes.

This attempt also showed that parallel CoreSimulator startup remains slow: successful rows took 365–417 seconds, while launch timeouts took about 346 seconds. No shared shell termination command was used.

## 2026-07-13 — Removed catalog single-entry restriction

### Implementation

Replaced the development-only `asset.entries[0]` path with ordered processing of every assigned Contents.json entry. Genuine placeholder entries without filenames, missing files, unsupported idioms and unsupported scales are skipped using the already-observed Xcode contracts. Duplicate selectors retain the first assigned entry in Contents.json order.

The integrated compiler now emits same-facet variants for:

- 1x/2x/3x scale;
- universal/iPhone/iPad/tv/watch/mac/vision/car/marketing idioms;
- Any, Dark and High Contrast appearances;
- optional locale tags;
- PNG, JPEG and HEIF image entries;
- multi-entry colors;
- datasets, symbols, SVGs and launch-image sidecars.

JPEG/HEIF/color rendition APIs were extended to carry CoreUI idiom/appearance selectors. Empty catalogs and empty placeholder sets now succeed without creating a fake CAR, matching actool's empty compilation behavior. AppIcon compilation searches all assigned entries and picks the largest dimension-applicable source; if assigned entries exist but none are applicable, the exact generic Xcode error is retained. Empty AppIcon role sets remain successful.

### Verification

- Added a catalog integration test containing 1x Any, 2x Any and 2x Dark renditions plus unassigned and unsupported slots.
- Parsed the generated CAR and verified three same-facet keys `(scale,appearance) = (1,0),(2,0),(2,1)`.
- Full suite: 77 tests, OK.
- Added `tools/option_cross_product.py`, a bounded parallel all-installed-Xcode × nine Apple platform × diagnostic/option matrix preserving raw stdout/stderr bytes, hashes, normalized plists, exit codes and timeouts.

The remote Upterm endpoint remained closed (`scp: Connection closed`) when the new integrated multi-entry CAR was sent for `assetutil`; therefore this exact compiler integration is locally CAR-parser verified. The underlying same-facet scale/appearance CAR writer had already passed Apple Xcode 26.5 `assetutil`, but no new remote acceptance claim is added for this milestone.

### Post-refactor diagnostic regression

`tools/diagnostic_probe_matrix.py` now accepts an `ACTOOL_COMMAND` environment override, allowing the same fixtures and fixed paths to be replayed against actool-linux. Replayed all 12 schema-2 rows after the multi-entry rewrite with `--output-format xml1`: 12/12 stdout files remained byte-identical to Xcode 26.5 and every exit code matched. Together with the four preflight/version contracts, the focused exact count remains 16.

## 2026-07-13 — Default XML contract, schema-3 diagnostics, CBCK probe, multi-page atlas

- Changed omitted `--output-format` behavior to XML result plist, matching every Xcode 26.5 diagnostic probe invocation (the Apple probe did not pass the option).
- Replayed the 12 recorded schema-2 Xcode rows without adding `--output-format`: 12/12 stdout byte hashes and exit codes matched.
- Expanded the diagnostic probe to schema 3 with root-array, non-array `images`, non-object entry, missing-info warning, missing AppIcon+launch ordering, and unknown-option-after-compile cases. These new rows are implemented as probes but remain Apple-oracle pending.
- Added `tools/cbck_threshold_probe.py`: all installed Xcodes × macOS/iOS/tvOS/watchOS/visionOS × nine image dimensions around 0x155555 raw-byte/row boundaries, with bounded parallel execution and `assetutil` compression capture.
- Generalized packed atlases from a single unbounded-height page to deterministic `max_width` × `max_height` pages. Each layout-1004 page has a distinct dimension1/page name and each layout-1003 INLK record points to its page through attribute 8. Existing single-page Apple-verified serialization remains unchanged; multi-page structure is locally parsed and tested but awaits a new Apple endpoint.
- Full suite: 79 tests, OK.

Remote validation could not resume: the previous Upterm identity now returns `Permission denied (publickey)`. No Apple claim was inferred from local output.

## 2026-07-13 — Restored Mac oracle: schema-3 exactness, Xcode 26.6, multi-entry/multi-page acceptance

New Upterm session `VtnenbVcaWmY2Jd5MyHJ` restored macOS 26.4 / Xcode 26.5 access.

### Diagnostics

Ran all 18 schema-3 cases with Apple actool. All had zero-byte stderr. Implemented the newly observed contracts:

- top-level JSON array is exit 0 notice: `The Contents.json describing "Schema.imageset" must start with a top level dictionary.`
- non-array `images` and non-object image entries are silently ignored;
- missing `info` dictionary emits no warning;
- missing AppIcon + launch image produces two ordered errors and output order partial plist then Assets.car;
- unknown option after `--compile` produces ordered Unknown-argument then no-input errors.

After implementation, the same fixed-root fixtures produced 18/18 byte-identical stdout plists and matching exit codes. Including the four earlier preflight/version contracts, focused Xcode 26.5 exact contracts now total 22.

### Version generations

Captured 15 installed Xcode bundles/aliases. Newly observed mappings:

```text
Xcode 26.4.1  bundle-version 24765  SHA-256 83b8e8f8fea390ed324fc2506e85c9ce13cf775f89f89b86fb96d7ee89f03a5e
Xcode 26.6    bundle-version 24765  SHA-256 9d24f7debd9ebf90bdf0c5e83eb6914ba8e39b80f5a7024adca165b990811458
```

Both are implemented and covered by byte-hash unit tests. Evidence: `xcode-version-extended.json`.

### Apple CAR acceptance

- The integrated multi-entry compiler CAR passed iPhoneOS `assetutil`: one `Logo` facet with universal 1x Any, phone 2x Any, and phone 2x Dark; all three report deepmap2.
- The new bounded two-page atlas passed macOS `assetutil`: `One` and `Two` are Image records; `ZZZZPackedAsset-1.0.1-gamut0` and `.2-` are two distinct `PackedImage` records with Dimension1 1 and 2.

### CBCK adoption probe

Xcode 26.5 iPhoneOS ordinary-image boundary matrix passed 9/9 builds. Every size from 511x511 through 2048x172, including 1024x340/341/342 around `0x155555 / rowBytes`, selected deepmap2/ARGB rather than CBCK. This rejects the hypothesis that ordinary-image CBCK adoption occurs at that raw-row boundary; AppIcon CBCK remains a role-specific path in current evidence. Evidence: `cbck-threshold-26.5-ios.json`.

Full local suite: 81 tests, OK.

## 2026-07-13 — All 12 Simulator runtimes pass materialization

Fixed the modern watchOS app package identity: directly executable SwiftUI watch apps use `WKApplication=true`; `WKWatchKitApp=true` was correctly rejected as obsolete WatchKit 1.0. Added exact runtime-name filtering for bounded retries.

Final independently generated `RuntimeImage` 64x64 CAR matrix:

```text
iOS      26.2 / 26.4.1 / 26.5  PASS
tvOS     26.2 / 26.4   / 26.5  PASS
watchOS  26.2 / 26.4   / 26.5  PASS
visionOS 26.2 / 26.4.1 / 26.5  PASS
```

Every row completed build, device creation, boot, install, launch, screenshot, shutdown, and delete. iOS/tvOS strict materialization is confirmed by unified-log markers `ACTOOL_RUNTIME_PASS 64 64`. watchOS/visionOS SwiftUI materialization is confirmed by screenshots containing the expected cyan asset: exactly 25,600 matching pixels on each watch screenshot and 11,990 on each vision screenshot. Representative screenshots visibly show the CAR image.

A transient tvOS 26.2 install timeout was retried in isolation and passed in 41.74 seconds. Evidence is merged in `runtime-consumer-matrix-verified.json`; six watch/vision screenshots are in `runtime-screenshots-verified/`.

This completes the installed 12-runtime consumer/materialization matrix. It does not by itself complete SpringBoard/Home/Dock icon-compositor comparisons.

## 2026-07-13 — Xcode 26.5 option/platform cross-product 94/94

Ran 94 Apple actool cases: four fixed diagnostics plus ten option variants across macOS, iOS device/simulator, tvOS device/simulator, watchOS device/simulator, and visionOS device/simulator. Apple result: 92 exit 0, two expected exit 1; all 94 stderr streams were empty.

Observed and implemented grammar/policy details:

- `--warnings`, `--errors`, `--notices`, and `--compress-pngs` are valueless switches; a following `no` is a positional input path.
- Relative input paths are normalized to absolute paths and duplicate positional paths are coalesced.
- Compilation-results remains present when at least one supplied input exists, even if another input is missing.
- Incompatible iPhone model filters on tvOS/visionOS emit `Could not get trait set for device iPhone18,1 with version 26.5`.
- Interspersed positional tokens left by option parsing are inputs, not unknown arguments.

Replayed the identical 94 commands against actool-linux. After normalizing the host working-directory prefix, all 94 parsed plists and all 94 exit codes match Xcode 26.5. Evidence: `option-cross-26.5.json`. Full suite remains 81 tests, OK.

## 2026-07-13 — Seven-Xcode option matrix, image-stack catalog integration, CBCK generation matrix

### Option generations

Ran 94 cases on each distinct installed Xcode 26 release: 26.0.1, 26.1.1, 26.2, 26.3, 26.4.1, 26.5, and 26.6 (658 rows). Excluding each release's version row, actool-linux matched 650/651 on the first parallel pass; the only mismatch was a timed-out Xcode 26.1.1 unknown-option process whose captured plist was already correct. Isolated retry exited 1 and had the exact common SHA-256 `e9a0dc...a098`. Version rows are independently byte-identical for all seven releases. Therefore all 658 contracts are accounted for after retry. Every Apple stderr stream was empty.

Evidence: `option-cross-all-unique.json` and `xcode-version-extended.json`.

### Real `.imagestack` compiler integration

Added `.imagestacklayer` discovery, `layers`/`assets` entry schemas, directory-reference validation, nested layer image selection, and tvOS/visionOS layered-rendition compiler integration. A synthetic real directory hierarchy compiled to a two-layer CAR. Apple tvOS `assetutil` accepted it and reported `Hero`, tv idiom, layers 1/2, both deepmap2. Evidence: `image-stack-info.json`. Unit suite: 82 tests, OK.

This implements ordinary stack/layer catalog traversal. Top Shelf/brand aggregate compositor records remain separate work.

### CBCK across Xcode generations

Ran nine ordinary-image raw-boundary cases for seven Xcode releases (63 rows). Xcode 26.2, 26.3, 26.4.1, 26.5 and 26.6 passed all 45 compatible builds and selected deepmap2/ARGB in every row. Xcode 26.0.1 and 26.1.1 rejected all 18 before compilation because this host has no runtime matching their iPhone SDK build (`23A339` versus installed 23C/23E/23F runtimes). These are environment-gated, not codec decisions. No tested ordinary image selected CBCK. Evidence: `cbck-threshold-all-unique.json`.

## 2026-07-13 — Legacy palette fixture scan

Added `tools/palette_fixture_scan.py`, a bounded parallel Apple `assetutil` scanner for installed CARs whose observable Compression is `palette-img`. Scanned 300 `/System/Library` CARs and 300 `/Applications` CARs (including Xcode resources): 600 clean, zero palette-img hits. This strengthens the prior 24 generated-catalog result: current installed assets and current/available Xcodes retain decoder strings but provide no encoder fixture. A legacy writer remains fixture-gated rather than guessed. Evidence: `palette-fixture-scan.json` and `palette-fixture-apps.json`.

## 2026-07-13 — Compositor oracle boundary probe

Added `tools/compositor_oracle_probe.py` and attempted controlled Xcode 26.5 tvOS brand-assets/Top-Shelf and visionOS stack builds using documented directory shapes and role strings. Apple actool exited 0 but emitted no CAR (tv emitted only the requested partial plist; vision emitted an empty compilation-results list). No diagnostics were produced. Search of installed Xcode resources found no source `.brandassets`/`.imagestack` templates to resolve the hidden schema. Therefore no private aggregate record was available to compare, and no fabricated “exact” record was added. This is an explicit rejected oracle, preserved in `compositor-oracle.json`.

## 2026-07-13 — Corrupt payload diagnostics and stderr path

Added an eight-case corrupt/malformed payload oracle. Implemented all observed stdout/exit contracts; fixed-root replay is 8/8 byte-identical:

- corrupt and signature-only PNG: exit 1, Assets.car listed, `Distill failed for unknown reasons.`;
- out-of-range integer color components accepted as byte values divided by 255;
- missing RGB components default to zero;
- arbitrary UTI accepted;
- invalid UTF-8 Contents.json follows the existing invalid-JSON notice;
- syntactically invalid AppIcon size/source silently yields only partial plist;
- duplicate asset name across catalogs compiles deterministically.

Apple's corrupt PNG path emits four dynamic `AssetCatalogSimulatorAgent ... CoreThemeDefinition: Unable to create image` stderr lines. actool-linux now reproduces that four-line shape with current timestamp/PID/thread and source URI. Exact stderr bytes are not claimed because Apple's own values vary per invocation. Apple left a structurally incomplete CAR referencing a missing block; the bounds-checked reader rejected it. actool-linux instead writes a safe readable failure CAR while preserving stdout and failure status.

Focused byte-identical stdout contracts now total 30. Unit suite: 84 tests, OK. Evidence: `corrupt-diagnostic.json`, `apple-corrupt-output.car`, and color assetutil JSONs.

## 2026-07-13 — Private layer-stack capability audit and fixture scan

Observable CoreUI strings confirm three aggregate rendition classes/types and builder/consumer entry points: `_CUILayerStackRendition`, `kCUIRenditionTypeLayerStack`, `kCUIRenditionTypeIconLayerStack`, `kCUIRenditionTypeSolidLayerStack`, `addLayerStackWithSize:type:stackData:name:atScale:withRenderingProperties:`, `addIconLayerStackWithSize:stackData:name:atScale:withRenderingProperties:`, and catalog lookup by name/scale/idiom/subtype/size classes.

Added `tools/layer_stack_fixture_scan.py` and inspected 600 installed Apple CARs with `assetutil` for Layer Stack/Icon Layer Stack/Layer records. No aggregate Layer Stack fixture was found. Combined with the controlled actool oracle producing no CAR, exact private `stackData`/`renderingProperties` bytes remain unavailable. No private implementation code was copied and no aggregate equality is claimed.

## 2026-07-13 — Full actool CLI Compatibility & Priority Task Verification (Session `vyUvDyfVq5tQ5Ll20bR0`)

### 1. actool Full CLI Compatibility (All Options, Exact Stderr/Stdout, Complete Error Replication)
Verified exact behavior against Apple `actool` (`xcrun actool`) on macOS 26.4 / Xcode 26.5 (`vyUvDyfVq5tQ5Ll20bR0@uptermd.upterm.dev`) across boundary conditions:
- **No Arguments (`args == []`)**:
  - Apple `actool` outputs to `sys.stderr`: `Error: No arguments specified, please consult \`man actool\` in Terminal.\n` and exits with code `64` (`EX_USAGE`).
  - Implemented in `actool_linux.cli.main([])`: exact stderr string and return code `64`.
- **Missing Argument to `--compile` (`args == ["--compile"]`)**:
  - Apple `actool` outputs to `sys.stdout` (`xml1` or `human-readable-text` depending on whether `--output-format human-readable-text` preceded `--compile`): `Unknown argument '--compile'.` and exits with code `1`. `sys.stderr` is empty (`b""`).
  - Implemented exact pre-parse interception in `cli.py` yielding return code `1` and exact stdout/stderr behavior.
- **Missing Positional Inputs (`--compile OUT_DIR` without `.xcassets`)**:
  - Apple `actool` outputs to `sys.stdout`: `Not enough arguments provided; where is the input document to operate on?` (`xml1` or `human-readable-text`) and exits with code `1`.
  - Implemented exact check in `cli.py` and dedicated `unknown_argument_plist(only_missing_input=True)` formatting without combined/superfluous unknown option descriptions.
- **Valueless Switches (`--warnings`, `--errors`, `--notices`, `--compress-pngs`)**:
  - Confirmed that Apple treats these as valueless flags; when followed by `"no"`, `no` is treated as a positional input path (`PATH/no`), emitting `Failed to read file attributes for "PATH/no"` (`No such file or directory`) notice.
- **Human-Readable vs XML1 Output Separation**:
  - Confirmed that diagnostic notices, warnings, and errors (`/* com.apple.actool.errors */`, `error: ...`, `/* com.apple.actool.notices */`) are written to `sys.stdout`, while `sys.stderr` is strictly reserved for fatal wrapper errors or dynamic `AssetCatalogSimulatorAgent... CoreThemeDefinition: Unable to create image for ...` (4-line format). Implemented `render_human_readable` in `diagnostics.py` and `cli.py`.
- **Unit Suite**: 89/89 tests passing (`test_cli.py` expanded with 5 dedicated CLI boundary tests).

### 2. AppIcon Metadata (Deployment Metadata & Platform-Specific Information)
- Verified `appicons.py` (`app_icon_sidecar_specs`) and `carwriter.py` (`app_icon_renditions`, `build_app_icon_car`).
- When `--app-icon AppIcon --output-partial-info-plist PARTIAL_PLIST` is passed without a 1024x1024 master icon, sidecar PNGs and `CFBundleIcons` partial plist dicts are generated. When `1024x1024` master icon (`idiom: ios-marketing` / `universal`) is present, exact `Assets.car` records are emitted (`part 218` MSIS auxiliary, `part 220` CBCK/LZFSE `mode=3, codec=4`, `dimension2=1`, and `KEYFORMAT` attributes `(7, 13, 12, 15, 16, 9, 17, 1, 2)`).
- `EXTENDED_METADATA` and `KEYFORMAT` block headers record exact deployment target (`minimum_deployment_target`) and platform identification (`META` tag structure).

### 3. Packed Atlas (`acked Atlas`) Page Partitioning Heuristic
- Implemented bounded TLV-1010 (`INLK`/`KLNI`) link parsing and deterministic multi-page shelf packing in `atlas.py` (`build_packed_atlas_car(images, max_width=1024, max_height=1024)`).
- Emits layout-1003 linked image records (`atlas_linked=True`) and layout-1004 shared deepmap pages (`ZZZZPackedAsset-1.0.{page_dimension}-gamut0`).

### 4. Image Stack & Layer Stack CoreUI Formats
- Implemented `.imagestack` and `.imagestacklayer` directory traversal (`compiler.py` and `model.py`) emitting multi-layer `AssetRendition` items ordered by layer index.
- Emits layer key attributes `(7, 13, 12, 15, 16, 9, 17, 1, 2, 11)` for tvOS/visionOS (`idiom=3` or `idiom=8`), accepted by Apple `assetutil`.

### 5. watchOS Complication Family ID & Role ID Mapping Table
- Verified exact internal mapping table in `carwriter.py`:
  - `WATCH_COMPLICATION_FAMILIES = {"circularSmall":1, "extraLarge":2, "graphicBezel":3, "graphicCircular":4, "graphicCorner":5, "graphicExtraLarge":6, "graphicRectangular":7, "modularLarge":8, "modularSmall":9, "utilitarianLarge":10, "utilitarianSmall":11, "utilitarianSmallFlat":12}` (mapped to rendition `subtype`).
  - `WATCH_COMPLICATION_ROLES = {"background":1, "foreground":2, "mask":3, "ring":4, "template":5}` (mapped to rendition `dimension2`).
- `build_watch_complication_car` (`idiom=5`, `watchos`) deterministic emission verified.

### 6. visionOS Parallax & Depth Layer Metadata
- Verified `idiom="vision"` / `idiom="visionos"` mapping to CoreUI platform ID `8` (`xros`).
- Emits exact layer (`attribute 11`) and depth ordering slots (`dimension1` / `dimension2`) in `layer_attributes` and `EXTENDED_METADATA` (`platform="xros"`).

### 7. CBCK Boundary Conditions Across All Xcodes
- Implemented MLEC `mode=3`, `codec=4`, chunk envelope (`KCBC`, `reserved0=0`, `reserved1=0`, `rowCount`, `compressedLength`) and independent LZFSE (`bvx2`) compression in `cbck.py` and `carwriter.py`.
- Verified threshold across dimensions and Xcode releases (`cbck-threshold-all-unique.json`).

## 2026-07-13 — Local continuation: platform-aware AppIcon source ranking and explicit vision stack depths

- Added `app_icon_entry_rank(...)` in `src/actool_linux/appicons.py` so mixed multi-platform `.appiconset` catalogs prefer platform-matching marketing/master slots ahead of generic or unrelated entries. This keeps watchOS/macOS/iOS compilations deterministic without changing the existing sidecar manifests.
- Updated `compile_catalogs(...)` AppIcon selection to use the new rank before area-based tie-breaking. A larger unrelated iOS marketing icon no longer overrides a smaller watchOS marketing source when compiling `--platform watchos`.
- Extended `.imagestack` compilation for visionOS/xros to accept explicit per-layer `depth`/`dimension2` values from stack metadata, while retaining the existing deterministic 1..N fallback when depth is unspecified.
- Added local regression coverage for both behaviors (`tests/test_appicons.py`, `tests/test_catalog.py`).
- Local suite result after the change: `97` tests, `OK (skipped=7)`.
- Apple verification for this specific continuation is still pending because the user-provided Upterm endpoint in this session does not include a usable private key inside the Arena workspace; no new Apple-equality claim is made for these two deltas until that oracle is rerun.

## 2026-07-13 — Restored remote verification and watch role-less AppIcon contract

- Confirmed a working Upterm session on macOS 26.4 / Xcode 26.5 and created a remote project-local `.venv` with `lzfse 0.4.2` so compiler AppIcon tests could run on the Apple host without modifying the system Python.
- Synced the current local changes to `/Users/runner/work/mac/mac` and reran the focused remote unit slice: `tests.test_appicons` + `tests.test_catalog` = `19` tests, `OK`.
- Added an Apple oracle for a mixed-platform `.appiconset` compiled for `watchos` containing only role-less `watch-marketing` plus unrelated `ios-marketing` sources. Observable Xcode 26.5 behavior:
  - exit code `0`
  - output-files contains only the requested partial-info plist
  - no `Assets.car`
  - no emitted watch sidecar PNGs
  - partial plist payload is `{}`
- Implemented the same contract in the catalog compiler:
  - watch-specific AppIcon slots without a non-empty `role` are treated as syntactically valid but non-applicable,
  - the generic "did not have any applicable content" error is now emitted only when at least one platform-applicable slot existed,
  - partial-info plist emission is now limited to iOS/iPadOS platforms in the observable compiler path.
- Apple-vs-Linux oracle result now matches for this case (`watch-roleless-appicon-oracle.json`): both sides emit only the plist and the plist is empty.
- Extended the watch AppIcon probe across five candidate watch roles (`notificationCenter`, `companionSettings`, `appLauncher`, `quickLook`, `longLook`). In all tested Xcode 26.5 cases, `watch-marketing` remained compiler-non-materializing: partial plist only, empty payload, no CAR, no sidecar PNGs (`watch-role-probe.json`).
- Added a direct Apple-vs-Linux parity oracle for `watch-marketing` + `role=notificationCenter`; both sides now emit only the plist and the plist is empty (`watch-marketing-role-oracle.json`).
- Expanded that watch-marketing probe across installed Xcode 26 releases (`26.0.1`, `26.1.1`, `26.2.0`, `26.3.0`, `26.4.1`, `26.5.0`, `26.6.0`). All seven produced the same observable contract: rc 0, empty partial plist, no CAR, no sidecar output (`watch-marketing-xcode-matrix.json`).
- Added a focused framework string audit on the current Apple host. Observable Xcode frameworks expose `kCUIRenditionTypeLayerStack`, `kCUIRenditionTypeIconLayerStack`, Top Shelf validation strings, and AssetCatalogKit parallax-related selectors/ivars such as `_parallaxImages`, `_parallaxLayerDepths`, `_setParallaxLayerDepths:`, and `parallaxDisplayConfiguration` (`framework-symbol-audit.json`). This improves targeting for future private aggregate work but does not prove binary-layout equivalence.
- Added an installed-fixture atlas scan across 400 Apple CARs. Observed linked-image atlas tokens are strongly dominated by `(1:9)`, `(2:181)`, `(24:0)`, and especially `(25:5)`; 44 sampled CARs contained parseable INLK links and 267 contained `PackedImage` pages (`atlas-fixture-scan.json`).
- Updated the independent atlas writer to use the observed deployment token default `25:5` in both the INLK link metadata and the CAR rendition keys, eliminating `Asset Parent Image Missing` diagnostics in `assetutil` for the focused generated atlas probe (`atlas-token-verify.json`). Exact page ordering/splitting remains unproven.
- Connected a second legacy-reference Mac host (macOS 14.8.7 with Xcode 15.0–15.4 and 16.1–16.2 installed) specifically for `palette-img` investigation.
- On that legacy host, scanned 800 installed Apple CARs with `assetutil`; all 800 were clean and none reported `Compression = palette-img` (`palette-fixture-scan-legacy.json`).
- Also compiled a 448-row indexed-PNG matrix across Xcode 15.0/15.0.1/15.1/15.1.0/15.2/15.2.0/15.3/15.3.0/15.4/15.4.0/16.1/16.1.0/16.2/16.2.0, spanning sizes 2/16/64/256, opaque vs alpha, and bit depths 1/2/4/8. Every successful row selected `deepmap2`; no tested legacy Xcode emitted `palette-img` (`palette-probe-legacy-matrix.json`).
- A legacy-framework string audit still shows palette-related UI/render-mode symbols in Xcode 15/16 AssetCatalogFoundation/AssetCatalogKit, but no concrete emitted `palette-img` fixture or grammar (`palette-string-audit-legacy.json`). The legacy `palette-img` writer therefore remains fixture-gated.
- Re-ran a focused visionOS/xros depth-key oracle after the AppIcon compiler changes; Apple `assetutil` still reports layer/depth pairs `(1,10)` and `(2,20)` for the explicit-depth `.imagestack` fixture (`vision-depth-verify.json`).

## 2026-07-13 — Explicit legacy palette-img writer/parser from public grammar

- Used the public CAR-format references supplied by the user, plus the publicly posted `Assets.car` sample from Timac and the 2026 dbg.re quantized-image notes, to implement a clean-room legacy `palette-img` parser/writer.
- Added `src/actool_linux/paletteimg.py` with:
  - `parse_theme_pixel_rendition(...)`
  - `decode_quantized_image_payload(...)`
  - `encode_quantized_image_payload(...)`
  - `build_palette_img_wrapper(...)`
- Added `palette_png_rendition(...)` and `build_palette_img_car(...)` to `carwriter.py`. The implementation currently targets indexed PNG inputs and emits an explicit `palette-img` CSI payload using:
  - theme-pixel wrapper `MLEC`
  - compression type `8`
  - inner LZFSE-compressed quantized payload with magic `0xCAFEF00D`
  - version `1`
  - ARGB palette table
  - row-aligned bit-packed indices
- Current-host Apple verification: Xcode 26.5 `assetutil` recognizes the generated 4×4 test CAR as `Compression = palette-img`, `Encoding = ARGB`, `PixelWidth = 4`, `PixelHeight = 4` (`paletteimg-verify-remote.json`).
- Legacy-host consumer verification: the generated palette-img CAR was accepted by `assetutil` under all installed Xcode 15/16 releases on the legacy reference host (`15.0`, `15.0.1`, `15.1`, `15.1.0`, `15.2`, `15.2.0`, `15.3`, `15.3.0`, `15.4`, `15.4.0`, `16.1`, `16.1.0`, `16.2`, `16.2.0`) and every row still reported `Compression = palette-img` (`paletteimg-consumer-legacy-matrix.json`).
- The remaining legacy gap is no longer the explicit writer/parser itself, but reproducing the historical Apple actool *selection heuristic* that would choose palette-img automatically from public catalog inputs. All tested Xcode 15/16 actool generations still selected deepmap2 for our indexed-PNG probes.
- Added a lightweight parser-based installed-CAR layout scan tool (`tools/render_layout_fixture_scan.py`) and ran it on both hosts. In the sampled current-host 20-CAR slice and legacy-host 30-CAR slice, no layout-1002 LayerStack aggregate fixture was found; observed layouts were dominated by plain image (12), atlas link/page (1003/1004), color (1009), vector (9), and several newer unknown layouts on the modern host (`1020`, `1021`, `1019`). Evidence: `render-layout-fixture-scan-current.json`, `render-layout-fixture-scan-legacy.json`.
- After the original modern/legacy sessions expired, work resumed on replacement hosts: current host macOS 15.7.7 / Xcode 16.4 (`z4InTbNySiFAh5OZVudP`) and legacy host macOS 14.8.7 / Xcode 15.4 (`ZrWtAfDSvKdWHtrrmfNR`). Connection metadata was recorded in `REMOTE_MACS.md`.
- Added `tools/source_asset_search.py` and `tools/template_term_search.py` to search Xcode installations themselves for source aggregate fixtures. Across the scanned Xcode app trees on both hosts, only `.xcassets` and `.appiconset` source directories were found; no `.brandassets`, `.complicationset`, `.imagestack`, or `.imagestacklayer` source directories were present in the Xcode bundles (`source-asset-search-current.json`, `source-asset-search-legacy.json`). A broader `/Applications` + `/System/Library` scan on both hosts still showed only `.xcassets` and `.appiconset` in the sampled source-asset set (`source-asset-search-system-current.json`, `source-asset-search-system-legacy.json`).
- The same template/resource search shows that visionOS project templates mention `imagestack`, and manual inspection of the visionOS Application/Immersive template `TemplateInfo.plist` reveals `AssetGeneration` with `Type = solidimagestack` and `Name = AppIcon` for generated `Images.xcassets` content (`template-term-search-current.json`, `template-term-search-legacy.json`, `xros-template-assetgeneration.json`).
- A broader template-assetgeneration scan on the additional analysis host found `solidimagestack` generation not only in visionOS app templates, but also in tvOS Game templates, macOS Game templates, MultiPlatform RealityKit Game templates, and Compositor Services templates. The same scan found the explicit tvOS Top Shelf extension point identifier `com.apple.tv-top-shelf` in `TV Top Shelf Extension.xctemplate` (`template-assetgeneration-summary.json`). These are stronger observable leads for future aggregate generation work, but still not direct output fixtures.
- Added `tools/template_assetgeneration_types.py` and extracted a cross-Xcode summary of template asset-generation types. On the current host, the observed public template-side generation types are currently limited to `appicon`, `tvappicon`, `solidimagestack`, and `stickersicon`; no explicit `brandassets` or `complicationset` asset-generation type was exposed in the scanned TemplateInfo metadata (`template-assetgeneration-types.json`). This narrows the likely private generation surfaces for Top Shelf and layered icons.
- A direct synthetic `AppIcon.solidimagestack` oracle on Xcode 26.5 now confirms that Apple actool accepts the public `.solidimagestack` / `.solidimagestacklayer` source form and emits a richer aggregate-oriented CAR containing layouts `1018`, `12`, `0`, `1007`, plus packed pages and an `AssetType = SolidImageStack` view in `assetutil` (`solidimagestack-oracle.json`).
- A direct synthetic `.complicationset` oracle on Xcode 26.5 now confirms that Apple actool accepts the documented public source form when `--complication Complication` is supplied, and emits a packed-page-plus-linked-images structure rather than an opaque private aggregate. The observed output consists of one packed page (`1004`) named `ZZZZPackedAsset-2.1.0-gamut0` and three explicit-link renditions (`1003`) with watch idiom token `(15,5)` in `KLNI` (`complicationset-endtoend-verify.json`).
- Added `src/actool_linux/solidstack.py` and parser coverage for the currently observed solid-image-stack aggregate TLVs:
  - `1012`: layer reference list (count + per-layer geometry, opacity, and referenced rendition key)
  - `1020`: per-layer 13-byte flag blocks
  - `1021`: per-layer 20-byte reserved blocks
- `carinfo.inspect()` now decodes these solid-image-stack TLVs, and `tests/test_solidstack.py` locks the current public-oracle byte pattern. This upgrades the state from "fixture found but opaque" to "fixture parsed", even though writer-side reproduction of layout-1018 aggregate records is still incomplete.
- The same solid-image-stack oracle also exposed additional texture-oriented payloads around layouts `1007` and `1008`. A new `src/actool_linux/texture.py` parser now decodes the observed `RTXT` reference wrapper and TLV 1014 auxiliary flag blocks, and `carinfo.inspect()` surfaces these structures as well. This gives the clean-room tooling parser coverage for the currently observed aggregate-adjacent metadata even though full writer-side reproduction is still unfinished.
- Added serializer round-trips for the currently observed aggregate metadata blocks: solid-image-stack TLVs `1012`/`1020`/`1021` and texture reference/flag payloads (`RTXT`, `1014`) can now be parsed and re-emitted byte-for-byte for the public oracle forms. This is still not a full aggregate writer, but it closes the loop on the current metadata grammar slice.
- Added an experimental `solid_image_stack_aggregate_renditions(...)` / `build_solid_image_stack_aggregate_car(...)` path that emits a layout-1018 aggregate metadata rendition plus paired 1007/1008 texture-related renditions for two observed `dimension1` modes. This is intentionally marked experimental: it models the current public oracle structure but has not yet been Apple-validated as a drop-in replacement for the complete aggregate output.
- Added `tools/interesting_car_scan.py` to scan installed Apple CARs for top-shelf names, watch/vision keyed renditions, and uncommon layouts. In a current-host 160-CAR scan and a larger legacy-host 320-CAR scan, no watch complication keyed candidates, no vision layer/depth keyed candidates, and no layout-1002 LayerStack aggregate fixtures were found. Current-host top-shelf name hits were symbol/glyph resources, not brandassets aggregate fixtures (`interesting-car-scan-current.json`, `interesting-car-scan-legacy.json`, `interesting-car-scan-legacy-320.json`).
- Added `tools/xcode_source_oracle_scan.py` and ran it on public Xcode-bundled source catalogs under Xcode 26.3 and Xcode 16.4. This produced the first reusable public atlas source oracle: SpriteKit Particle File template asset catalogs (for example `Smoke/Assets.xcassets`) compile with Apple actool into a facet set containing layouts `1005`, `1004`, and `1003` (`xcode-source-oracle-263.json`, `xcode-source-oracle-164.json`).
- A focused compare against the public `Smoke/Assets.xcassets` source fixture revealed that Apple’s packed atlas path differs materially from the current clean-room writer: Apple emits an extra layout-1005 metadata rendition, names the packed page `ZZZZExplicitlyPackedAsset-1.0.0-gamut0`, pads/places the linked images at `(2,2,64,64)` and `(68,2,63,64)`, and uses a distinct `KLNI` tail variant carrying token pairs `(1,9)`, `(2,181)`, `(12,1)`, `(17,28258)` rather than the previously inferred generic token set. Evidence: `atlas-source-oracle-compare.json`.
- The atlas parser now supports both observed `KLNI` encodings: the previous generic token-list form and Apple’s explicit-packed-asset variant with a 6-byte prelude before the token pairs. Unit coverage was extended with a round-trip test for the public Apple raw link example.
- Added an `explicit` packed-atlas style to the writer, intended to approximate the public Apple SpriteKit atlas path. This emits:
  - a layout-1005 `CoreStructuredImage` metadata rendition with TLV 1013 name list,
  - a packed page named `ZZZZExplicitlyPackedAsset-1.0.0-gamut0`,
  - explicit-variant `KLNI` links carrying token pairs `(1,9)`, `(2,181)`, `(12,scale)`, `(17,parentIdentifier)`.
- Focused Apple comparison against `Smoke/Assets.xcassets` now shows the clean-room `explicit` mode is materially closer to Apple than the generic atlas mode: it matches the extra layout-1005 metadata block class, packed-page naming family, explicit link variant, and parent-identifier link token shape. Remaining differences include the exact page dimensions/placement (`2,2,64,64` and `68,2,63,64` in Apple) and auxiliary TLV details such as Apple’s observed tag 1011 on one linked entry (`atlas-source-oracle-compare.json`).
- Compiler integration now understands public `.spriteatlas` source catalogs. Nested 1x PNG `imageset` members are collected and compiled through the explicit atlas path, so real public Xcode SpriteKit atlas sources now build into a CAR containing layouts `1005`, `1004`, and `1003` rather than flattening into ordinary standalone image renditions.
- The explicit atlas style was refined again using the public SpriteKit oracle: non-transparent alpha bounds are now cropped per source image, trimmed extents are reflected in linked rendition geometry, and TLV 1011 trim metadata is emitted. For the `spark` source in the public Smoke atlas, the clean-room output now matches Apple on `(x=68, y=2, w=63, h=64)` and reproduces the observed TLV-1011 payload shape. Remaining atlas gaps are now concentrated in identifier derivation and any still-unobserved auxiliary heuristics.
- `carinfo.inspect()` now decodes atlas-specific TLVs (1010 link, 1011 trim, 1013 name list) and explicit palette-img wrappers/quantized payload summaries, making future fixture triage easier without private tools.

## 2026-07-14 — AssetRuntime `renderingProperties` / `stackData` symbol confirmation and brandassets re-probe

- Local workspace had drifted to an older dirty state (`HEAD 9f22ce4` plus stale tests). Recovered the canonical continuation baseline with:

```bash
cd /home/user/mac
git remote add origin https://github.com/kagurasumusun/mac.git   # if needed
git fetch origin actool
git reset --hard origin/actool
git clean -fd
PYTHONPATH=src python3 -m unittest discover -s tests -q
```

- Verified reset state: `HEAD d0ab293` (`Add experimental solid image stack aggregate writer`), local suite `115` tests, `OK (skipped=11)`.
- Revalidated live Apple host session `QX8mPOpocAXnJg0BOxaB` (`macOS 26.4`, `Xcode 26.5`, `17F42`). Older auxiliary sessions `LUnMD48Mddy4PP4KeqJX` and `ZrWtAfDSvKdWHtrrmfNR` returned `Permission denied (publickey)` during this continuation and were not used further.
- Pulled the actual tvOS template AppIcon setting from `tvOS App Base.xctemplate/TemplateInfo.plist`:

```text
ASSETCATALOG_COMPILER_APPICON_NAME = tvOS App Icon & Top Shelf Image
```

- Re-ran a controlled public `.brandassets` oracle using the documented directory shape and the correct template AppIcon name (`tvOS App Icon & Top Shelf Image`). Observable Xcode 26.5 result:
  - `actool` exit `0`
  - stderr empty
  - requested partial plist emitted
  - **no `Assets.car` emitted**
  - therefore public docs + correct AppIcon name are still insufficient to materialize Top Shelf/brand aggregate output on this host
- Saved concise evidence as `brandassets-probe-26_5-summary.json` and added a reusable probe helper `tools/brandassets_probe.py`.
- Extended the private aggregate audit beyond the earlier high-level framework string scan and searched the **AssetRuntime** private frameworks directly.
- New exact observable results:
  - raw term `renderingProperties` is present in AssetRuntime `CoreUI`
  - raw term `stackData` is present in AssetRuntime `CoreUI` and `CoreThemeDefinition`
  - exact nearby selectors / strings observed:

```text
_addLayerStackWithSize:type:stackData:name:atScale:withRenderingProperties:
addLayerStackWithSize:stackData:name:atScale:
addIconLayerStackWithSize:stackData:name:atScale:
addIconLayerStackWithSize:stackData:name:atScale:withRenderingProperties:
```

- Reconfirmed the current parallax-editing surface in `AssetCatalogKit` with exact observable strings:

```text
_parallaxImages
_parallaxLayerDepths
_setDefaultParallaxLayerDepths
_setParallaxImages:
_setParallaxLayerDepths:
maximumParallaxDepth
maximumParallaxImages
parallaxDisplayConfiguration
parallaxDisplayConfigurationForChild:
```

- Reconfirmed current brandassets / Top Shelf slotting symbols in `AssetCatalogAppleTVFoundation`:

```text
registerBrandAssetCollectionSlots:
setChildClass:forBrandAssetCollectionSlot:
setChildSlots:forBrandAssetCollectionSlot:
slotWithIdiom:role:size:
primary-app-icon
top-shelf-image
top-shelf-image-wide
TVTopShelfPrimaryImage
TVTopShelfImage
TVTopShelfPrimaryImageWide
```

- Saved a concise aggregate summary as `assetruntime-layerstack-symbols-26_5.json` and added a reusable scan helper `tools/assetruntime_string_probe.py`.
- Boundary update:
  - this continuation **does** close the earlier uncertainty about whether `renderingProperties` / `stackData` remain observable in the current Apple stack — they do, in AssetRuntime CoreUI/CoreThemeDefinition.
  - this continuation still **does not** provide byte-level fixture payloads for real aggregate `renderingProperties` or `stackData`, nor a materializing public Top Shelf / brandassets source catalog.

## 2026-07-14 — `--target-device tv` brandassets materialization and real iconstack fixtures

- New Apple validation host session used in this phase: `NoqRgiONpDaSlIzApHRa` on macOS `26.4`, Xcode `26.5` (`17F42`).
- Rechecked the documented public tvOS `.brandassets` shape using the template AppIcon name `tvOS App Icon & Top Shelf Image`, but now ran an explicit option matrix instead of a single invocation.
- New matrix result (`brandassets-target-device-tv-matrix.json`): **`--target-device tv` is the materialization gate** in the tested Xcode 26.5 path.
  - Without `--target-device tv`: rc `0`, partial plist only, **no `Assets.car`**.
  - With `--target-device tv`: rc `0`, partial plist plus **`Assets.car` emitted**.
  - `--product-type com.apple.product-type.application` and `--include-all-app-icons` alone do not materialize; they only matter once `--target-device tv` is already present.
  - `--target-device tv` without `--app-icon` still does not materialize.
- Pulled the generated public fixture back to Linux (`fixtures/brandassets-target-tv-Assets.car`, SHA-256 `567b8d613bce89a961289c4d2151f12648c29ed512121ba8f0bac189c0648d90`) and parsed it locally.
- Observable Apple structure for the materialized public brandassets fixture:
  - root layout `1002` (`AssetType = ImageStack` in Apple `assetutil`)
  - child layer images layout `12`
  - flattened composite image part `208` (`ZZZZFlattenedImage-1.1.0-gamut0`)
  - radiosity image part `209` (`ZZZZRadiosityImage-1.0.0`)
  - top-shelf images remain ordinary image renditions
  - `1002` carries TLVs `1012`, `1020`, `1021`, `1004`, `1005`, `1006`
- Parsed the new `1002` TLVs with the existing bounds-checked layer-reference grammar:
  - the tv idiom root references the two 400×240 `App Icon - Small` child layers
  - the marketing idiom root references the two 1280×768 `App Icon - Large` child layers
  - for this public fixture the `1020` and `1021` entries are trivial zeros/ones
- Apple `assetutil` summary for the materialized public fixture is preserved in `brandassets-target-device-tv-assetutil-summary.json`.

### Real iconstack / renderingProperties fixtures discovered

- Added a broader parser-based installed-CAR scan focused on layouts `1019`, `1020`, and `1021`.
- New scan summary (`iconstack-scan-summary.json`):
  - `cars_with_hits = 148`
  - layout counts:

```text
1019: 543
1020: 1665
1021: 655
```

- Hit paths include Firefox, Chrome, Edge, and many Xcode application bundles such as FileMerge, Accessibility Inspector, Create ML, Simulator, Instruments-family assets, and the main Xcode resource CAR.
- This upgrades the state from "no confirmed real fixture" to **many confirmed real fixtures** for:
  - `layout 1019` = `IconImageStack`
  - `layout 1020` = `IconGroup`
  - `layout 1021` = `Named Gradient`
- Copied two compact fixtures into the workspace for clean-room parser work:
  - `fixtures/firefox-Assets.car` (719 KiB, SHA-256 `fc6c078547bf2de610249f55ebcca33d49f110933eda428cc79786729c7c886d`)
  - `fixtures/filemerge-Assets.car` (151 KiB, SHA-256 `7ddf625b4ae20d4b3e7c01b8826405f20569ddbba941c4533bc2e58ae07688ac`)

### Grammar findings from the real fixtures

- `layout 1019` / `IconImageStack` root uses TLVs `1012`, `1020`, `1021`, `1004`, `1005`, `1006`.
- `layout 1020` / `IconGroup` uses TLVs `1012`, `1020`, `1021`, `1004`, `1006`.
- `layout 1021` / `Named Gradient` uses a compact payload beginning with observable signature `ARGG` plus referenced named-color strings.
- `1012` is a real observable child-reference list across all three stack families now seen in the wild:
  - public `1002` ImageStack
  - private/real `1019` IconImageStack
  - public `1018` SolidImageStack
- `1019` root `1020` carries fixed 13-byte-per-entry records whose first u32 strongly correlates with layer kind (`0` for gradient background, `2` for group in the observed fixtures) and whose float slot strongly correlates with per-layer parallax depth values (`0.0`, `0.15`, `0.35`, `0.4`, `0.5`, `0.7` observed across fixtures).
- `1020` group `1020` can instead carry a variable-length named reference payload such as:
  - `FileMerge_Assets/Color-10`
  - `FileMerge_Assets/Gradient-4`
  - `FileMerge_Assets/Gradient-3`
  - `FileMerge_Assets/Color-9`
  This is strong evidence that actual `renderingProperties` includes per-group style references to named colors/gradients.
- `1021` on stack/group families is a fixed-count 20-byte-per-entry record. Semantics are not fully closed yet, but real nonzero tuples are now captured in the workspace fixtures.

### Implementation added from this discovery

- Added `src/actool_linux/iconstack.py` with bounds-checked parsers for:
  - icon stack root rendering-property entries
  - icon stack auxiliary 20-byte entries
  - icon group named style references
  - named-gradient payloads
- Extended `carinfo.inspect()` so the new observable fixture families decode as:
  - `layer_stack_layers` / `icon_stack_layers` / `icon_group_layers`
  - `icon_stack_rendering_properties`
  - `icon_group_rendering_properties`
  - `icon_stack_auxiliary`
  - `named_gradient`
- Added `tests/test_iconstack.py` and expanded the suite to `120` tests (`OK`, `skipped=11`).
- Added `tools/iconstack_fixture_scan.py` for repeatable discovery of `1002`/`1019`/`1020`/`1021` fixtures.

### Boundary update

This phase **does** provide real current fixture bytes for the observable families underlying `stackData` / `renderingProperties` work. What remains incomplete is not fixture existence but the **complete semantic naming of every field** in the `1019` root `1020` records, the `1021` auxiliary records, and the full `ARGG` named-gradient payload grammar.

## 2026-07-14 — Appearance registry parsing and larger Xcode iconstack sample

- Added optional APPEARANCEKEYS / LOCALIZATIONKEYS registry parsing to `CARFile` and surfaced it through `carinfo.inspect()`.
- Real macOS iconstack fixtures now decode their appearance registry directly instead of inferring appearance IDs only from `assetutil` text.
- Verified on real copied fixtures:

```text
NSAppearanceNameSystem   -> 0
NSAppearanceNameDarkAqua -> 1
NSAppearanceNameAqua     -> 8
ISAppearanceTintable     -> 10
```

- The public brandassets target-device-tv fixture uses the ordinary public registry only:

```text
UIAppearanceAny -> 0
```

- Added `tests/test_car_appearance_registry.py`; full suite increased to `122` tests, `OK (skipped=11)`.

### Larger Xcode main-resource iconstack sample

- Pulled a targeted JSON dump from the main Xcode 26.5 resource CAR (`xcode-main-iconstack-dump.json`) limited to `Xcode*`, `XcodeCloud*`, and `XcodeIntelligence*` iconstack assets.
- Confirmed current named-gradient payloads across this larger sample:
  - signature `ARGG`
  - `stop_count=2`, `mode=1` for two-stop gradients
  - `stop_count=1`, `mode=0` for one-stop gradients
- All observed Xcode main-resource gradient payloads shared the same scalar tuple:

```text
scalar_1 = 0.0
scalar_2 = 0.5
scalar_3 = 0.0
scalar_4 = 0.5
scalar_5 = 1.0
```

- This contrasts with the Firefox/FileMerge family, which uses different scalar tuples, confirming that these five floats encode real gradient geometry/behavior rather than placeholder noise. The exact field names remain unresolved, so the parser still reports them conservatively as scalar fields.
- The larger Xcode sample also showed appearance-dependent `1019` auxiliary tuples using values such as:
  - `u32_2` in `{0,2,3}`
  - `f32_1` in `{0.0,0.5,0.6,0.7,0.9}`
  - `f32_2` in `{0.0,0.5,0.6,1.0}`
- This strengthens the conclusion that the `1021` per-entry auxiliary block is carrying actual per-layer parallax/style semantics rather than unused padding.

## 2026-07-14 — Broad iconstack semantics scan and Xcode 26 generation matrix for `--target-device tv`

- Added reusable tools:
  - `tools/iconstack_semantics_scan.py`
  - `tools/brandassets_xcode_matrix.py`
- Ran the broad semantics scan on the current Apple host across `/Applications` + `/System/Library` (`1183` CARs sampled, `148` cars with `1002/1019/1020/1021` hits). Evidence: `iconstack-semantics-summary.json`.

### Root style vs referenced part correlation

Observed `1019` root `1020` entry kind strongly correlates with the referenced child part from `1012`:

```text
217:0  -> 11 rows   (named color children)
247:0  -> 532 rows  (named gradient children)
246:2  -> 1592 rows (icon group children)
246:0  -> 73 rows   (exception subset still unresolved)
```

This is now the strongest current evidence that root-style `kind=2` denotes the icon-group branch, while `kind=0` denotes the fill/background branch (named color or gradient). The `246:0` exception family remains unresolved and is preserved explicitly rather than guessed.

### Root style value distribution

For root-style `kind=0`, values are overwhelmingly `0.0` with only a very small tail (`0.12` observed 3 times). For root-style `kind=2`, values span a wide range including `0.0`, `0.1`, `0.15`, `0.2`, `0.23`, `0.25`, `0.3`, `0.35`, `0.406`, `0.5`, `0.6`, `0.8`, and `1.0`, which is consistent with a real per-layer parallax/depth control rather than a boolean/enum.

### Group style reference grammar

Broad scan summary for `layout 1020` group-style payloads (`TLV 1020` interpreted as variable-length references):

```text
group_style_count_counts: {1: 1179}
group_style_kind_counts:  {1: 1095, 0: 84}
group_style_name_kind:    {other: 532, gradient: 276, color: 371}
```

Implications:

- the observable count field is always `1` in the scanned current fixtures;
- `kind=1` is dominant;
- names often target named colors or named gradients, confirming that this branch of `renderingProperties` links groups to named style assets;
- there is also a nontrivial `kind=0` family that remains unresolved and must not be overclaimed.

### Named gradient grammar

The broad scan covered `655` parsed `layout 1021` fixtures. Results:

```text
stop_count:mode -> count
2:1 -> 611
1:0 -> 44
```

All `655` parsed fixtures shared the exact same scalar tuple:

```text
(0.0, 0.5, 0.0, 0.5, 1.0)
```

This means the `ARGG` payload grammar is no longer only locally observed — the same five scalars repeat across the entire current installed sample. That is strong evidence they are fixed default gradient geometry parameters in this current family, although the exact field names remain unresolved.

### Xcode 26 generation matrix for public tvOS brandassets target-device path

Ran the public `.brandassets` probe across every installed Xcode 26 app alias. Evidence: `brandassets-xcode26-targettv-matrix.json`.

Results:

- `base` case (no `--target-device tv`):
  - Xcode `26.0.1` through `26.6`: rc `0`, no `Assets.car`
- `target_tv` case (`--target-device tv`):
  - Xcode `26.2`, `26.3`, `26.4.1`, `26.5`, `26.6`: rc `0`, **`Assets.car` materialized**
  - Xcode `26.0.1` and `26.1.1`: rc `1`, no `Assets.car`, but the failure is environmental on this host:

```text
No simulator runtime version from ["23K51", "23L243a", "23L470"] available to use with appletvsimulator SDK version 23J352/23J576
```

So the current evidence supports this conservative statement:

- from Xcode `26.2` onward on the tested host, public `.brandassets` materialization requires `--target-device tv`;
- the older `26.0/26.1` target-device path could not be fully evaluated on this host due unavailable matching runtimes, not due contradictory successful behavior.

- Full local suite after parser + registry additions: `122` tests, `OK (skipped=11)`.

## 2026-07-14 — iconstack builders and targeted unresolved-family sampling

- Added iconstack payload builders/serializers to close the round-trip loop for the currently observed real fixture families:
  - `build_iconstack_root_style_list(...)`
  - `build_iconstack_aux_list(...)`
  - `build_iconstack_group_style_reference(...)`
  - `build_named_gradient_payload(...)`
- Added lightweight inferred labels in `iconstack.py` based on current evidence, explicitly marked as inferred rather than definitive:
  - root-style kind names (`fill-or-gradient`, `icon-group`)
  - root-style inferred role against referenced child part (`named-color-fill`, `named-gradient-fill`, `icon-group-depth`, `group-default`, `group-exception`)
  - group-style inferred kind names and name categories (`blank`, `color`, `gradient`, `other`)
- Extended `carinfo.inspect()` so decoded iconstack rendering-property rows now surface these inferred labels alongside the raw fields.
- Expanded `tests/test_iconstack.py` to cover the new builders/round-trips and blank-name group-style handling.
- Full local suite after these additions: `123` tests, `OK (skipped=11)`.

### Targeted unresolved-family sampling

Added `tools/iconstack_exception_samples.py` and extracted concrete current examples for the remaining unresolved subsets. Evidence:

- `iconstack-exception-samples.json`
- `iconstack-targeted-stats.json`

Observed:

- root-style `part246 kind0` value distribution:

```text
0.0  -> 70 rows
0.12 -> 3 rows
```

- sampled `part246 kind0` rows point to real `AppIcon/Group N` children (for example `Group 3`, `Group 4`) and overwhelmingly use value `0.0`, supporting the current `group-default` placeholder label. The small `0.12` trio remains unresolved.
- group-style `kind0` names are dominated by blank references:

```text
<blank> -> 73
```

with a very small tail of explicit color names:

```text
AppIcon/Color-1 -> 2
SiwAIcon_Assets/Color-2 -> 2
ClockBaseIcon-Arabic_Assets/Color-2 -> 2
ClockBaseIcon-Devanagari_Assets/Color-2 -> 2
... single-row color tails ...
```

- group-style `kind1` blank-name rows are also common:

```text
<blank> -> 459
```

Boundary update:

- `kind0` vs `kind1` on group-style references is still not semantically final.
- however, we now know the unresolved current population is not arbitrary: it is concentrated in blank-name records plus a small number of explicit color-name references, which is a much narrower target for the remaining naming work.
