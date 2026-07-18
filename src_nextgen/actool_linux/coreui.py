"""CoreUI dialect profiles and version-dependent constants.

Every CoreUI-version-sensitive value the writer emits is centralized here so
tracking a future CoreUI/Xcode release means editing one table, not hunting
through the writers. All values derive from observable Apple output bytes
(CAR files and assetutil dumps produced by Xcode 16.4 / 26.5 oracles on
independently created input catalogs). No Apple code or binaries are copied.

Profile history observed so far:

===================  =====================  ============  ================
oracle               CARHEADER              program tag   trailing u32x4
===================  =====================  ============  ================
Xcode 16.4 (macOS15) ``918, 17, 0, n``       ``918.5``     ``0, 5, 1, 1``
Xcode 26.5 macosx    ``975, 17, 0, n``       ``975 [LAR]`` ``0, 2, 1, 1``
Xcode 26.5 ios/tvos  ``975, 17, 0, n``       ``975``       ``0, 2, 1, 2``
===================  =====================  ============  ================

Apple also stamps a provenance comment ``Xcode 26.5 (17F42) via
AssetCatalogAgent-AssetRuntime`` (macosx) resp. ``...SimulatorAgent``
(ios/tvos). This implementation writes its own provenance string instead;
the profile only records the *observed* agent token because the last header
word correlates with it (1 = AssetRuntime, 2 = Simulator agent).
"""
from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# dmp2 image grammar versions (first byte after the "dmp2" fourcc).
# ---------------------------------------------------------------------------
DMP2_RAW = 1       # raw premultiplied bytes (legacy, always accepted)
DMP2_LZFSE = 2     # premultiplied BGRA, one LZFSE stream
DMP2_MINI = 3      # tiny uniform-image "mini" grammar (observed; writer TBD)
DMP2_PALETTE = 4   # swatch table + 8-bit index plane (LZFSE)

# dmp2 trailing header fields observed constant across grammars: (1, 10, bpp)
DMP2_FIELD1 = 1
DMP2_FIELD2 = 10

# ---------------------------------------------------------------------------
# MLEC payload wrapper.
# ---------------------------------------------------------------------------
MLEC_CODEC_DMP2 = 11        # payload embeds a dmp2 stream
MLEC_CODEC_LZFSE_CHUNKS = 4  # KCBC chunks of raw LZFSE (CBCK bitmap)
MLEC_MODE_DEFAULT = 0
MLEC_MODE_OPAQUE_UNIFORM = 2  # uniform + fully opaque deepmaps
MLEC_MODE_CHUNKED = 3

# ---------------------------------------------------------------------------
# CSI rendition layouts (u16 at CSI offset 36).
# ---------------------------------------------------------------------------
LAYOUT_DEEPMAP = 12          # ordinary pixel-mapped image
LAYOUT_IMAGE_STACK = 1002    # tvOS layered image stack aggregate
LAYOUT_LINK = 1003           # packed-asset reference into an atlas
LAYOUT_ATLAS = 1004          # ZZZZPackedAsset atlas image

# ---------------------------------------------------------------------------
# CSI TLV tags (u32 tag + u32 byte length, value padded to the stated size).
# ---------------------------------------------------------------------------
TLV_GEOMETRY = 1001          # 20 bytes: (1, 0, 0, w, h) / atlas (1,0,0,0,0)
TLV_SLICE = 1003             # 28 bytes slice information
TLV_OPACITY = 1004           # 8 bytes, observed 00 00 00 00 00 00 80 3f
TLV_FLAGS = 1006             # 4 bytes, observed 1
TLV_ROW_BYTES = 1007         # 4 bytes (image width*bpp; atlas 16-aligned)
TLV_LINK = 1010              # packed-asset rectangle + atlas key
TLV_STACK_INFO = 1012        # image-stack aggregate data (see imagestack.py)
TLV_STACK_CANVAS = 1020      # image-stack canvas
TLV_STACK_FLAGS = 1021       # image-stack per-layer flags

# Maximum colors representable by the v4 palette grammar: 8-bit index plane
# gives 256 swatches, swatch 0 reserved for transparent padding.
DMP2_PALETTE_MAX_COLORS = 255

DEFAULT_COREUI_PROFILE_NAME = "coreui-975"


@dataclass(frozen=True)
class CoreUIProfile:
    """One observed CoreUI output dialect."""

    name: str
    header_version: int                 # first u32 after the RATC magic
    header_field2: int                  # second u32 (17 in every oracle)
    project_tag: str                    # embedded in the program string
    header_tail: tuple[int, int, int, int]
    apple_agent_token: str              # observed provenance agent (reference)

    @property
    def program_string(self) -> str:
        return f"@(#)PROGRAM:CoreUI  PROJECT:CoreUI-{self.project_tag}\n"

    # Our own provenance; deliberately NOT a copy of Apple's string.
    @property
    def writer_comment(self) -> str:
        return "actool-linux clean-room writer"


COREUI_918 = CoreUIProfile(
    name="coreui-918",
    header_version=918,
    header_field2=17,
    project_tag="918.5",
    header_tail=(0, 5, 1, 1),
    apple_agent_token="AssetCatalogSimulatorAgent",  # Xcode 16.4 era oracles
)

COREUI_400 = CoreUIProfile(
    name="coreui-400",
    header_version=400,
    header_field2=14,
    project_tag="400",
    header_tail=(0, 0, 1, 1),
    apple_agent_token="AssetCatalogSimulatorAgent",
)

COREUI_450 = CoreUIProfile(
    name="coreui-450",
    header_version=450,
    header_field2=15,
    project_tag="450",
    header_tail=(0, 0, 1, 1),
    apple_agent_token="AssetCatalogSimulatorAgent",
)

COREUI_498 = CoreUIProfile(
    name="coreui-498",
    header_version=498,
    header_field2=15,
    project_tag="498",
    header_tail=(0, 0, 1, 1),
    apple_agent_token="AssetCatalogSimulatorAgent",
)

COREUI_700 = CoreUIProfile(
    name="coreui-700",
    header_version=700,
    header_field2=16,
    project_tag="700",
    header_tail=(0, 1, 1, 1),
    apple_agent_token="AssetCatalogSimulatorAgent",
)

COREUI_800 = CoreUIProfile(
    name="coreui-800",
    header_version=800,
    header_field2=16,
    project_tag="800",
    header_tail=(0, 3, 1, 1),
    apple_agent_token="AssetCatalogSimulatorAgent",
)

COREUI_850 = CoreUIProfile(
    name="coreui-850",
    header_version=850,
    header_field2=16,
    project_tag="850",
    header_tail=(0, 4, 1, 1),
    apple_agent_token="AssetCatalogSimulatorAgent",
)

COREUI_918_MACOS = CoreUIProfile(
    name="coreui-918-macos",
    header_version=918,
    header_field2=17,
    project_tag="918.5",
    header_tail=(0, 5, 1, 1),
    apple_agent_token="AssetCatalogAgent-AssetRuntime",
)

COREUI_918_DEVICE = CoreUIProfile(
    name="coreui-918-device",
    header_version=918,
    header_field2=17,
    project_tag="918.5",
    header_tail=(0, 5, 1, 2),
    apple_agent_token="AssetCatalogSimulatorAgent",
)

COREUI_975_MACOS = CoreUIProfile(
    name="coreui-975-macos",
    header_version=975,
    header_field2=17,
    project_tag="975 [LAR]",
    header_tail=(0, 2, 1, 1),
    apple_agent_token="AssetCatalogAgent-AssetRuntime",  # (verified oracles)
)

COREUI_975_DEVICE = CoreUIProfile(
    name="coreui-975-device",
    header_version=975,
    header_field2=17,
    project_tag="975",
    header_tail=(0, 2, 1, 2),
    apple_agent_token="AssetCatalogSimulatorAgent",  # (verified oracles)
)

PROFILE_ALIASES = {
    DEFAULT_COREUI_PROFILE_NAME: "coreui-975-device",
    "coreui-975": "coreui-975-device",
}

MACOS_HEADER_PLATFORMS = frozenset({"macosx"})


def profile_for_platform(platform: str | None) -> CoreUIProfile:
    """Observed per-platform header dialect for the current CoreUI (975)."""
    if (platform or "macosx").lower() in MACOS_HEADER_PLATFORMS:
        return COREUI_975_MACOS
    return COREUI_975_DEVICE


def auto_select_profile(platform: str | None, target: str | float | None = None) -> CoreUIProfile:
    """Select the historical or current CoreUI profile based on deployment target and platform."""
    plat = (platform or "macosx").lower()
    is_mac = plat in MACOS_HEADER_PLATFORMS
    if target is None:
        return COREUI_975_MACOS if is_mac else COREUI_975_DEVICE
    try:
        ver = float(str(target).split(".")[0])
    except (ValueError, TypeError):
        return COREUI_975_MACOS if is_mac else COREUI_975_DEVICE
    if is_mac:
        if ver <= 11.0:
            return COREUI_700
        if ver <= 13.0:
            return COREUI_850
        if ver <= 15.0:
            return COREUI_918_MACOS
        return COREUI_975_MACOS
    else:
        if ver <= 13.0:
            return COREUI_700
        if ver <= 15.0:
            return COREUI_850
        if ver <= 16.0:
            return COREUI_918_DEVICE
        return COREUI_975_DEVICE


def resolve_profile(profile: "CoreUIProfile | str | None", platform: str | None) -> CoreUIProfile:
    """Normalize a user-supplied profile choice.

    ``None`` selects the current dialect for ``platform``; a string looks up
    :data:`PROFILES` (aliases allowed); a profile instance passes through.
    """
    if profile is None:
        return profile_for_platform(platform)
    if isinstance(profile, CoreUIProfile):
        return profile
    name = PROFILE_ALIASES.get(profile, profile)
    try:
        return PROFILES[name]
    except KeyError:
        raise ValueError(
            f"unknown CoreUI profile {profile!r}; known: {sorted(PROFILES)} "
            f"or aliases {sorted(PROFILE_ALIASES)}"
        ) from None


# Additional legacy profiles based on MacOSX SDK analysis
COREUI_420 = CoreUIProfile(
    name="coreui-420",
    header_version=420,
    header_field2=14,
    project_tag="420",
    header_tail=(0, 0, 1, 1),
    apple_agent_token="AssetCatalogSimulatorAgent",
)

COREUI_480 = CoreUIProfile(
    name="coreui-480",
    header_version=480,
    header_field2=15,
    project_tag="480",
    header_tail=(0, 0, 1, 1),
    apple_agent_token="AssetCatalogSimulatorAgent",
)

COREUI_580 = CoreUIProfile(
    name="coreui-580",
    header_version=580,
    header_field2=15,
    project_tag="580",
    header_tail=(0, 0, 1, 1),
    apple_agent_token="AssetCatalogSimulatorAgent",
)

COREUI_680 = CoreUIProfile(
    name="coreui-680",
    header_version=680,
    header_field2=16,
    project_tag="680",
    header_tail=(0, 0, 1, 1),
    apple_agent_token="AssetCatalogSimulatorAgent",
)


PROFILES: dict[str, CoreUIProfile] = {
    p.name: p for p in (
        COREUI_400, COREUI_420, COREUI_450, COREUI_480, COREUI_498,
        COREUI_580, COREUI_680, COREUI_700, COREUI_800, COREUI_850,
        COREUI_918, COREUI_918_MACOS, COREUI_918_DEVICE,
        COREUI_975_MACOS, COREUI_975_DEVICE,
    )
}
