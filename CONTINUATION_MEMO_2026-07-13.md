# Continuation Memo — 2026-07-13

This memo is a compact exact-session carryover for the current `actool` branch workspace.
Read together with:

- `REMOTE_MACS.md`
- `HANDOFF.md`
- `SESSION_HANDOFF_COMPLETE.md`
- `ENGINEERING_LOG.md`
- `PROJECT_STATE.json`
- `EVIDENCE_MANIFEST.json`

## Workspace

- Local repo: `/home/user/mac`
- Branch: `actool`
- Latest local commit: `3a8c312` (`Refine watch AppIcon compiler applicability and add Apple oracles`)
- Latest source ZIP: `/home/user/mac-actool-linux-source.zip`
- Latest ZIP SHA-256: `d5c297ef35aff7cd1f31c190c30b8fcfa56d248cf3a38a7d3b680a47fd672cf2`

## Current remote Apple hosts

### Primary validation host

Current Upterm session during this continuation:

- session: `z4InTbNySiFAh5OZVudP`
- host: `uptermd.upterm.dev:22`
- remote repo: `/Users/runner/work/mac/mac`

Observed host state:

- macOS `15.7.7`
- Xcode default `16.4` (`16F6`)
- installed Xcode 16 apps/resources are present and were used for current-host source/fixture scans

### Additional analysis host

Additional Upterm session used for broader template/Xcode-tree analysis:

- session: `LUnMD48Mddy4PP4KeqJX`
- host: `uptermd.upterm.dev:22`
- remote repo: `/Users/runner/work/mac/mac`

Observed host state:

- macOS `15.7.7` (`24G720`)
- Xcode default `16.4` (`16F6`)
- installed Xcodes include `16.0`–`16.4` and `26.0`–`26.3`

### Legacy reference host

Second Upterm session used specifically for `palette-img` investigation:

- session: `ZrWtAfDSvKdWHtrrmfNR`
- host: `uptermd.upterm.dev:22`
- remote repo: `/Users/runner/work/mac/mac`

Observed host state:

- macOS `14.8.7` (`23J520`)
- default Xcode `15.4` (`15F31d`)
- installed Xcodes include:
  - `15.0`, `15.0.1`
  - `15.1`, `15.1.0`
  - `15.2`, `15.2.0`
  - `15.3`, `15.3.0`
  - `15.4`, `15.4.0`
  - `16.1`, `16.1.0`
  - `16.2`, `16.2.0`

## Latest implementation changes in this continuation

### 1. watchOS AppIcon compiler applicability

Files changed:

- `src/actool_linux/appicons.py`
- `src/actool_linux/compiler.py`
- `tests/test_appicons.py`
- `tests/test_catalog.py`

Behavior now implemented:

- `watch-marketing` AppIcon slots are treated as compiler-non-materializing for the tested watchOS path.
- The compiler emits only the requested partial plist for these watch cases.
- The partial plist is empty (`{}`), with no `Assets.car` and no sidecar PNGs.
- The generic “did not have any applicable content” error is now gated on actually having at least one platform-applicable slot.
- Partial-info plist icon dictionaries are emitted only on the observable iOS/iPadOS compiler path.

### 2. explicit visionOS depth retention revalidated

The explicit `depth` / `dimension2` handling for `.imagestack` vision/xros paths remains active and Apple-accepted after the AppIcon changes.

## Latest Apple verification artifacts added

- `watch-roleless-appicon-oracle.json`
- `watch-marketing-role-oracle.json`
- `watch-role-probe.json`
- `watch-marketing-xcode-matrix.json`
- `vision-depth-verify.json`
- `appicon-vision-verify.json`
- `framework-symbol-audit.json`
- `atlas-fixture-scan.json`
- `atlas-token-verify.json`
- `palette-fixture-scan-legacy.json`
- `palette-probe-legacy-matrix.json`
- `palette-string-audit-legacy.json`
- `paletteimg-verify-remote.json`
- `paletteimg-consumer-legacy-matrix.json`
- `render-layout-fixture-scan-current.json`
- `render-layout-fixture-scan-legacy.json`
- `source-asset-search-current.json`
- `source-asset-search-legacy.json`
- `source-asset-search-system-current.json`
- `source-asset-search-system-legacy.json`
- `template-term-search-current.json`
- `template-term-search-legacy.json`
- `xros-template-assetgeneration.json`
- `template-assetgeneration-summary.json`
- `template-assetgeneration-types.json`
- `solidimagestack-oracle.json`
- `interesting-car-scan-current.json`
- `interesting-car-scan-legacy.json`
- `interesting-car-scan-legacy-320.json`
- `xcode-source-oracle-263.json`
- `xcode-source-oracle-164.json`
- `atlas-source-oracle-compare.json`

### What these verify

#### `watch-roleless-appicon-oracle.json`
Apple `actool` and Linux compiler both:

- exit successfully
- emit only the partial plist
- produce an empty plist payload
- produce no CAR and no PNG outputs

#### `watch-marketing-role-oracle.json`
Same result as above even with `role=notificationCenter` on the tested `watch-marketing` slot.

#### `watch-role-probe.json`
Across these candidate watch roles:

- `notificationCenter`
- `companionSettings`
- `appLauncher`
- `quickLook`
- `longLook`

Xcode `26.0.1` through `26.6.0` all showed the same observable contract:

- rc `0`
- no output files in compile directory
- empty partial plist
- no stderr

#### `vision-depth-verify.json`
Apple `assetutil` still reports:

- layer `1` / `Dimension2=10`
- layer `2` / `Dimension2=20`
- idiom `vision`

#### `framework-symbol-audit.json`
Observable framework strings confirm continued evidence for:

- `kCUIRenditionTypeLayerStack`
- `kCUIRenditionTypeSolidLayerStack`
- `kCUIRenditionTypeIconLayerStack`
- Top Shelf validation strings
- AssetCatalogKit parallax-related symbols such as:
  - `_parallaxImages`
  - `_parallaxLayerDepths`
  - `_setParallaxLayerDepths:`
  - `maximumParallaxDepth`
  - `parallaxDisplayConfiguration`

This is evidence for discovery and targeting, not proof of private binary layout equivalence.

#### `atlas-fixture-scan.json`
Installed Apple CAR scan summary on the remote host:

- sampled `400` CARs
- `267` contained `PackedImage`
- `44` contained parseable `INLK` / linked-image atlas metadata
- `126,885` linked atlas images were observed in those sampled fixtures
- dominant token pairs were:
  - `1:9`
  - `2:181`
  - `24:0`
  - `25:5`

This is the current strongest observable evidence for atlas defaults, but it still does not reveal the exact Xcode page split heuristic from source inputs.

#### `atlas-token-verify.json`
After updating the writer to use observed deployment token `25:5` in both link metadata and rendition keys, the focused generated atlas no longer triggers `Asset Parent Image Missing` diagnostics in `assetutil` and is recognized as one `PackedImage` plus linked child images.

#### `palette-fixture-scan-legacy.json`
Legacy-reference host scan summary:

- sampled `800` installed Apple CARs
- `0` `palette-img` hits

#### `palette-probe-legacy-matrix.json`
Indexed-PNG generation matrix on the legacy-reference host:

- Xcode releases: `15.0`, `15.0.1`, `15.1`, `15.1.0`, `15.2`, `15.2.0`, `15.3`, `15.3.0`, `15.4`, `15.4.0`, `16.1`, `16.1.0`, `16.2`, `16.2.0`
- 448 rows total (sizes `2/16/64/256`, alpha on/off, bit depths `1/2/4/8`)
- every successful row selected `deepmap2`
- no tested legacy Xcode emitted `palette-img`

#### `palette-string-audit-legacy.json`
Legacy Xcode 15/16 frameworks still expose palette-related UI/rendering symbols.

#### `paletteimg-verify-remote.json`
Current-host Apple verification of the explicit clean-room `palette-img` writer:

- Xcode 26.5 `assetutil` reports `Compression = palette-img`
- `Encoding = ARGB`
- size `4x4`
- the wrapper compression type is `8`
- the decoded quantized payload contains 4 palette colors and 2-bit indices

#### `paletteimg-consumer-legacy-matrix.json`
An independently generated explicit `palette-img` CAR is accepted by `assetutil` across all installed legacy-reference Xcode releases:

- `15.0`, `15.0.1`
- `15.1`, `15.1.0`
- `15.2`, `15.2.0`
- `15.3`, `15.3.0`
- `15.4`, `15.4.0`
- `16.1`, `16.1.0`
- `16.2`, `16.2.0`

Each row reported `Compression = palette-img` and `Encoding = ARGB` for the generated 4×4 test CAR. This upgrades the legacy state from purely fixture-gated to an explicit writer/parser with consumer verification. What remains unproven is Apple actool’s historical automatic selection heuristic.

#### `render-layout-fixture-scan-current.json` / `render-layout-fixture-scan-legacy.json`
A lightweight parser-based installed-CAR scan was run on both hosts to look specifically for candidate aggregate fixtures.

- current host sample: 20 CARs
- legacy host sample: 30 CARs
- no sampled CAR contained CSI layout `1002` (LayerStack aggregate)
- observed layouts were dominated by ordinary image (`12`), atlas link/page (`1003` / `1004`), color (`1009`), and vector (`9`)
- the modern host also showed additional newer layouts (`1019`, `1020`, `1021`) that remain to be classified

#### `source-asset-search-current.json` / `source-asset-search-legacy.json` / `source-asset-search-system-current.json` / `source-asset-search-system-legacy.json`
Direct directory scans of installed Xcode app trees on both hosts found only `.xcassets` and `.appiconset` source directories. No `.brandassets`, `.complicationset`, `.imagestack`, or `.imagestacklayer` source directories were present in the scanned Xcode bundles. A broader sampled scan over `/Applications` + `/System/Library` on both hosts still surfaced only `.xcassets` and `.appiconset` in the captured source-asset set.

#### `template-term-search-current.json` / `template-term-search-legacy.json` / `xros-template-assetgeneration.json` / `template-assetgeneration-summary.json`
The resource/template text search did not reveal real `.brandassets` or `.complicationset` source fixtures, but it did expose several concrete template-side aggregate leads:

- visionOS Application templates mention `imagestack`
- inspected `TemplateInfo.plist` metadata shows `AssetGeneration` with:
  - `Type = solidimagestack`
  - `Name = AppIcon`
- additional template-side `solidimagestack` generation was observed in:
  - tvOS Game templates
  - macOS Game templates
  - MultiPlatform RealityKit Game templates
  - Compositor Services templates
- tvOS Top Shelf extension templates explicitly declare the extension point identifier:
  - `com.apple.tv-top-shelf`

These are the current best observable template-side leads for future aggregate AppIcon / Top Shelf generation work, even though they are still not byte-level output fixtures.

#### `template-assetgeneration-types.json`
A cross-Xcode extraction of public `AssetGeneration` metadata on the active modern host currently shows only these generation types:

- `appicon`
- `tvappicon`
- `solidimagestack`
- `stickersicon`

No explicit `brandassets` or `complicationset` AssetGeneration type was found in the scanned public TemplateInfo metadata, which further narrows where private aggregate generation is likely happening.

#### `solidimagestack-oracle.json`
A synthetic public-source `AppIcon.solidimagestack` catalog compiled with Apple actool on Xcode 26.5 demonstrates that Apple accepts the public `.solidimagestack` / `.solidimagestacklayer` source form and emits a richer aggregate-oriented CAR than the current clean-room layered-image path. The observable Apple output includes:

- `AssetType = SolidImageStack` in `assetutil`
- CSI layouts `1018`, `12`, `0`, `1007`, plus packed pages
- packed pages named `ZZZZPackedAsset-2.0.0-gamut0` and `ZZZZPackedAsset-2.1.0-gamut0`
- aggregate-associated TLVs `1012`, `1020`, and `1021` on the layout-1018 rendition

Those TLVs are now parser-decoded in the clean-room implementation:

- `1012`: layer reference list with geometry, opacity, and referenced rendition key tuples
- `1020`: per-layer 13-byte flag blocks
- `1021`: per-layer 20-byte reserved blocks

The same oracle also exposes additional texture-oriented payloads around layouts `1007` and `1008`. The clean-room parser now decodes the observed `RTXT` wrapper plus TLV 1014 auxiliary flag blocks as well.

This is the first direct public-source oracle for a solid image stack aggregate path, and it is no longer opaque to the parser.

#### `interesting-car-scan-current.json` / `interesting-car-scan-legacy.json` / `interesting-car-scan-legacy-320.json`
Installed CAR scans for candidate aggregate fixtures show:

- no `layout 1002` LayerStack aggregate fixtures in the scanned sets
- no watch complication keyed candidates in the scanned sets
- no vision layer/depth keyed aggregate candidates in the scanned sets
- current-host Top Shelf name hits were symbol/glyph resources rather than aggregate brandassets output

#### `xcode-source-oracle-263.json` / `xcode-source-oracle-164.json`
Public Xcode-bundled source catalogs were compiled with Apple actool and inspected with the local parser. This produced a reusable public packed-atlas oracle: multiple SpriteKit Particle File template asset catalogs compile into CARs containing layouts `1005`, `1004`, and `1003`.

#### `atlas-source-oracle-compare.json`
A focused compare on `SpriteKit Particle File.xctemplate/Smoke/Assets.xcassets` shows a concrete Apple-vs-clean-room atlas difference:

- Apple emits an extra layout `1005` metadata rendition
- Apple names the packed page `ZZZZExplicitlyPackedAsset-1.0.0-gamut0`
- Apple places/pads linked images at `(2,2,64,64)` and `(68,2,63,64)`
- Apple uses a distinct explicit `KLNI` tail variant with token pairs:
  - `(1,9)`
  - `(2,181)`
  - `(12,1)`
  - `(17,28258)`

The parser now supports this explicit packed-asset link encoding in addition to the previously observed generic token-list form.
A new `explicit` atlas writer style was also added, which emits a layout-1005 metadata rendition plus explicit-link `KLNI` records keyed back to the atlas identifier. This is materially closer to Apple for the public SpriteKit fixture. The latest refinement now crops non-transparent alpha bounds and emits TLV 1011 trim metadata, matching Apple on the public `spark` linked geometry `(68,2,63,64)` from the Smoke atlas oracle. Remaining atlas gaps are concentrated in identifier derivation and any still-unobserved auxiliary heuristics.
The catalog compiler now also recognizes public `.spriteatlas` source directories and routes nested 1x PNG members through this explicit atlas path.

## Test status

### Local

```text
PYTHONPATH=src python3 -m unittest discover -s tests -q
Ran 98 tests
OK (skipped=7)
```

### Remote focused slice

```text
PYTHONPATH=src python -m unittest tests.test_appicons tests.test_catalog -q
Ran 19 tests
OK
```

## Current verified generation / platform coverage

### Reader / consumer acceptance already established before this continuation

- Xcode `16.0`–`16.4`
- Xcode `26.0.1`–`26.3`
- SDK families:
  - `macosx`
  - `iphoneos`
  - `appletvos`
  - `watchos`
  - `xros`
- file: consumer matrix referenced in handoff docs

### Option / CLI contract coverage already established before this continuation

- Xcode `26.0.1`–`26.6`
- 658 option/platform cases
- file: `option-cross-all-unique.json`

### Version plist byte-identical coverage already established before this continuation

- Xcode `16.0`, `16.1`, `16.2`, `16.3`, `16.4`
- Xcode `26.0.1`, `26.1.1`, `26.2`, `26.3`, `26.4.1`, `26.5`, `26.6`

### Runtime matrix already established before this continuation

- iOS `26.2`, `26.4.1`, `26.5`
- tvOS `26.2`, `26.4`, `26.5`
- watchOS `26.2`, `26.4`, `26.5`
- visionOS/xrOS `26.2`, `26.4.1`, `26.5`
- file: `runtime-consumer-matrix-verified.json`

### New coverage added in this continuation

- watch-marketing AppIcon compiler behavior validated on Xcode:
  - `26.0.1`
  - `26.1.1`
  - `26.2.0`
  - `26.3.0`
  - `26.4.1`
  - `26.5.0`
  - `26.6.0`

## Still not complete / must not be overstated

These remain incomplete and must not be described as solved without new evidence:

- private compositor aggregate
- Home / Dock pixel-diff
- exact Xcode atlas page split / placement heuristic
- legacy `palette-img` writer/reader semantics without a real fixture
- Apple aggregate `stackData`
- `renderingProperties` binary layout
- private parallax grammar / complete vision metadata grammar
- private Top Shelf aggregate fixture
- private watch complication aggregate fixture
- Xcode 16 extended option matrix on a host that actually has Xcode 16 apps installed

## Push status

A local commit exists, but push from this environment failed because no GitHub credential was available:

```text
fatal: could not read Username for 'https://github.com': No such device or address
```

So the authoritative deliverables for this continuation are:

- workspace files
- local Git commit `3a8c312`
- the ZIP artifact

## Recommended next steps

1. Build a controlled Apple atlas oracle that actually emits `PackedImage` from Apple `actool`, then compare page split / placement across candidate heuristics.
2. Continue private aggregate discovery using observable Xcode/framework strings plus any newly discovered valid catalog schema for Top Shelf / Layer Stack.
3. Probe non-marketing AppIcon paths for watchOS/macOS/visionOS platform metadata and deployment side-effects.
4. If a host with Xcode 16 apps becomes available, rerun the extended 94-case matrix there.
5. If real Apple aggregate CAR fixtures become available, add parsers before attempting any writer claims.
