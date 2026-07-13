"""Deterministic compatibility AppIcon sidecar manifests and source ranking."""
from __future__ import annotations

# These are compatibility PNGs used by older bundle consumers. Modern tvOS
# and visionOS layered icons remain in Assets.car and intentionally have no
# flattened sidecar in this table.
_IOS = (
 ("AppIcon20x20@2x.png",40),("AppIcon20x20@3x.png",60),
 ("AppIcon29x29@2x.png",58),("AppIcon29x29@3x.png",87),
 ("AppIcon40x40@2x.png",80),("AppIcon40x40@3x.png",120),
 ("AppIcon60x60@2x.png",120),("AppIcon60x60@3x.png",180),
 ("AppIcon20x20@2x~ipad.png",40),("AppIcon29x29@2x~ipad.png",58),
 ("AppIcon40x40@2x~ipad.png",80),("AppIcon76x76@2x~ipad.png",152),
 ("AppIcon83.5x83.5@2x~ipad.png",167),
)
_WATCH = (
 ("AppIcon24x24@2x~watch.png",48),("AppIcon27.5x27.5@2x~watch.png",55),
 ("AppIcon29x29@2x~watch.png",58),("AppIcon40x40@2x~watch.png",80),
 ("AppIcon44x44@2x~watch.png",88),("AppIcon50x50@2x~watch.png",100),
 ("AppIcon86x86@2x~watch.png",172),("AppIcon98x98@2x~watch.png",196),
 ("AppIcon108x108@2x~watch.png",216),
)
_MAC = (
 ("AppIcon16x16.png",16),("AppIcon16x16@2x.png",32),
 ("AppIcon32x32.png",32),("AppIcon32x32@2x.png",64),
 ("AppIcon128x128.png",128),("AppIcon128x128@2x.png",256),
 ("AppIcon256x256.png",256),("AppIcon256x256@2x.png",512),
 ("AppIcon512x512.png",512),("AppIcon512x512@2x.png",1024),
)

_PLATFORM_ALIASES = {
    "iphoneos": "ios", "iphonesimulator": "ios", "ios": "ios",
    "appletvos": "tvos", "appletvsimulator": "tvos", "tvos": "tvos",
    "watchos": "watchos", "watchsimulator": "watchos",
    "macosx": "macos", "macos": "macos",
    "xros": "visionos", "xrsimulator": "visionos", "visionos": "visionos",
}

_PLATFORM_ENTRY_FIELDS = {
    "ios": {"ios"},
    "tvos": {"tvos", "appletvos"},
    "watchos": {"watchos"},
    "macos": {"macos", "macosx"},
    "visionos": {"visionos", "xros"},
}

_PLATFORM_ENTRY_IDIOMS = {
    "ios": {"universal", "iphone", "ipad", "ios-marketing", "marketing"},
    "tvos": {"universal", "tv", "tv-marketing", "marketing"},
    "watchos": {"universal", "watch", "watch-marketing", "marketing"},
    "macos": {"universal", "mac", "mac-marketing", "marketing"},
    "visionos": {"universal", "vision", "visionos", "vision-marketing", "marketing"},
}

_PLATFORM_PREFERRED_IDIOMS = {
    "ios": ("ios-marketing", "marketing", "iphone", "ipad", "universal"),
    "tvos": ("tv-marketing", "marketing", "tv", "universal"),
    "watchos": ("watch-marketing", "marketing", "watch", "universal"),
    "macos": ("mac-marketing", "marketing", "mac", "universal"),
    "visionos": ("vision-marketing", "marketing", "vision", "visionos", "universal"),
}


def _canonical_platform(platform: str) -> str:
    try:
        return _PLATFORM_ALIASES[platform.lower()]
    except KeyError as exc:
        raise ValueError(f"unsupported AppIcon platform: {platform}") from exc



def app_icon_entry_rank(entry: dict[str, object], platform: str) -> int | None:
    """Return a deterministic preference rank for one AppIcon Contents.json entry.

    ``None`` means the slot does not apply to the requested platform at all.
    Higher scores are preferred. Platform-tagged marketing slots rank above
    plain generic/universal slots so mixed multi-platform icon sets choose the
    expected source before falling back to area-based tie-breaking.

    Observable Xcode behavior also shows that watch-marketing slots in the
    compiler path are accepted syntactically but do not materialize Assets.car
    or sidecar output for the tested watchOS cases, so they are treated as
    non-applicable here.
    """
    canonical = _canonical_platform(platform)
    entry_platform = str(entry.get("platform", "")).strip().lower()
    entry_idiom = str(entry.get("idiom", "")).strip().lower()

    if entry_platform and entry_platform not in _PLATFORM_ENTRY_FIELDS[canonical]:
        return None
    if entry_idiom and entry_idiom not in _PLATFORM_ENTRY_IDIOMS[canonical]:
        return None
    if canonical == "watchos" and entry_idiom == "watch-marketing":
        return None

    score = 0
    if entry_platform:
        score += 100
    if entry_idiom:
        preferred = _PLATFORM_PREFERRED_IDIOMS[canonical]
        score += 50 - preferred.index(entry_idiom) if entry_idiom in preferred else 0
    return score



def app_icon_sidecar_specs(platform: str) -> tuple[tuple[str,int,int],...]:
    key = _canonical_platform(platform)
    source = _IOS if key == "ios" else _WATCH if key == "watchos" else _MAC if key == "macos" else ()
    return tuple((name,size,size) for name,size in source)
