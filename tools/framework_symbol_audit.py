#!/usr/bin/env python3
"""Collect observable framework-string evidence for private aggregate work.

The output is a JSON map from framework binary path to a small set of matched
strings. This is intended for continuation/handoff evidence only.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess

FILES = [
    "/System/Library/PrivateFrameworks/CoreUI.framework/CoreUI",
    "/System/Library/PrivateFrameworks/CoreThemeDefinition.framework/CoreThemeDefinition",
    "/Applications/Xcode.app/Contents/Frameworks/AssetCatalogFoundation.framework/AssetCatalogFoundation",
    "/Applications/Xcode.app/Contents/Frameworks/AssetRuntime/AssetCatalogFoundation.framework/AssetCatalogFoundation",
    "/Applications/Xcode.app/Contents/Frameworks/AssetCatalogKit.framework/AssetCatalogKit",
]
TERMS = [
    "LayerStack",
    "IconLayerStack",
    "stackData",
    "renderingProperties",
    "Top Shelf",
    "parallax",
    "complication",
    "PackedImage",
    "CBCK",
]


def main() -> int:
    out: dict[str, object] = {}
    for raw_path in FILES:
        path = Path(raw_path)
        if not path.exists():
            out[raw_path] = {"present": False}
            continue
        try:
            text = subprocess.check_output(["strings", "-a", raw_path], stderr=subprocess.DEVNULL).decode("utf-8", "replace")
        except Exception as exc:  # pragma: no cover - host/environment specific
            out[raw_path] = {"present": True, "error": str(exc)}
            continue
        hits: dict[str, list[str]] = {}
        lines = text.splitlines()
        for term in TERMS:
            matches: list[str] = []
            for line in lines:
                if term.lower() in line.lower():
                    matches.append(line)
                    if len(matches) >= 12:
                        break
            if matches:
                hits[term] = matches
        out[raw_path] = {"present": True, "hits": hits}
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
