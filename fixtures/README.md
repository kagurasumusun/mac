# fixtures

Self-made CAR fixtures only. Every file here is compiled from inputs authored by
this project (generated PNGs/colors/metadata) — no Apple- or third-party-
copyrighted artwork.

| Entry | Compiled by | Source inputs | Purpose |
|---|---|---|---|
| `brandassets-target-tv-Assets.car` | Apple `actool` (Xcode 26.5) on this project's clean-room `.brandassets` catalog | `tools/make_*_suite.py`-family generators | tvOS brandassets layout-1002 oracle (self-authored artwork) |
| `selfgen-rich-Assets.car` | Apple `actool` on GitHub-hosted macOS runner | `tools/make_public_fixtures.py` (self-authored appearance colors, @1x/@2x/@3x images, data asset, app icon) | appearance-registry + broad rendition coverage (replaces the removed third-party-app fixture role) |
| `selfgen-stacks-Assets.car` | Apple `actool` on GitHub-hosted macOS runner | `tools/make_public_fixtures.py` (self-authored imagestack layers) | imagestack (layout 1002) layer metadata |
| `selfgen-solidstack-demo.car` | `actool-linux` (this repo), validated by Apple `assetutil` on the runner | `tools/make_public_fixtures.py --emit-solidstack-demo` | self-authored SolidImageStack (layout 1018) stack TLV demo |
| `selfgen-vec-Assets.car` | Apple `actool` on GitHub-hosted macOS runner | `tools/make_public_fixtures.py` | special payloads: PDF vector (preserve-vector), 16-bit GA/gray PNGs, self-rendered JPEG, high-contrast color, translucent P3 color, typed datasets |
| `selfgen-ios-Assets.car` | Apple `actool` on GitHub-hosted macOS runner | `tools/make_public_fixtures.py` | iphone/ipad idioms ×1x/2x/3x, dark appearance variants, `ja` localization (Loc8), light/dark Display-P3 colors |

## Removal log (2026-07-17)

- `firefox-Assets.car` (extracted from Mozilla Firefox.app) — removed for
  license hygiene. The investigative value (appearance registry, layout-1019
  IconImageStack statistics) is preserved as *metadata-only* scans in
  `../research/iconstack-*.json` and re-created self-authored equivalents above.
- `filemerge-Assets.car` (extracted from Apple FileMerge.app) — removed for
  license hygiene; same replacement story.

Historical engineering notes that mention the removed fixtures remain in
`../ENGINEERING_LOG.md` / `../docs/` as dated records; the binary payloads are
no longer distributed.
