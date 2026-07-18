#!/usr/bin/env python3
"""Collect legacy-reference palette-related framework strings from older Xcodes."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess

files = [
    '/System/Library/PrivateFrameworks/CoreThemeDefinition.framework/CoreThemeDefinition',
    '/System/Library/PrivateFrameworks/CoreUI.framework/CoreUI',
]
for app in Path('/Applications').glob('Xcode*.app'):
    for rel in [
        'Contents/Frameworks/AssetCatalogFoundation.framework/AssetCatalogFoundation',
        'Contents/Frameworks/AssetRuntime/AssetCatalogFoundation.framework/AssetCatalogFoundation',
        'Contents/Frameworks/AssetCatalogKit.framework/AssetCatalogKit',
    ]:
        candidate = app / rel
        if candidate.exists():
            files.append(str(candidate))
terms = ['palette-img', 'palette img', 'palette', 'indexed', 'deepmap2', 'CBCK']
out: dict[str, object] = {}
for raw in files:
    path = Path(raw)
    try:
        text = subprocess.check_output(['strings', '-a', str(path)], stderr=subprocess.DEVNULL).decode('utf-8', 'replace')
    except Exception as exc:  # pragma: no cover - host specific
        out[str(path)] = {'error': str(exc)}
        continue
    hits: dict[str, list[str]] = {}
    for term in terms:
        matches: list[str] = []
        for line in text.splitlines():
            if term.lower() in line.lower():
                matches.append(line)
                if len(matches) >= 20:
                    break
        if matches:
            hits[term] = matches
    if hits:
        out[str(path)] = hits
print(json.dumps(out, indent=2))
