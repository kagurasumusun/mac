"""Machine-readable implementation and Apple-verification boundary."""
from __future__ import annotations

CAPABILITIES = {
    "container": {"implemented": True, "apple_assetutil": True, "generations": "CoreUI storage 15-17; Xcode 10-era readers through Xcode 26.5 observed"},
    "images": {"implemented": True, "apple_assetutil": True, "appkit": True, "formats": ["PNG/deepmap2", "CBCK/LZFSE", "JPEG", "HEIF", "PDF", "SVG"]},
    "symbols": {"implemented": True, "apple_assetutil": True, "scope": "part-59 vectors, 9 weights, S/M/L; advanced effects partial"},
    "packed_atlas": {"implemented": True, "apple_assetutil": True, "scope": "INLK links and deterministic bounded multi-page shelf packer Apple-accepted; exact Xcode split/order heuristic not byte-identical"},
    "app_icons": {"implemented": True, "apple_assetutil": True, "platforms": ["iOS", "iPadOS", "tvOS", "watchOS", "macOS", "visionOS"]},
    "layered_icons": {"implemented": True, "apple_assetutil": True, "scope": "tvOS/visionOS .imagestack/.imagestacklayer plus .solidimagestack/.solidimagestacklayer source traversal; decoded aggregate TLVs 1012/1020/1021 for public solid-image-stack oracles; decoded public tvOS brandassets target-device-tv layout-1002 ImageStack fixture and real layout-1019 IconImageStack / 1020 IconGroup / 1021 Named Gradient fixtures; proprietary compositor aggregate writing remains partial"},
    "watch_complications": {"implemented": True, "apple_assetutil": True, "scope": "12 family IDs and 5 role IDs in subtype/dimension2 keys"},
    "thinning": {"implemented": True, "apple_assetutil": True, "scope": "writer-side deterministic selector; exact actool device-model policy partial"},
    "simulator_consumers": {"implemented": True, "verified": ["all 12 installed iOS/tvOS/watchOS/visionOS 26.2/26.4/26.5 runtimes: build, install, launch, materialization, screenshot"], "remaining": "Home/SpringBoard compositor comparison is separate"},
    "diagnostics": {"implemented": False, "scope": "22 focused byte-identical contracts; 658/658 option/platform contracts across seven Xcode 26 releases after one transient retry; broader malformed corpus incomplete"},
    "cbck_threshold_matrix": {"implemented": True, "scope": "45/45 compatible iPhoneOS ordinary-image boundary builds across Xcode 26.2-26.6 selected deepmap2; Xcode 26.0/26.1 blocked by unavailable matching runtime; role-specific matrix incomplete"},
    "springboard_dock_comparison": {"implemented": False, "scope": "not yet completed across platforms"},
    "legacy_palette_img": {"implemented": True, "apple_assetutil": True, "scope": "explicit indexed-PNG palette-img writer and parser implemented from public quantized-image grammar; automatic historical actool selection across old toolchains remains partial"},
}


def capability_report() -> dict[str, object]:
    return {"tool": "actool-linux", "claims": CAPABILITIES,
            "verified_hosts": ["macOS 15.7.7 / Xcode 16.4 / CoreUI 918.5", "macOS 26.4 / Xcode 26.5 / assetutil 974.1"]}
