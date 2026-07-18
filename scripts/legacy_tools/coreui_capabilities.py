#!/usr/bin/env python3
"""Record observable CoreUI codec capability strings without copying binaries."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

PATTERN = re.compile(
    r"palette-img|palette.?image|deepmap2|CBCK|LZFSE|allowsPaletteImageCompression|"
    r"allowsDeepmap2ImageCompression|compressionType",
    re.IGNORECASE,
)


def inspect(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    result = subprocess.run(["strings", "-a", str(path)], capture_output=True, text=True, check=True)
    matches = sorted({line for line in result.stdout.splitlines() if PATTERN.search(line)})
    return {
        "path": str(path),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "matches": matches,
        "legacy_palette_decoder_evidence": "palette-img" in matches,
        "legacy_palette_switch_evidence": any("allowsPaletteImageCompression" in item for item in matches),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("binaries", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = {"schema": 1, "binaries": [inspect(path) for path in args.binaries]}
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
