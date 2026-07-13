# Continuation Memo — 2026-07-13

This memo is a compact exact-session carryover for the current `actool` branch workspace.
Read together with:

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

## Current remote Apple host

Active Upterm session during this continuation:

- session: `xGBjvOFB6rf9fCdPeiIx`
- host: `uptermd.upterm.dev:22`
- remote repo: `/Users/runner/work/mac/mac`

Observed host state:

- macOS `26.4` (`25E246`)
- Xcode default `26.5` (`17F42`)
- installed Xcode 26 apps present: `26.0.1`, `26.1.1`, `26.2.0`, `26.3.0`, `26.4.1`, `26.5.0`, `26.6.0`
- installed simulator runtimes present:
  - iOS `26.2`, `26.4.1`, `26.5`
  - tvOS `26.2`, `26.4`, `26.5`
  - watchOS `26.2`, `26.4`, `26.5`
  - xrOS `26.2`, `26.4.1`, `26.5`

A project-local remote venv was created at `/Users/runner/work/mac/mac/.venv` and `lzfse 0.4.2` was installed there for AppIcon/CBCK validation.

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
- `vision-depth-verify.json`
- `appicon-vision-verify.json`
- `framework-symbol-audit.json`

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
