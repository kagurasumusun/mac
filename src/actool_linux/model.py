from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json


@dataclass(frozen=True)
class Diagnostic:
    severity: str
    message: str
    path: Path | None = None
    failure_reason: str | None = None

    def render(self) -> str:
        prefix = f"{self.path}: " if self.path else ""
        return f"{prefix}{self.severity}: {self.message}"


@dataclass
class Asset:
    catalog: Path
    directory: Path
    kind: str
    name: str
    properties: dict[str, Any]
    entries: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Catalog:
    path: Path
    assets: list[Asset]
    diagnostics: list[Diagnostic]


KNOWN_SUFFIXES = {
    ".appiconset": "app-icon",
    ".imageset": "image",
    ".colorset": "color",
    ".symbolset": "symbol",
    ".launchimage": "launch-image",
    ".brandassets": "brand-assets",
    ".dataset": "data",
    ".imagestack": "image-stack",
    ".imagestacklayer": "image-stack-layer",
    ".stickerpack": "sticker-pack",
}


def load_catalog(path: Path) -> Catalog:
    diagnostics: list[Diagnostic] = []
    assets: list[Asset] = []
    if not path.is_dir():
        return Catalog(path, [], [Diagnostic("error", "input is not an asset catalog directory", path)])
    if path.suffix != ".xcassets":
        diagnostics.append(Diagnostic("warning", "asset catalog does not use the .xcassets extension", path))

    for contents in sorted(path.rglob("Contents.json")):
        directory = contents.parent
        if directory == path:
            continue
        kind = KNOWN_SUFFIXES.get(directory.suffix)
        if kind is None:
            continue
        try:
            raw = json.loads(contents.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            diagnostics.append(Diagnostic("error", f"cannot read Contents.json: {exc}", contents))
            continue
        if not isinstance(raw, dict):
            diagnostics.append(Diagnostic("error", "Contents.json root must be an object", contents))
            continue
        info = raw.get("info")
        if not isinstance(info, dict) or "version" not in info or "author" not in info:
            diagnostics.append(Diagnostic("warning", "Contents.json has no complete info dictionary", contents))
        entries_key = {"color": "colors", "data": "data", "symbol": "symbols", "image-stack": "layers", "brand-assets": "assets"}.get(kind, "images")
        entries = raw.get(entries_key, [])
        if not isinstance(entries, list):
            diagnostics.append(Diagnostic("error", f"'{entries_key}' must be an array", contents))
            entries = []
        valid_entries = []
        for entry in entries:
            if not isinstance(entry, dict):
                diagnostics.append(Diagnostic("error", f"'{entries_key}' contains a non-object entry", contents))
                continue
            valid_entries.append(entry)
            filename = entry.get("filename")
            if isinstance(filename, str) and not (directory / filename).exists():
                diagnostics.append(Diagnostic("warning", f"referenced file is missing: {filename}", contents))
        assets.append(Asset(path, directory, kind, directory.stem, raw, valid_entries))
    return Catalog(path, assets, diagnostics)
