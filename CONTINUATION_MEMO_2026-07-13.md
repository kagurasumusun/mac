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
- `complicationset-endtoend-verify.json`
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

These currently observed payloads can also be serialized back byte-for-byte for the public oracle forms, which closes the loop on the known metadata grammar even though a full aggregate writer is still unfinished.
An experimental aggregate writer path now exists for this oracle family: it can emit a layout-1018 metadata rendition plus the paired 1007/1008 texture-related renditions for the two observed `dimension1` modes, but it still requires Apple validation before being treated as consumer-compatible.

This is the first direct public-source oracle for a solid image stack aggregate path, and it is no longer opaque to the parser.

#### `complicationset-endtoend-verify.json`
A synthetic public `.complicationset` source fixture compiled with Apple actool on Xcode 26.5 demonstrates that the documented watch complication set path is not an opaque private aggregate. When `--complication Complication` is supplied, Apple emits:

- one packed page (`1004`) named `ZZZZPackedAsset-2.1.0-gamut0`
- three linked image renditions (`1003`)
- explicit `KLNI` links using token pairs `(1,9)`, `(2,181)`, `(12,2)`, `(15,5)`

The clean-room compiler now reproduces this structure closely for named complication sets.

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

## 2026-07-14 follow-up

### Current live host

- primary usable session in this follow-up: `QX8mPOpocAXnJg0BOxaB`
- ssh target: `QX8mPOpocAXnJg0BOxaB@uptermd.upterm.dev`
- observed host:
  - macOS `26.4`
  - Xcode `26.5`
  - build `17F42`
- repo path: `/Users/runner/work/mac/mac`

### Session health changes

- `LUnMD48Mddy4PP4KeqJX`: returned `Permission denied (publickey)` in this follow-up.
- `ZrWtAfDSvKdWHtrrmfNR`: returned `Permission denied (publickey)` in this follow-up.
- The working host for this follow-up was therefore the current 26.5 host above.

### Local workspace recovery

The local repo had drifted backward and tests were broken. It was reset to the remote continuation tip:

```bash
cd /home/user/mac
git fetch origin actool
git reset --hard origin/actool
git clean -fd
PYTHONPATH=src python3 -m unittest discover -s tests -q
```

Recovered state:

- `HEAD d0ab293` — `Add experimental solid image stack aggregate writer`
- local tests: `Ran 115 tests`, `OK (skipped=11)`

### New concrete discoveries in this follow-up

#### 1. `renderingProperties` is still observable in current Apple AssetRuntime

A direct raw-byte scan of Xcode 26.5 AssetRuntime private frameworks found:

- `renderingProperties` present in:
  - `.../System/AssetRuntime/.../CoreUI.framework/Versions/A/CoreUI`
- `stackData` present in:
  - `.../System/AssetRuntime/.../CoreUI.framework/Versions/A/CoreUI`
  - `.../System/AssetRuntime/.../CoreThemeDefinition.framework/Versions/A/CoreThemeDefinition`

Exact nearby observable selectors/strings now captured:

- `_addLayerStackWithSize:type:stackData:name:atScale:withRenderingProperties:`
- `addLayerStackWithSize:stackData:name:atScale:`
- `addIconLayerStackWithSize:stackData:name:atScale:`
- `addIconLayerStackWithSize:stackData:name:atScale:withRenderingProperties:`

This is stronger than the earlier generic layer-stack string audit because it ties `renderingProperties` and `stackData` directly to current AssetRuntime layer-stack/icon-layer-stack builder entry points.

Evidence:

- `assetruntime-layerstack-symbols-26_5.json`
- `coreui_exact_rendering_stack_terms_26_5.txt`
- `coretheme_rendering_stackdata_context_26_5.txt`

#### 2. Current parallax editing surface tightened further

`AssetCatalogKit` exact observable strings reconfirm the current parallax editor/control surface:

- `_parallaxImages`
- `_parallaxLayerDepths`
- `_setDefaultParallaxLayerDepths`
- `_setParallaxImages:`
- `_setParallaxLayerDepths:`
- `maximumParallaxDepth`
- `maximumParallaxImages`
- `parallaxDisplayConfiguration`
- `parallaxDisplayConfigurationForChild:`

Evidence:

- `assetruntime-layerstack-symbols-26_5.json`
- `assetcatalogkit_parallax_context_26_5.txt`
- `assetcatalogkit_parallax_context2_26_5.txt`

#### 3. Public Top Shelf / brandassets still does not materialize on current Xcode 26.5

Pulled the actual template AppIcon name from:

- `tvOS App Base.xctemplate/TemplateInfo.plist`

Observable value:

```text
ASSETCATALOG_COMPILER_APPICON_NAME = tvOS App Icon & Top Shelf Image
```

Then re-ran a clean public `.brandassets` probe using:

- asset name `tvOS App Icon & Top Shelf Image.brandassets`
- two imagestacks sized `1280x768` and `400x240`
- top-shelf imagesets sized `1920x720` and `2320x720`
- `--app-icon 'tvOS App Icon & Top Shelf Image'`

Observed Apple result on Xcode 26.5:

- rc `0`
- stderr empty
- requested partial plist emitted
- **no `Assets.car`**

So even with the template-correct AppIcon name plus the documented public `.brandassets` directory shape, the hidden applicability/schema gate is still unresolved.

Evidence:

- `brandassets-probe-26_5-summary.json`
- reusable helper: `tools/brandassets_probe.py`

### New helper tools added

- `tools/assetruntime_string_probe.py`
- `tools/brandassets_probe.py`

### State delta vs previous memo

This follow-up upgrades the state from:

- "`renderingProperties` / `stackData` existence uncertain in current Apple stack"

to:

- "both are definitely still present in current AssetRuntime private frameworks, and are directly adjacent to layer-stack/icon-layer-stack builder selectors"

But the following are **still not solved**:

- real fixture bytes for aggregate `renderingProperties`
- real fixture bytes for aggregate `stackData`
- source-level field mapping for the private parallax grammar
- a public or private materializing Top Shelf / `.brandassets` input schema

## 2026-07-14 second follow-up — actual brandassets materialization gate and real iconstack fixtures

### Current active host in this phase

- session: `NoqRgiONpDaSlIzApHRa`
- ssh target: `NoqRgiONpDaSlIzApHRa@uptermd.upterm.dev`
- observed host:
  - macOS `26.4`
  - Xcode `26.5`
  - build `17F42`
- repo path: `/Users/runner/work/mac/mac`

### Major discoveries

#### 1. Public `.brandassets` does materialize — but only when `--target-device tv` is supplied

The earlier public `.brandassets` probes were incomplete because they omitted the device-target gate.
A new 10-case Apple matrix now shows:

- without `--target-device tv`:
  - rc `0`
  - partial plist only
  - no `Assets.car`
- with `--target-device tv` and `--app-icon 'tvOS App Icon & Top Shelf Image'`:
  - rc `0`
  - partial plist emitted
  - **`Assets.car` emitted**

`--product-type com.apple.product-type.application` and `--include-all-app-icons` only matter once `--target-device tv` is already present; neither alone causes materialization.
`--target-device tv` without `--app-icon` still does not materialize.

Evidence:

- `brandassets-target-device-tv-matrix.json`
- `brandassets-target-device-tv-assetutil-summary.json`
- copied CAR fixture: `fixtures/brandassets-target-tv-Assets.car`
- parsed local inspect: `brandassets-target-tv-inspect.json`

#### 2. The materialized public tvOS brandassets fixture gives a real `layout 1002` ImageStack oracle

The Apple-generated public fixture contains:

- root layout `1002`
- child layer images layout `12`
- flattened image part `208`
- radiosity image part `209`
- top-shelf images as ordinary deepmap2 image renditions

Apple `assetutil` reports the root records as:

- `AssetType = ImageStack`
- idiom `universal` for the small icon stack
- idiom `marketing` for the large icon stack

The root `1002` rendition carries TLVs:

- `1012`
- `1020`
- `1021`
- `1004`
- `1005`
- `1006`

For this public fixture the `1012` child references decode cleanly and the `1020` / `1021` entries are trivial zeros/ones.

#### 3. Real current `IconImageStack` / `IconGroup` / `Named Gradient` fixtures are now confirmed in many installed CARs

A broader installed-CAR scan found:

- `cars_with_hits = 148`
- layout counts:
  - `1019: 543`
  - `1020: 1665`
  - `1021: 655`

Observed hit families include:

- Firefox
- Chrome / Google Chrome for Testing
- Edge
- Xcode applications such as:
  - FileMerge
  - Accessibility Inspector
  - Create ML
  - Simulator
  - Instruments-family assets
  - main Xcode resource CAR

This is the first strong evidence that the previously missing private aggregate family is not rare at all — it is widespread in current installed application CARs.

Evidence:

- `iconstack-scan-summary.json`
- `fixtures/firefox-Assets.car`
- `fixtures/filemerge-Assets.car`
- `iconstack-fixture-summary.json`
- `firefox-iconstack-inspect.json`

#### 4. `renderingProperties` grammar is no longer fixture-less

The real fixtures show three important layers of grammar:

##### `layout 1019` / `IconImageStack`

- TLVs: `1012`, `1020`, `1021`, `1004`, `1005`, `1006`
- `1012` is a child-reference list:
  - background named gradient(s)
  - icon groups
- root `1020` uses fixed 13-byte-per-entry records
- the first u32 strongly correlates with entry kind:
  - `0` for gradient background in observed roots
  - `2` for icon groups in observed roots
- the float slot strongly correlates with per-layer parallax depth values observed in current fixtures:
  - `0.0`
  - `0.15`
  - `0.35`
  - `0.4`
  - `0.5`
  - `0.7`

##### `layout 1020` / `IconGroup`

- TLVs: `1012`, `1020`, `1021`, `1004`, `1006`
- `1012` references the underlying vector/image child
- group `1020` can contain a variable-length named style reference such as:
  - `FileMerge_Assets/Color-10`
  - `FileMerge_Assets/Gradient-4`
  - `FileMerge_Assets/Gradient-3`
  - `FileMerge_Assets/Color-9`

This is strong evidence that current real `renderingProperties` includes per-group style links to named colors and gradients.

##### `layout 1021` / `Named Gradient`

- payload begins with observable signature `ARGG`
- contains stop count, mode-like integer, several scalar fields, and named-color references
- current extracted examples reference names like:
  - `AppIcon_Assets/Color-2`
  - `AppIcon_Assets/Color-3`
  - `FileMerge_Assets/Color-4`
  - `FileMerge_Assets/Color-5`

This is now a real fixture family, not a string-only hypothesis.

### New implementation in this phase

Added:

- `src/actool_linux/iconstack.py`
- `tests/test_iconstack.py`
- `tools/iconstack_fixture_scan.py`

`carinfo.inspect()` now decodes the discovered fixture families as:

- `layer_stack_layers`
- `icon_stack_layers`
- `icon_group_layers`
- `icon_stack_rendering_properties`
- `icon_group_rendering_properties`
- `icon_stack_auxiliary`
- `named_gradient`

### Test status after this phase

```text
PYTHONPATH=src python3 -m unittest discover -s tests -q
Ran 120 tests
OK (skipped=11)
```

### What is still incomplete

These items remain unsolved and should still not be overstated:

- exact semantic naming of every field in root `1019` `1020` records
- exact semantic naming of every field in `1021` auxiliary entries
- full `ARGG` named-gradient field semantics
- exact writer parity for public tvOS brandassets `1002` / flattened / radiosity output
- complete private parallax grammar naming at the source-schema level

However, the state has materially changed:

- `renderingProperties` and `stackData` are **no longer fixture-less**
- there is now a real public `1002` ImageStack fixture
- there are now many real `1019` / `1020` / `1021` fixtures in installed current software

## 2026-07-14 third follow-up — APPEARANCEKEYS and larger Xcode iconstack sample

### New parser coverage

`CARFile` now parses optional:

- `APPEARANCEKEYS`
- `LOCALIZATIONKEYS`

and `carinfo.inspect()` surfaces both registries.

### Confirmed macOS iconstack appearance mapping

Real current iconstack fixtures now decode their own appearance registry directly:

- `NSAppearanceNameSystem -> 0`
- `NSAppearanceNameDarkAqua -> 1`
- `NSAppearanceNameAqua -> 8`
- `ISAppearanceTintable -> 10`

This is important because the observed `1019` / `1020` iconstack fixtures use appearance IDs `1`, `8`, and `10`, and these are now grounded in the actual CAR registry instead of only in `assetutil` text.

Test coverage added:

- `tests/test_car_appearance_registry.py`

Full suite now:

```text
Ran 122 tests
OK (skipped=11)
```

### Larger Xcode 26.5 iconstack sample

A targeted dump from the main Xcode 26.5 resource CAR was added:

- `xcode-main-iconstack-dump.json`

This confirms across `Xcode*`, `XcodeCloud*`, and `XcodeIntelligence*` icon assets:

- `ARGG` named-gradient payloads with:
  - `stop_count=2`, `mode=1` for two-stop gradients
  - `stop_count=1`, `mode=0` for single-stop gradients
- all observed Xcode main-resource gradients share the same scalar tuple:
  - `0.0, 0.5, 0.0, 0.5, 1.0`

That strongly suggests the five scalar fields encode real gradient geometry/behavior, not padding. The exact semantic names are still unresolved, so they should still be reported conservatively.

The same larger sample also strengthens the current hypothesis that `1019` auxiliary `1021` blocks carry real per-layer style/parallax semantics, with observed value families such as:

- `u32_2` in `{0,2,3}`
- `f32_1` in `{0.0,0.5,0.6,0.7,0.9}`
- `f32_2` in `{0.0,0.5,0.6,1.0}`

### State change

At this point the project is no longer missing fixture bytes for the aggregate family under investigation. The remaining work is **semantic naming and writer reproduction**, not basic fixture discovery.

## 2026-07-14 fourth follow-up — broad semantics scan and Xcode 26 generation matrix

### New reusable tools added

- `tools/iconstack_semantics_scan.py`
- `tools/brandassets_xcode_matrix.py`

### Broad semantics scan result

A broad installed-CAR scan over `/Applications` + `/System/Library` on the active Apple host produced:

- `sampled_cars = 1183`
- `cars_with_hits = 148`

Evidence:

- `iconstack-semantics-summary.json`

#### Root-style kind correlation

For `layout 1019` root `1020` records, the observed kind field correlates with referenced child part as follows:

- `217:0` — named color children
- `247:0` — named gradient children
- `246:2` — icon group children
- `246:0` — unresolved exception subset

This is now the strongest current evidence that:

- `kind=0` belongs to the fill/background branch
- `kind=2` belongs to the icon-group branch

while explicitly preserving the current unresolved `246:0` exception family.

#### Group-style reference statistics

Observed `layout 1020` group-style payloads show:

- `count` always `1` in the current scanned set
- dominant kinds:
  - `kind=1` — 1095 rows
  - `kind=0` — 84 rows
- referenced-name families:
  - `color` — 371
  - `gradient` — 276
  - `other` — 532

This strongly supports the interpretation that group `renderingProperties` links a group to one named style asset, often a named color or named gradient. The `kind=0` / `other` family remains unresolved.

#### Named gradient scan statistics

Across all parsed `layout 1021` current fixtures:

- `2:1` (`stop_count=2`, `mode=1`) — 611 rows
- `1:0` (`stop_count=1`, `mode=0`) — 44 rows

All `655` scanned gradients shared the same scalar tuple:

- `(0.0, 0.5, 0.0, 0.5, 1.0)`

This strongly suggests the five scalar fields are fixed default gradient geometry parameters in the current family, although the exact semantic names are still unresolved.

### Xcode 26 generation matrix for public `.brandassets`

Evidence:

- `brandassets-xcode26-targettv-matrix.json`

Observed across installed Xcode 26 apps:

- without `--target-device tv`:
  - `26.0.1` through `26.6` all rc `0`, no `Assets.car`
- with `--target-device tv`:
  - `26.2`, `26.3`, `26.4.1`, `26.5`, `26.6` all rc `0`, `Assets.car` emitted
  - `26.0.1` and `26.1.1` failed on this host because no matching AppleTV simulator runtime was installed for their older SDKs:
    - `23J352`
    - `23J576`

So the current conservative generation statement is:

- from Xcode `26.2` onward on the tested host, public `.brandassets` materialization requires `--target-device tv`;
- `26.0/26.1` remain environment-blocked rather than semantically disproved.

### Current local test state after this phase

```text
Ran 122 tests
OK (skipped=11)
```

## 2026-07-14 fifth follow-up — builders and unresolved-family narrowing

### New implementation in this phase

`src/actool_linux/iconstack.py` now has writer-side round-trip coverage for the observed current fixture grammars:

- `build_iconstack_root_style_list(...)`
- `build_iconstack_aux_list(...)`
- `build_iconstack_group_style_reference(...)`
- `build_named_gradient_payload(...)`

This closes the parser/serializer loop for the iconstack payload families that were discovered from real fixtures.

Also added conservative inferred labels (still not final semantics) for:

- root-style kind names
- root-style inferred role against referenced child part
- group-style kind names
- group-style name categories (`blank`, `color`, `gradient`, `other`)

`carinfo.inspect()` now surfaces those inferred labels.

### New targeted unresolved-family evidence

Added:

- `tools/iconstack_exception_samples.py`
- `iconstack-exception-samples.json`
- `iconstack-targeted-stats.json`

This narrowed the remaining unresolved sets substantially.

#### `part246 kind0` root-style rows

Current broad counts:

- `0.0` → `70`
- `0.12` → `3`

Sampled rows point to actual `AppIcon/Group N` children and overwhelmingly use `0.0`, which supports the current temporary label `group-default` for the common family.
The `0.12` trio remains unresolved and is now isolated as a tiny exception family.

#### group-style `kind0`

Current name distribution is dominated by blank references:

- `<blank>` → `73`

with only a very small explicit-color tail such as:

- `AppIcon/Color-1`
- `SiwAIcon_Assets/Color-2`
- `ClockBaseIcon-Arabic_Assets/Color-2`
- `ClockBaseIcon-Devanagari_Assets/Color-2`

#### group-style `kind1`

Blank-name rows are also common here:

- `<blank>` → `459`

So the remaining unresolved group-style work is now tightly bounded to:

- blank-name records
- a small explicit-color subset
- distinguishing what `kind0` vs `kind1` means when both can be blank

### Local test state after this phase

```text
Ran 123 tests
OK (skipped=11)
```
