# actool-linux

A clean-room, cross-platform implementation of the **observable command-line contract** of Apple's `actool`.

## Status

Active research implementation with bounds-checked BOM/CAR/CSI parsing and deterministic writing. Enabled catalog paths include data, JPEG, HEIF, sRGB/Display-P3 colors, mixed multi-assets, and verified PNG deepmap2 inputs (GA8/GA16/RGB/RGBA/indexed). PDF vector plus pre-rasterized 1×/2×/optional-3× fallbacks is available through `actool-pdf-car`. Optional LZFSE compression requires `pip install -e '.[lzfse]'` and is Apple-consumer-verified on macOS 26.4 / Xcode 26.5.

### Verified so far

- Linux full optional-dependency unit suite: 77 tests.
- Xcode 16.4 / CoreUI 918.5 parsing agrees with `assetutil` for header, platform, key format, facets, and rendition name/dimensions/scale.
- A 300-facet / 301-rendition CAR is parsed and compared with the Apple oracle.
- The Linux BOM writer can repack all blocks of a CAR into a newly generated container; Apple's `assetutil` accepts it.
- Linux independently generates a `.dataset` CAR from `Contents.json` plus source bytes. On macOS, `assetutil` reports the expected name, UTI, and length, and AppKit `NSDataAsset` loads the payload (`hello-linux-car`) from a test bundle.
- Linux independently generates JPEG and HEIF/HEIC `.imageset` CARs. On macOS, `assetutil` reports the expected encoding/dimensions, and actual app-bundle executables load both through `NSImage(named:)` and obtain TIFF representations.
- Linux independently generates sRGB and Display P3 `.colorset` CARs. On macOS, `assetutil` reports `[1, 0.5, 0.25, 0.75]`, and an app-bundle executable loads identical RGBA values through `NSColor(named:bundle:)`.
- Multiple data/JPEG/color assets can be emitted into one CAR, including variable-length facet names. A mixed CAR was accepted by `assetutil`, and one app process loaded all three through `NSDataAsset`, `NSImage`, and `NSColor`.
- A 100-row installed-Xcode/SDK consumer matrix opened the Linux-generated mixed CAR successfully in every row. Covered Xcode 16.0–16.4 and 26.0.1–26.3 app bundles/aliases, five SDK families, and CoreUI 918/971/972 readers.

These results cover the BOM container, CAR metadata, arbitrary-depth B+ trees, rendition keys, CSI header/TLV, RAWD data/JPEG/HEIF payloads, COLR sRGB/Display-P3 named colors, and verified arbitrary-size 8/16-bit GA, opaque RGB/ARGB, RGBA/ARGB, and indexed-palette-to-ARGB `MLEC/dmp2` PNG paths. The compiler processes every assigned Contents.json entry, including same-facet scale/idiom/appearance variants, while legally unassigned slots are ignored. PDF/SVG vectors, modern CBCK AppIcons, symbols, packed atlases, thinning, layers, watch family/role keys, and an explicit legacy `palette-img` indexed-PNG writer/parser are implemented with the verification boundaries documented in `ENGINEERING_LOG.md`. Exact Xcode atlas heuristics, private compositor semantics, historical automatic palette-img selection, and the complete option cross-product remain incomplete.

## Principles

- Reproduce behavior from independently created inputs and observable outputs.
- Do not copy, decompile, redistribute, or link private Apple implementation code.
- Record Xcode/macOS build identity with every oracle result.
- Treat compatibility as a tested matrix, not an unqualified “100%” claim.
- Keep parsers bounds-checked and fuzzable; treat catalogs/CAR files as untrusted.

## Development

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
python -m unittest discover -s tests -v
actool --version
```

## Oracle run (authorized Mac)

```sh
python3 tools/oracle.py Fixtures/Basic.xcassets \
  --case xcode-26.5-basic-macos --platform macosx --target 13.0
```

Oracle evidence contains commands, exit codes, diagnostics, output paths, sizes, and SHA-256 values. Generated Apple artifacts should not be committed unless their licensing and redistribution status has been reviewed.

Compare a CAR with Apple's metadata oracle:

```sh
python3 tools/compare_assetutil.py build/Assets.car
```

Inspect or deterministically repack on Linux:

```sh
actool-car-info Assets.car
actool-car-repack Assets.car Repacked.car
```

## Planned compatibility layers

1. CLI grammar, exit status, diagnostics, output partial-info plist.
2. Asset catalog semantic model and deterministic normalization.
3. BOM/CAR container reader with strict validation.
4. Rendition key/token model and supported payload codecs.
5. CAR writer behind oracle-gated feature flags.
6. Xcode-version fixture matrix and Apple consumer smoke tests.
7. Linux packaging, reproducibility, fuzzing, and conformance reports.

“Full” includes all of these workstreams, but each capability is marked supported only after repeatable evidence exists.

### Latest verified image support

The independent writer accepts non-interlaced and Adam7-interlaced supported PNGs and emits deepmap2. Multiple 1×/2×/3× renditions can share one named facet via `png_rendition(..., scale=N)` (also JPEG/HEIF scale keys). Adam7 and same-facet 1×/2× were accepted by Xcode 26.5 `assetutil` and loaded by AppKit on macOS 26.4. See `ENGINEERING_LOG.md` for exact evidence and remaining compatibility boundaries.

### CBCK AppIcon writer

`build_app_icon_car(name, png)` now creates modern iOS phone/iPad AppIcon CAR records using independently generated chunked CBCK LZFSE data plus MSIS auxiliary records. Xcode 26.5 `assetutil` recognizes the output as 1024×1024 ARGB/LZFSE for both idioms. Install the optional dependency with `pip install -e '.[lzfse]'`. See `ENGINEERING_LOG.md` for the exact chunk grammar and validation boundary.

### Platform idioms and thinning

The rendition writer supports checked CoreUI idioms for universal, iPhone, iPad, tvOS, CarPlay, watchOS, marketing, macOS, and visionOS. `actool_linux.thinning` provides deterministic pre-BOM selection by idiom, scale, appearance, and localization while retaining fallback renditions, and the writer can record thinning arguments in `EXTENDED_METADATA`. Xcode 26.5 `assetutil` recognizes all nine independently generated idiom keys.

### Symbol sets

`.symbolset` discovery uses the `symbols` array. The writer emits CoreUI part-59 `SVG ` vectors with layout 1017, the 16-field glyph key schema, glyph weight/size slots, and symbol metrics/info TLVs. Xcode 26.5 `assetutil` recognizes an independently generated result as `Vector Glyph`. Advanced multi-weight template expansion and raster atlas fallbacks remain separate work.

### Packed atlases

`actool_linux.atlas` implements bounded TLV-1010 `INLK`/`KLNI` metadata parsing, including both the generic token-list form and Apple’s observed explicit packed-asset variant, deterministic shelf packing, layout-1003 linked image records, layout-1004 shared deepmap pages, and a layout-1005 atlas metadata path. Public `.spriteatlas` source catalogs are compiler-integrated and routed through an explicit atlas style derived from Apple’s SpriteKit template outputs. Xcode/assetutil accepts the generated CARs and identifies the shared packed-page renditions as `PackedImage`, but exact Xcode page splitting, placement, identifier derivation, and every auxiliary TLV still remain incomplete.

### Multi-weight symbols and platform AppIcons

SF Symbols template groups named `Weight-S`, `Weight-M`, or `Weight-L` are expanded into distinct CoreUI glyph keys for all nine standard weights and three sizes. Modern CBCK/MSIS AppIcon records can be emitted for iOS, tvOS, watchOS, macOS, and visionOS (including simulator platform aliases). Xcode 26.5 `assetutil` recognizes each generated icon with its platform idiom and LZFSE encoding.

### Layered icons, complications, and sidecars

`build_layered_icon_car` emits ordered layer-key images for tvOS or visionOS, and `build_watch_complication_car` emits watch-idiom subtype variants. Xcode 26.5 `assetutil` recognizes the layer and subtype keys. The compiler now emits complete compatibility PNG manifests for iOS/iPad, watchOS, and macOS; layered tvOS/visionOS icons are not incorrectly flattened.

### Runtime matrix and CLI contracts

`tools/simulator_runtime_matrix.py` inventories all installed iOS/tvOS/watchOS/visionOS runtimes and has an opt-in boot mode with bounded boot/cleanup timeouts and incremental JSON output. The CLI accepts target-device and device model/OS filters, product type, development region, PNG-compression, and on-demand-resource switches; a single target device drives rendition thinning and metadata recording.

## Session handoff

Read `HANDOFF.md` first when continuing in another session. `PROJECT_STATE.json` provides the same verification boundary in machine-readable form. Neither file upgrades partial features to verified status; detailed commands and observations remain in `ENGINEERING_LOG.md`.
