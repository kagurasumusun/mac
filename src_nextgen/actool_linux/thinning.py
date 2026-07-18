"""Deterministic CoreUI rendition thinning.

The selector operates on the clean-room intermediate representation, before BOM
indexes are emitted.  It deliberately retains universal/Any/unlocalized
fallbacks unless ``keep_fallbacks`` is disabled.
"""
from __future__ import annotations

from dataclasses import dataclass

from .carwriter import AssetRendition

IDIOMS = {
    "universal": 0, "iphone": 1, "phone": 1, "ipad": 2, "pad": 2,
    "tv": 3, "car": 4, "carplay": 4, "watch": 5, "marketing": 6,
    "mac": 7, "vision": 8, "visionos": 8,
}


@dataclass(frozen=True)
class ThinningOptions:
    idiom: str | int | None = None
    scale: int | None = None
    appearance: int | None = None
    localization: str | None = None
    keep_fallbacks: bool = True

    def idiom_id(self) -> int | None:
        if self.idiom is None:
            return None
        try:
            value = IDIOMS[self.idiom] if isinstance(self.idiom, str) else int(self.idiom)
        except (KeyError, ValueError) as exc:
            raise ValueError(f"unsupported thinning idiom: {self.idiom}") from exc
        if value not in range(9):
            raise ValueError(f"unsupported thinning idiom: {self.idiom}")
        return value

    def metadata_arguments(self) -> str:
        fields: list[str] = []
        idiom_id = self.idiom_id()
        if idiom_id is not None:
            fields += ["idiom", str(idiom_id)]
        if self.scale is not None:
            fields += ["scale", str(self.scale)]
        if self.appearance is not None:
            fields += ["appearance", str(self.appearance)]
        if self.localization is not None:
            fields += ["localization", self.localization]
        return " ".join(fields)


def thin_renditions(assets: list[AssetRendition], options: ThinningOptions) -> list[AssetRendition]:
    """Select device-compatible renditions while preserving fallback records.

    Vector payloads (part 42) and auxiliary records sharing the selected idiom
    are retained. Ordering is unchanged; ``build_assets_car`` performs its own
    canonical sort.
    """
    idiom = options.idiom_id()
    if options.scale is not None and options.scale not in (1, 2, 3):
        raise ValueError("thinning scale must be 1, 2, or 3")
    if options.appearance is not None and options.appearance not in (0, 1, 2):
        raise ValueError("unsupported thinning appearance")

    selected: list[AssetRendition] = []
    for asset in assets:
        if idiom is not None:
            allowed = {idiom}
            if options.keep_fallbacks:
                allowed.add(0)
            # Marketing (App Store) content is device-independent: Apple
            # retains idiom 6 renditions under --target-device thinning.
            allowed.add(6)
            if asset.idiom not in allowed:
                continue
        if options.scale is not None and asset.part != 42 and asset.scale != options.scale:
            continue
        if options.appearance is not None:
            allowed_appearances = {options.appearance}
            if options.keep_fallbacks:
                allowed_appearances.add(0)
            if asset.appearance not in allowed_appearances:
                continue
        if options.localization is not None:
            allowed_locales = {options.localization}
            if options.keep_fallbacks:
                allowed_locales.add(None)  # type: ignore
            if asset.localization not in allowed_locales:
                continue
        selected.append(asset)
    return selected
