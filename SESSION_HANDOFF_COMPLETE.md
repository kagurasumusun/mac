# actool-linux — Complete cross-session handoff

Last updated: 2026-07-13 (Etc/GMT-9) - Session vyUvDyfVq5tQ5Ll20bR0

This document is the authoritative human-readable continuation record. It describes observable engineering evidence, not hidden chain-of-thought. Read this file, `PROJECT_STATE.json`, `ENGINEERING_LOG.md`, and `EVIDENCE_MANIFEST.json` before changing claims.

## 1. Mission

Build a clean-room, Linux-capable replacement for Apple Xcode `actool` and CoreUI CAR generation. Generated CARs must be accepted by Apple readers/framework consumers. Reverse engineering is limited to observable commands, generated containers, public catalog inputs, framework strings/symbol names, and consumer behavior. Do not copy or redistribute Apple private binaries or implementation code.

Never claim 100% actool compatibility without evidence. “Implemented”, “Apple assetutil verified”, “AppKit verified”, “Simulator materialized”, and “experimental/fixture-gated” are distinct states.

## 2. User requirements and operational constraints

- Respond in Japanese.
- Prefer implementation and repeated Apple validation over planning.
- Mac tools/Simulators are accepted substitutes for non-Mac physical devices.
- Deliver a ZIP after every milestone.
- Preserve exact verification boundaries across sessions.
- Never run `exit`, `logout`, Ctrl-D, or commands that terminate the shared Upterm tmux/shell.
- Detach client-side only. Use `run_upterm_interrupt.py` only for a genuinely stuck foreground process.
- Clean-room: observe behavior/format; do not copy private Apple source/binaries.
- Keep readers bounds-checked and reject malformed references.

## 3. Authoritative local workspace

```text
/home/user/actool-linux
```

ZIP is regenerated at:

```text
/home/user/actool-linux-source.zip
```

The local Git baseline is old; most current files are working-tree modifications/untracked. Do **not** use `git archive`. Package the filesystem while excluding `.git`, caches, build/dist, node_modules, and virtual environments.

Test command:

```bash
cd /home/user/actool-linux
PYTHONPATH=src python3 -m unittest discover -s tests -q
```

Current result:

```text
Ran 89 tests
OK
```

Optional local dependencies installed during development:

```text
lzfse 0.4.2
cairosvg 2.9.0
cairocffi 1.7.1
cssselect2 0.9.0
```

Minimal environments intentionally skip optional-backend tests.

## 4. Current Apple host/session

Current Upterm session:

```text
Session: vyUvDyfVq5tQ5Ll20bR0
SSH: ssh GPGyZL9N7vxJupq8TAL1@uptermd.upterm.dev
Host: uptermd.upterm.dev:22
Force command: tmux attach -t upterm
```

Identity:

```text
/home/user/.ssh/arena_upterm_ed25519
```

Always run first:

```bash
chmod 600 /home/user/.ssh/arena_upterm_ed25519
```

Safe command helper:

```bash
python3 /home/user/run_upterm_command.py GPGyZL9N7vxJupq8TAL1 "COMMAND" WAIT_SECONDS
```

Observed host:

```text
macOS 26.4
Build 25E246
Xcode 26.5
Build 17F42
```

Installed Xcode 26 app/aliases include 26.0.1, 26.1.1, 26.2, 26.3, 26.4.1, 26.5, and 26.6. Previous sessions `b8btbueUHxFMnZpY5cHt` and `VtnenbVcaWmY2Jd5MyHJ` are historical and may reject authentication.

SCP can return a nonstandard final status after transferring. Verify destination size/hash explicitly.

## 5. High-level verified status

### Local tests

```text
89/89 pass
```

### Apple reader generation matrix

`apple-consumer-matrix.json`:

```text
100 rows
100 assetutil passes
```

Covers Xcode 16.0–16.4 and 26.0.1–26.3 aliases across:

```text
macosx, iphoneos, appletvos, watchos, xros
```

This is reader acceptance of an independently generated mixed CAR, not full actool behavior.

### Installed Simulator runtime matrix

`runtime-consumer-matrix-verified.json` is authoritative:

```text
iOS      26.2 / 26.4.1 / 26.5  PASS
tvOS     26.2 / 26.4   / 26.5  PASS
watchOS  26.2 / 26.4   / 26.5  PASS
visionOS 26.2 / 26.4.1 / 26.5  PASS
```

Every row completed build, device creation, boot, install, launch, CAR materialization, screenshot, shutdown, and delete.

- iOS/tvOS: `ACTOOL_RUNTIME_PASS 64 64` unified-log marker.
- watchOS/visionOS: retained screenshots contain expected cyan CAR pixels.
- Modern standalone watch app uses `WKApplication=true` and `WKWatchOnly=true`; `WKWatchKitApp=true` is obsolete WatchKit 1.0 and is rejected.

### Xcode CLI contracts

- 30 focused stdout diagnostic contracts byte-identical with Xcode 26.5.
- Schema-3 core diagnostics: 18/18 byte-identical stdout and exit code.
- Corrupt/malformed extension: 8/8 byte-identical stdout and exit code.
- Seven Xcode 26 releases × 94 cases = 658 contracts accounted after one transient timeout retry.
- All Apple stderr streams in the 658 option matrix were empty.
- Corrupt PNG is a known stderr case with four dynamic AssetCatalogSimulatorAgent lines.

### Xcode version result plists

Byte-identical mappings:

```text
16.0   23094
16.1   23504
16.2   23504
16.3   23727
16.4   23727
26.0.1 24128
26.1.1 24412
26.2   24506
26.3   24506
26.4.1 24765
26.5   24765
26.6   24765
```

See `tests/test_version_matrix.py`, `xcode-actool-version-matrix.json`, and `xcode-version-extended.json`.

## 6. Implemented format/core capabilities

### BOM/CAR

- Bounds-checked BOMStore reader/writer.
- CARHEADER, EXTENDED_METADATA, KEYFORMAT.
- RENDITIONS, FACETKEYS, BITMAPKEYS.
- Variable and numeric B+ trees at arbitrary depth.
- Internal separators, final children, leaf links, cycle/shared-node rejection.
- Deterministic repacker.
- 140-facet independently generated all-multilevel CAR accepted by Apple.
- 5,000-facet Apple oracle parsed.

### CSI/TLV

- Bounds-checked CSI headers and payload limits.
- TLV 1001 slices, 1003 metrics, 1004 blend, 1005 UTI, 1006 orientation, 1007 additional metadata, 1010 atlas link, 1018/1019 symbols.

### Images/data/colors

- DATA/NSDataAsset.
- JPEG and HEIF/HEIC.
- sRGB and Display P3 named colors.
- PNG GA8, RGB, RGBA, indexed 1/2/4/8-bit, GA16, Adam7.
- Premultiplied BGRA/ARGB deepmap2.
- Palette deepmap2 with optional LZFSE index plane.
- PDF preserved vector plus raster fallbacks.
- SVG preserved vector plus automatic fallbacks.
- Multi-entry `.xcassets`, legal placeholders, missing/unsupported slot filtering.
- Scale, idiom, appearance, localization selectors.

Color parser observation:

- Decimal string (`"0.5"`) is float.
- Integer string (`"2"`) is byte component `2/255`.
- Missing RGB components default to zero.

### CBCK

- MLEC mode 3 / codec 4.
- KCBC chunk headers and independent LZFSE streams.
- AppIcon CBCK/MSIS records.
- Bounds-checked parser/decompressor.
- UIKit Simulator CBCK materialization.
- Ordinary image boundary probes selected deepmap2, not CBCK.

### AppIcons

- iOS/iPadOS, tvOS, watchOS, macOS, visionOS idioms.
- Part 220 image and part 218 MSIS.
- Largest dimension-applicable source selection for multi-entry AppIcon catalogs.
- Platform sidecar manifests.
- Partial-info plist.
- Empty roles, dimensions, missing named icon contracts.

### Symbols

- Part 59, SVG, layout 1017.
- TLV 1018/1019.
- Nine weights and S/M/L template expansion.
- Apple assetutil reports Vector Glyph.

### Packed atlas

- INLK/KLNI metadata parser/writer.
- Deterministic shelf packing.
- Bounded single/multi-page output.
- Layout 1003 links and layout 1004 PackedImage pages.
- Single and multi-page outputs accepted by Apple.
- Exact Xcode packing/page heuristic is **not** reproduced.

### Layers/Image Stack

- tvOS/visionOS layer keys.
- `.imagestack`, `.imagestacklayer`, `layers`, brand `assets` traversal.
- Layer scale/order.
- Apple tvOS assetutil accepted compiled two-layer hierarchy.
- vision depth values in dimension2.

### Watch complication keys

- 12 family IDs in subtype.
- 5 role IDs in dimension2.
- Apple assetutil key recognition.
- Runtime watch materialization.
- Private compositor registry equivalence not proven.

### Thinning

- Idiom, scale, appearance, localization selection.
- Universal/Any/unlocalized fallback.
- EXTENDED_METADATA arguments.
- Target-device and model/OS CLI integration.
- Exact Apple device-model policy remains partial.

## 7. Diagnostic/CLI behavior implemented

- Default XML result plist.
- Unknown option, including option position behavior.
- No input and mixed existing/missing input.
- Absolute path normalization and duplicate input coalescing.
- Valueless `--warnings`, `--errors`, `--notices`, `--compress-pngs` switches.
- Missing platform/deployment notices.
- Malformed JSON and invalid UTF-8 notice.
- Top-level array notice.
- Non-array images/non-object entries silently ignored.
- Missing info dictionary silently accepted.
- Missing image and unsupported idiom/scale ignored.
- Duplicate slots: first assigned slot wins.
- Invalid/missing AppIcon roles and dimensions.
- Missing AppIcon/launch image ordered errors and output ordering.
- Incompatible tvOS/visionOS device filter notice.
- Corrupt PNG: Distill error, exit 1, Assets.car listed, four-line dynamic stderr shape.
- Corrupt PNG safe divergence: Apple leaves malformed CAR; Linux emits safe readable failure CAR.

## 8. Private compositor investigation boundary

Observable CoreUI strings confirm:

```text
_CUILayerStackRendition
kCUIRenditionTypeLayerStack
kCUIRenditionTypeIconLayerStack
kCUIRenditionTypeSolidLayerStack
addLayerStackWithSize:type:stackData:name:atScale:withRenderingProperties:
addIconLayerStackWithSize:stackData:name:atScale:withRenderingProperties:
```

A controlled tvOS brand/Top-Shelf and visionOS stack Apple oracle exited 0 but emitted no CAR and no diagnostic. `compositor-oracle.json` records the rejected input hypothesis.

`layer-stack-fixtures.json` scanned 600 installed CARs and found no observable aggregate Layer Stack fixture. `stackData` and `renderingProperties` binary grammar therefore remain fixture-gated. Do not invent or claim exact private aggregate equality.

Ordinary layer records and `.imagestack` compilation are Apple verified; aggregate compositor records are not.

## 9. Legacy palette boundary

- CoreUI retains palette-img decoder/capability strings.
- 24 generated indexed-PNG probes selected deepmap2.
- 300 System Library CARs + 300 Applications/Xcode CARs scanned: zero palette-img hits.
- Writer remains fixture-gated.

Evidence: `palette-fixture-scan.json`, `palette-fixture-apps.json`.

## 10. Remaining work (must not be reported complete)

### Private/system compositor

- Top Shelf aggregate stackData/renderingProperties.
- visionOS private parallax/glass/shadow/specular metadata.
- private watch complication aggregate/registry semantics.
- SpringBoard, tvOS Home, watch face, vision Home, Dock/Finder Apple-vs-Linux screenshot pixel diffs.

### Exact heuristics

- Xcode exact atlas ordering/padding/alignment/page split.
- Full AppIcon deployment-target side effects, alternate icons, `.icns` differences.

### Older generations/runtime

- Xcode 16 full 94-case extended matrix requires a host with Xcode 16 installs.
- Xcode 26.0/26.1 CBCK image builds are blocked on current host by missing SDK-matching runtime build 23A339.
- Current host runtimes are 23C54/23E254a/23F77 families.

### Additional asset classes

- Sticker packs.
- Full Top Shelf aggregate role output.
- ODR asset-pack emission.
- memory/graphics/size-class/direction/state variants in all combinations.
- advanced multicolor/animated symbol effects.

### Legacy

- Actual palette-img writer/reader semantics require a real fixture.

## 11. Important accepted/rejected hypotheses

Accepted:

- Multi-entry same-facet scale/appearance keys are valid and Apple accepted.
- AppIcon CBCK is role-specific.
- Ordinary-image cases around `0x155555/rowBytes` remain deepmap2 in compatible Xcode 26.2–26.6 builds.
- Modern watch app package uses WKApplication.
- Integer color strings are byte/255.

Rejected/not established:

- Generic image size threshold causes CBCK: rejected by 45 compatible rows.
- Public-looking brand/stack hierarchy automatically yields private aggregate CAR: rejected; no CAR emitted.
- Installed system/Xcode CARs provide palette-img fixture: no hit in 600.
- Installed CARs provide aggregate Layer Stack fixture: no hit in 600.
- Apple corrupt-failure CAR is safe/readable: false; it references a missing block.

## 12. Evidence file map

Script inventory:

```text
USED_SCRIPTS.md
tools/session_helpers/run_upterm_command.py
tools/session_helpers/run_upterm_interrupt.py
```

Core evidence:

```text
ENGINEERING_LOG.md
PROJECT_STATE.json
VERIFICATION.md
HANDOFF.md
SESSION_HANDOFF_COMPLETE.md
EVIDENCE_MANIFEST.json
```

CLI/diagnostics:

```text
diagnostic-probe-xcode26.5.json
diagnostic-schema3.json
corrupt-diagnostic.json
option-cross-26.5.json
option-cross-all-unique.json
xcode-actool-version-matrix.json
xcode-version-extended.json
```

Runtime:

```text
simulator-runtime-inventory.json
runtime-consumer-matrix-verified.json
runtime-screenshots-verified/
runtime-watch2.json
runtime-fixed.json
runtime-264.json
runtime-edge.json
runtime-tv262.json
```

CAR/core:

```text
apple-consumer-matrix.json (may be outside project in older workspace snapshot)
multi-entry-info.json
multipage-info.json
image-stack-info.json
cbck-threshold-26.5-ios.json
cbck-threshold-all-unique.json
apple-corrupt-output.car
invalid-color-info.json
missing-color-info.json
```

Private/fixture scans:

```text
compositor-oracle.json
layer-stack-fixtures.json
palette-fixture-scan.json
palette-fixture-apps.json
```

## 13. Recommended next actions

1. Acquire a licensed aggregate Layer Stack CAR fixture or a valid Xcode project/template that emits one; parse only observable CAR/assetutil output.
2. Acquire a host with Xcode 16.0–16.4 and run `tools/option_cross_product.py` with the seven/old app paths.
3. Install an SDK-matching 23A339 Simulator runtime only if the user explicitly accepts the large Apple download; then rerun blocked Xcode 26.0/26.1 CBCK rows.
4. Build paired Apple-actool and Linux-actool icon apps for SpringBoard/Home/Dock screenshot comparison.
5. Probe atlas placement with controlled distinct-size assets once an Apple input path that triggers packing is found.
6. Continue malformed PDF/SVG/JPEG/HEIF and advanced symbol diagnostics.
7. Regenerate manifest, run tests, package ZIP, verify `unzip -t`, and report SHA-256.

## 14. Reproducible final checks

```bash
cd /home/user/actool-linux
PYTHONPATH=src python3 -m unittest discover -s tests -q
python3 tools/verify_handoff.py
python3 -m json.tool PROJECT_STATE.json >/dev/null
git diff --check
```

Package:

```bash
cd /home/user
rm -f actool-linux-source.zip
zip -qr actool-linux-source.zip actool-linux \
  -x 'actool-linux/.git/*' '*/__pycache__/*' '*.pyc' \
     '*/node_modules/*' '*/build/*' '*/dist/*' '*/.venv/*' '*/.cache/*'
unzip -t actool-linux-source.zip
sha256sum actool-linux-source.zip
```

## 15. Git/push boundary

Historical push attempts failed:

```text
remote: Permission to kagurasumusun/mac.git denied to github-actions[bot].
fatal: HTTP 403
```

Workflow requires:

```yaml
permissions:
  contents: write
```

Until credentials are fixed, the source ZIP and workspace are authoritative.
