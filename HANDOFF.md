# actool-linux Engineering Handoff

> Canonical full handoff: `SESSION_HANDOFF_COMPLETE.md`. Machine-verifiable hashes: `EVIDENCE_MANIFEST.json`; run `python3 tools/verify_handoff.py`.

Last updated: 2026-07-16 (Etc/GMT-9)

## Latest status (2026-07-16)

- Workspace moves: local repo is `/home/user/mac-repo` (branch `actool`), remote repo `/Users/runner/work/mac/mac`. 145 local tests OK (11 optional skips without lzfse).
- Xcode-26.5/CoreUI-975 dialect measured from Apple oracles: `CoreUI-975 [LAR]` + `AssetCatalogAgent-AssetRuntime` on macosx, `CoreUI-975` + `AssetCatalogSimulatorAgent` + tail `(0,2,1,2)` on iphoneos/appletvos; header stamps centralized in `src/actool_linux/coreui.py` (`CoreUIProfile`, selectable via `--coreui-profile`; legacy `coreui-918` profile = Xcode 16.4).
- macosx APPEARANCEKEYS uses AppKit names (`NSAppearanceNameSystem`, `NSAppearanceNameDarkAqua`); multilevel writer now emits APPEARANCEKEYS too.
- Packed assets (ZZZZPackedAsset/LINK): registry-independent trigger (>= 2 same-class `(appearance, alpha, gray)` candidates), GA sources pack into GA8 atlases, atlas pages keyed by attribute 8 (dimension1; macosx KEYFORMAT `(7,13,1,2,3,17,8,11,12)` vs iOS-family `(7,13,12,15,16,8,17,1,2)`), LINK tails `(1,9)(2,181)[(8,page)](12,1)[(7,appearance)](0,0)`, atlas naming `ZZZZPackedAsset-1.{opaque}.{gray}-gamut0`, aggregate renditions (identifier_override set) and non-1x/localized/idiom-bound sources never pack.
- Grayscale-representable RGB(A) sources are re-encoded to GA8 (verified for packed renditions; standalone-path inference is queued for probe6 validation).
- `assetutil --info` semantic parity (Apple consumer as judge): basic 5/5, colordata 4/4, brand 14/14, scales 7/8, probe3a 21/23, probe3b 5/6 — the only residual differences are atlas bin-packing geometry (Apple's private MaxRects-style heuristic is not replicated; documented cosmetic).
- Remaining diff_cars residuals vs Apple oracles: identifier/localization 16-bit hash (unidentified), v3-mini dmp2 grammar (partially decoded, mid-token rule open), LZFSE encoder quality, CBCK band-chunking heuristic, radiosity approximation — all catalogued in "Unfinished work".
- Remote Mac (session `EGWf17GG5atCmsgJGl5B`) went unreachable mid-session on 2026-07-16 (uptermd auth rejection); probe6 (standalone gray-RGB(A) storage, GA v3 boundary refinement, two-color v4 usage) is staged locally in `tools/make_probe6.py` and awaits a reachable host.
- Local commit: `2d814c6` (dialect + packed rules + GA normalize + facet merge + docs + probe6 suite). Push to `kagurasumusun/mac:actool` requires the Mac host (osxkeychain credentials); reconnect and run the patch flow in "Push procedure".

## Mission and clean-room boundary

Build a Linux-capable clean-room replacement for Apple `actool` and CoreUI CAR generation. Generated CARs must be accepted by Apple `assetutil` and, where tested, AppKit/UIKit/Simulator consumers. Observe public command behavior and generated data; do not copy or redistribute Apple binaries/private framework source. Keep readers bounds-checked. Never claim 100% compatibility without evidence.

Maintain reproducible evidence in `ENGINEERING_LOG.md`: commands, inputs, outputs, hashes, accepted/rejected hypotheses, and verification boundaries. Distinguish implemented, Apple `assetutil` verified, AppKit verified, UIKit Simulator verified, and experimental.

## User constraints

- Japanese responses; implementation and repeated validation are preferred over planning.
- Mac commands/tools/Simulators are approved substitutes for non-Mac physical devices.
- Never execute `exit`, `logout`, Ctrl-D, or terminate the shared tmux/Upterm shell. Detach only.
- Slow runtime boot/screenshot matrices are currently deferred at the user's request; prioritize short equivalent checks.
- Deliver a ZIP after every milestone.
- Legacy palette-img may use the public references listed by the user, but Apple code/binaries must not be copied.

## Current workspace and artifact

Local source tree: `/home/user/actool-linux`

Latest ZIP: `/home/user/actool-linux-source.zip`

The local Git repository has an old baseline and the current source is represented as working-tree changes/untracked files. Do not use local `git archive`; create ZIP from the filesystem excluding `.git`, caches, and build directories.

Current test command:

```bash
cd /home/user/actool-linux
PYTHONPATH=src python -m unittest discover -s tests
```

Latest full optional-dependency result: 89 tests, OK, no skips. lzfse 0.4.2 and cairosvg 2.9.0 were installed. Minimal environments retain explicit skips.

Capability report:

```bash
PYTHONPATH=src python -m actool_linux.cli --capabilities
```

## Current remote Mac

Upterm session (2026-07-16, went unreachable mid-session — re-run host before use): `EGWf17GG5atCmsgJGl5B`

SSH:

```bash
chmod 600 /home/user/.ssh/arena_upterm_ed25519
ssh -i /home/user/.ssh/arena_upterm_ed25519 \
  EGWf17GG5atCmsgJGl5B@uptermd.upterm.dev
```

Repository on the host: `/Users/runner/work/mac/mac` (branch `actool`, git author `actool-linux <actool-linux@users.noreply.github.com>`). Push is only possible from this host (osxkeychain GitHub credentials).

### Push procedure (established 2026-07-16)

1. Local: commit, then `find . -name __pycache__ -type d -exec rm -rf {} +` before any tarball sync (stale pyc incidents happened).
2. Sync the worktree to the host (tarball excluding `.git`, caches, `work/`), run `PYTHONPATH=src python3 -m unittest discover -s tests -q` there.
3. Host: `git add -A && git commit ... && git push origin actool`.
4. Host: `git format-patch -1 --stdout` → fetch the patch → local: `git stash` (if local has the same working-tree changes), `git am <patch>`, verify `git diff HEAD stash@{0} --stat` is empty, then `git stash drop`. Local/remote SHAs converge.

Use `/home/user/run_upterm_command.py SESSION COMMAND WAIT_SECONDS` for short commands. Use `run_upterm_interrupt.py` only for a genuinely stuck foreground process.

SCP transfers work even though SCP may return status `-1` after transferring. Verify the remote file explicitly:

```bash
scp -i /home/user/.ssh/arena_upterm_ed25519 \
  /home/user/actool-linux-source.zip \
  b8btbueUHxFMnZpY5cHt@uptermd.upterm.dev:/Users/runner/actool-linux-source.zip
```

Remote host observed:

```text
macOS 26.4
Xcode 26.5
Build 17F42
assetutil DumpToolVersion 974.1
```

The repository at `/Users/runner/work/mac/mac` on this new runner is only the upstream workflow repository (`a069646`) and does not contain actool-linux. The uploaded source was extracted at:

```text
/Users/runner/actool-current/actool-linux
```

Bare remote Python lacks optional `lzfse` and `cairosvg`; CBCK/SVG fallback tests fail there for dependency reasons. Use local Linux results or transfer already-generated CARs for Apple `assetutil` checks.

## Verified Xcode generations

`apple-consumer-matrix.json` contains 100/100 passing `assetutil` consumer rows across five SDK families (`macosx`, `iphoneos`, `appletvos`, `watchos`, `xros`) and these Xcode releases:

```text
Xcode 16.0
Xcode 16.1
Xcode 16.2
Xcode 16.3
Xcode 16.4
Xcode 26.0.1
Xcode 26.1.1
Xcode 26.2
Xcode 26.3
```

This is reader acceptance of a mixed independently generated CAR, not complete actool behavioral equivalence.

Additional focused Apple validation was performed with Xcode 26.5 for CBCK, AppIcons, vector glyphs, packed atlases, idioms, localization, appearance, SVG, layers, and complication subtype keys.

`xcode-matrix.json` is an actool build matrix with 100 rows: 60 pass, 38 build-failed, 2 build-timeout. Do not misreport this as 100/100 pass. `actool-contract.json` contains 20 Xcode installations/aliases and captured CLI contracts.

## Simulator inventory

Current new host has 12 available runtimes:

```text
iOS 26.2, 26.4.1, 26.5
tvOS 26.2, 26.4, 26.5
watchOS 26.2, 26.4, 26.5
visionOS 26.2, 26.4.1, 26.5
```

Inventory is saved in `simulator-runtime-inventory.json`.

Tool: `tools/simulator_runtime_matrix.py`. It supports inventory and optional bounded boot mode, incrementally saving JSON. A full boot pass was attempted but Simulator shutdown exceeded the 30-second cleanup timeout. The user then requested that time-consuming checks be deferred. Do not restart the all-runtime boot pass unless asked.

Runtime consumer actually verified previously:

```text
iOS 26.2 Simulator, iPhone 17 Pro, CBCK/UIKit consumer PASS
```

## Implemented and verification status

### BOM/CAR core — implemented and Apple verified

- Big-endian BOMStore parser/writer.
- CARHEADER, EXTENDED_METADATA, KEYFORMAT.
- Bounds-checked CSI/TLV parser.
- FACETKEYS, RENDITIONS, BITMAPKEYS.
- Arbitrary-depth B+ trees with internal separators, numeric BITMAPKEYS, and leaf links.
- 140-facet independent all-multilevel CAR accepted by Apple.
- 5,000-facet Apple oracle parsed.

### Images/data/colors — implemented and Apple verified

- DATA / NSDataAsset.
- JPEG, HEIF/HEIC.
- sRGB and Display P3 colors.
- PNG deepmap2 GA8, RGB, RGBA, indexed 1/2/4/8-bit, GA16, Adam7.
- Premultiplied BGRA and palette LZFSE.
- PDF preserved vector + deepmap fallbacks.
- SVG direct vector + automatic fallbacks.
- AppKit checks for JPEG/HEIF/colors/data/PDF/SVG.

### CBCK — implemented and Apple/UIKit verified

Grammar:

```text
MLEC
u32 mode=3
u32 codec=4
u32 chunkCount
repeat: KCBC, reserved0, reserved1, rowCount, compressedLength, LZFSE stream
```

Modern AppIcon part 220 and MSIS part 218 implemented. Apple reports ARGB/LZFSE. iOS 26.2 UIKit consumer passed. Complete all-Xcode adoption thresholds remain incomplete.

### AppIcons and platform idioms — implemented and assetutil verified

CoreUI idioms:

```text
universal=0 phone=1 pad=2 tv=3 car=4 watch=5 marketing=6 mac=7 vision=8
```

Modern CBCK/MSIS icon records support iOS/iPadOS, tvOS, watchOS, macOS, and visionOS plus simulator aliases. Xcode 26.5 assetutil reported the correct idiom, `Icon Image`, `MultiSized Image`, and LZFSE.

Compatibility sidecar manifests:

- 13 iOS/iPad PNGs.
- 9 watchOS PNGs.
- 10 macOS PNGs.
- tvOS/visionOS are intentionally not flattened.

### Symbols — implemented and assetutil verified

- `.symbolset` `symbols` discovery.
- Part 59, pixel format SVG, layout 1017, flags 4.
- 16-field glyph KEYFORMAT.
- TLV 1018 metrics and 1019 symbol information.
- SF template expansion for nine weights and S/M/L.
- Xcode 26.5 reports `Vector Glyph`.
- Advanced symbol effects/motion/color and complete raster atlas fallback remain partial.

### Packed atlas — implemented and assetutil verified

- TLV 1010 INLK/KLNI parser/writer.
- Exact 54-byte oracle round trip.
- Deterministic shelf packing and RGBA page composition.
- Layout 1003 empty linked records.
- Layout 1004 shared `ZZZZPackedAsset` deepmap page.
- Xcode 26.5 reports the shared page as `PackedImage` and linked entries as images.
- Xcode's exact packing heuristic/page splitting is not reproduced.

### Layered images / complications — implemented key representation, partially Apple verified

- tvOS/visionOS ordered `kCRThemeLayerName` renditions.
- visionOS depth value in `kCRThemeDimension2Name`.
- Watch family IDs in subtype and role IDs in dimension2.
- Xcode 26.5 verified basic tv/vision layer 1/2 and watch subtype 1/2 recognition.
- Latest explicit depth and semantic family/role keys are Apple `assetutil` verified: vision layer/dimension2 1/10 and 2/20; watch subtype/dimension2 4/2 and 7/3. Do not call this proprietary compositor/registry-equivalent without a private-runtime oracle.

### Thinning — implemented, policy partial

- Idiom, scale, appearance, localization selection.
- Universal/Any/unlocalized fallback retention.
- EXTENDED_METADATA thinning arguments.
- CLI single target-device integration.
- Exact device-model policy remains partial.

### CLI — partial

Accepted/integrated options include compile, platform, deployment target, app icon, launch image, partial plist, diagnostics toggles, target device, model/OS filters, product type, development region, PNG compression, and ODR switch.

Complete Apple plist output, every option combination, stdout/stderr order, and byte-identical diagnostics are not done.

## Key format discoveries

Generic base:

```text
appearance, localization, element, part, size, identifier, layer, scale
```

Modern iOS variants:

```text
appearance, localization, scale, idiom, subtype, identifier, element, part
```

AppIcon adds dimension2. Symbol format:

```text
appearance, localization, element, part, direction, identifier,
dimension1, dimension2, state, presentationState, scale,
previousState, previousValue, deploymentTarget, glyphWeight, glyphSize
```

## Unfinished work — do not claim complete

- All 12 Simulator build/install/launch/materialization matrix.
- tvOS/visionOS/watchOS equivalent runtime apps.
- SpringBoard, tvOS Home, watch Home/complication, vision Home, and macOS Dock screenshot comparisons.
- All macOS generation AppKit matrix.
- Exact tvOS Image Stack compositor aggregate record.
- Apple-internal watch family/role registry mapping.
- Apple-internal vision depth/parallax compositor metadata.
- Full CLI option cross-product and byte-identical diagnostics corpus. Sixteen focused Xcode 26.5 stdout plist contracts are byte-identical, and version plists are byte-identical for ten distinct Xcode releases from 16.0 through 26.5. See ENGINEERING_LOG.md and xcode-actool-version-matrix.json.
- Complete CBCK adoption thresholds across every Xcode.
- Historical automatic palette-img selection heuristic.
- Exact Xcode atlas pack/page heuristic (bin-packing + multi-page pagination).
- Full AppIcon metadata and every platform's deployment side effects.
- CoreUI facet/localization 16-bit identifier hash (name -> u16; sha256-prefix disproved). All hash-shaped diff_cars residuals trace to this.
- dmp2 v3-mini grammar: swatch/opcode framing decoded, mid-token encoding rule open (Xcode 26.5 uses v3-mini for uniform color sources with <= 512 raw bytes and uniform GA sources of every probed size; our writer emits valid v1/v2/v4 instead).
- GA atlas TLV1007 semantics (observed 224/224/96 does not match align16(w*bpp); we emit align16 — readable, cosmetic).
- Apple LZFSE encoder quality (their bvx2 tables out-compress ours; structure matches, sizes differ).
- CBCK band-chunk row/chunk heuristic (brand shelf 1404 vs 2435 bytes).
- Radiosity approximation (brandassets alpha-derived pseudo-kernel).
- Xcode 16.x option matrix and simulator boot matrix (deferred).
- Standalone gray-RGB(A) storage format (probe6 staged, awaiting reachable host).

## Recommended short next steps

1. Probe warning/error ordering and stderr-producing cases beyond the current 16 byte-identical Xcode 26.5 contracts.
2. Add a parser for tvOS Image Stack aggregate records from a valid Xcode oracle. The previous attempted catalog emitted no Assets.car because the nested schema was incomplete.
3. Expand the diagnostic matrix across older Xcodes and additional option cross-products; retain both raw and path-normalized hashes.
4. Build a CBCK threshold probe that uses `actool` only and dimensions around `0x155555 / rowBytes`; this is short and avoids Simulator boot.
5. For runtime work, test one representative runtime per platform first. Do not run all 12 serial boots until cleanup behavior is stable.
6. Regenerate local ZIP, test with `unzip -t`, compute SHA-256, and present it.

## Push limitation

Historical actool-linux commits on the previous runner were ahead of origin, but GitHub push failed with HTTP 403 because the Actions token lacks write permission. Required workflow permission:

```yaml
permissions:
  contents: write
```

The new runner's `/Users/runner/work/mac/mac` contains only the upstream workflow repository. The source ZIP is the authoritative transfer artifact for this session.

## Latest 12-runtime attempt

`runtime-consumer-matrix.json` is a complete first-attempt raw matrix. Four rows reached build/install/launch/screenshot (iOS 26.2/26.5 and tvOS 26.2/26.5), two launch commands timed out, watch installation exposed a missing `WKWatchOnly` key, and vision compilation exposed forbidden `UIScreen` use. Both source defects are fixed in `tools/runtime_consumer_matrix.py`; corrected watch/vision results remain unverified because the Upterm endpoint closed during the focused rerun. The tool now also gates UIKit success on the explicit `ACTOOL_RUNTIME_PASS` log marker. Do not relabel the four screenshot rows as strict materialization passes retroactively.

## Multi-entry catalog compiler

The former `entries[0]`/single-entry restriction is removed. The compiler processes every assigned slot and supports same-facet scale, idiom, appearance and locale variants. It skips legal placeholders, missing files and unsupported selectors, and deterministically retains the first duplicate slot. Local CAR parsing verifies 1x Any, 2x Any and 2x Dark keys. The writer primitives were previously Apple `assetutil` verified, but the latest integrated CAR could not be uploaded because the Upterm endpoint closed; preserve that verification boundary. `tools/option_cross_product.py` is ready to run against all installed Xcodes when a Mac endpoint is available.

## Latest local continuation

Default output is now XML like the recorded Xcode invocations; all 12 schema-2 probes remain byte-identical without an explicit output-format option. Diagnostic probing is schema 3 (18 cases), CBCK threshold probing spans all installed Xcodes and five platform families, and atlas writing supports bounded multi-page output. New schema-3 and multi-page Apple checks are pending because session `b8btbueUHxFMnZpY5cHt` now rejects its SSH identity.

## Restored Apple oracle milestone

Current session: `VtnenbVcaWmY2Jd5MyHJ`. Schema-3 diagnostics are now 18/18 byte-identical with Xcode 26.5 (22 focused exact contracts including prior preflights). Xcode 26.4.1 and 26.6 version plists are implemented and byte-identical. Integrated multi-entry and bounded two-page atlas CARs were accepted by Apple `assetutil`. The focused Xcode 26.5 iPhoneOS nine-row CBCK boundary probe selected deepmap2 for every ordinary image, rejecting a generic size-threshold hypothesis.

## All-12 runtime milestone

`runtime-consumer-matrix-verified.json` is authoritative: all iOS/tvOS/watchOS/visionOS 26.2, 26.4/26.4.1 and 26.5 rows pass build/install/launch/materialization/screenshot/cleanup. UIKit rows contain `ACTOOL_RUNTIME_PASS 64 64`; watch/vision screenshots contain the expected cyan CAR asset and are retained under `runtime-screenshots-verified/`. Modern watch packaging requires `WKApplication`, not obsolete `WKWatchKitApp`.

## Option cross-product milestone

`option-cross-26.5.json` contains 94 Xcode 26.5 cases across nine platforms. actool-linux matches 94/94 normalized plists and exit codes. Valueless diagnostic/compression switches, interspersed positional inputs, mixed existing/missing compilation-results, and incompatible tvOS/visionOS device-filter notices are implemented.

## Seven-Xcode and image-stack milestone

`option-cross-all-unique.json` covers 658 cases across Xcode 26.0.1-26.6; all contracts are accounted for after one isolated timeout retry. `.imagestack`/`.imagestacklayer` traversal is compiler-integrated and Apple tvOS assetutil verified (`image-stack-info.json`). The 63-row CBCK boundary matrix has 45 compatible deepmap2 passes; 18 Xcode 26.0/26.1 rows are runtime-build gated.

## Legacy palette scan

600 installed CARs (300 System Library, 300 Applications/Xcode resources) were inspected with Apple assetutil; none reported `palette-img`. A later legacy-reference host expanded this with 800 more installed CARs and a 448-row indexed-PNG generation matrix across Xcode 15.0–16.2, still with no Apple actool-emitted `palette-img`. However, an explicit clean-room parser/writer based on public quantized-image grammar is now implemented and Apple assetutil/consumer-verified; what remains unproven is Apple actool’s historical automatic selection heuristic. Evidence files: `palette-fixture-scan.json`, `palette-fixture-apps.json`, `palette-fixture-scan-legacy.json`, `palette-probe-legacy-matrix.json`, `paletteimg-consumer-legacy-matrix.json`.

## Private compositor oracle attempt

A controlled tvOS brand/Top-Shelf and visionOS stack oracle produced no CAR and no diagnostics under Xcode 26.5. Installed Xcode resources contain no source templates. Preserve `compositor-oracle.json` as a rejected hypothesis; do not claim private aggregate equality or invent records.

## Corrupt diagnostic milestone

Eight additional corrupt/malformed contracts are byte-identical on stdout and exit status. Corrupt PNG stderr has four dynamic Apple-agent lines; actool-linux matches the shape, not volatile timestamp/PID bytes. Apple leaves a malformed CAR; actool-linux deliberately emits a safe readable failure CAR. Focused exact stdout count: 30.

## Private layer-stack audit

CoreUI publicly observable strings confirm LayerStack/IconLayerStack/SolidLayerStack and stackData/renderingProperties builders. `layer-stack-fixtures.json` scanned 600 installed CARs and found no aggregate fixture. Exact private stackData remains fixture-gated; ordinary layers and `.imagestack` compiler integration are Apple verified.
