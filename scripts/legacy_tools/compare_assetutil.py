#!/usr/bin/env python3
"""Compare observable CAR metadata with Apple's assetutil oracle on macOS."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from actool_linux.car import CARFile  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("car", type=Path)
    ap.add_argument("--sdk", default="macosx")
    ns = ap.parse_args()
    proc = subprocess.run(
        ["xcrun", "--sdk", ns.sdk, "assetutil", "--info", str(ns.car)],
        text=True, capture_output=True,
    )
    if proc.returncode:
        print(proc.stderr, file=sys.stderr)
        return proc.returncode
    oracle = json.loads(proc.stdout)
    header = oracle[0]
    assets = oracle[1:]
    ours = CARFile.from_path(str(ns.car))
    checks = {
        "CoreUIVersion": (ours.header.core_ui_version, header.get("CoreUIVersion")),
        "StorageVersion": (ours.header.storage_version, header.get("StorageVersion")),
        "SchemaVersion": (ours.header.schema_version, header.get("SchemaVersion")),
        "MainVersion": (ours.header.main_version, header.get("MainVersion")),
        "Platform": (
            ours.extended_metadata.deployment_platform if ours.extended_metadata else None,
            header.get("Platform"),
        ),
        "PlatformVersion": (
            ours.extended_metadata.deployment_platform_version if ours.extended_metadata else None,
            header.get("PlatformVersion"),
        ),
        "Key Format": (list(ours.key_format.names), header.get("Key Format")),
        "Facet Names": (
            sorted(f.name for f in ours.facets),
            sorted({
                a.get("Name") for a in assets
                if a.get("Name") and a.get("AssetType") != "PackedImage"
            }),
        ),
        "Renditions": (
            sorted(
                (r.csi.name, r.csi.width, r.csi.height, r.csi.scale)
                for r in ours.renditions
            ),
            sorted(
                (
                    a.get("RenditionName"), a.get("PixelWidth", 0),
                    a.get("PixelHeight", 0), float(a.get("Scale", 1)),
                )
                for a in assets
            ),
        ),
    }
    def display(value):
        if isinstance(value, list) and len(value) > 12:
            return f"<{len(value)} items; first={value[:3]!r}; last={value[-3:]!r}>"
        return repr(value)

    failed = False
    for label, (actual, expected) in checks.items():
        ok = actual == expected
        print(f"{'PASS' if ok else 'FAIL'} {label}: ours={display(actual)} apple={display(expected)}")
        failed |= not ok
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
