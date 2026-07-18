#!/usr/bin/env python3
"""Scan Apple AssetRuntime / Xcode binaries for aggregate-related observable strings.

This is a clean-room helper: it reports only matched filenames and optionally
matched printable lines from `strings`, without copying binary contents.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', action='append', default=[],
                    help='Root directory to scan (repeatable).')
    ap.add_argument('--term', action='append', default=[],
                    help='Case-insensitive raw-byte term to search for (repeatable).')
    ap.add_argument('--context-strings', action='store_true',
                    help='Also run `strings -a` on matched files and capture lines containing the terms.')
    ap.add_argument('--size-limit', type=int, default=50_000_000,
                    help='Skip files larger than this many bytes (default: 50MB).')
    ap.add_argument('--output', type=Path, default=Path('assetruntime-string-probe.json'))
    return ap.parse_args()


def main() -> int:
    ns = parse_args()
    roots = [Path(p) for p in ns.root] or [
        Path('/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/System/AssetRuntime/System/Library/PrivateFrameworks'),
        Path('/Applications/Xcode.app/Contents/Frameworks'),
    ]
    raw_terms = [t.encode('utf-8') for t in ns.term] or [
        b'renderingProperties',
        b'stackData',
        b'parallaxImages',
        b'parallaxLayerDepths',
        b'maximumParallaxDepth',
        b'maximumParallaxImages',
        b'brandassets',
        b'TopShelf',
    ]
    results: dict[str, dict[str, object]] = {
        term.decode('utf-8', 'replace'): {'count': 0, 'files': []}
        for term in raw_terms
    }
    visited = 0
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob('*'):
            try:
                if not path.is_file() or path.is_symlink():
                    continue
                st = path.stat()
                if st.st_size > ns.size_limit:
                    continue
                visited += 1
                data = path.read_bytes().lower()
            except Exception:
                continue
            for raw_term in raw_terms:
                key = raw_term.decode('utf-8', 'replace')
                if raw_term.lower() not in data:
                    continue
                item = results[key]
                item['count'] = int(item['count']) + 1
                entry: dict[str, object] = {'path': str(path), 'size': len(data)}
                if ns.context_strings:
                    try:
                        text = subprocess.run(['strings', '-a', str(path)], capture_output=True, text=True, timeout=20).stdout
                        lines = [line for line in text.splitlines() if raw_term.decode('utf-8', 'replace').lower() in line.lower()]
                        if lines:
                            entry['strings'] = lines[:20]
                    except Exception as exc:
                        entry['strings_error'] = str(exc)
                cast_files = item['files']
                assert isinstance(cast_files, list)
                cast_files.append(entry)
    payload = {
        'schema': 1,
        'roots': [str(p) for p in roots],
        'terms': [t.decode('utf-8', 'replace') for t in raw_terms],
        'visited_files': visited,
        'results': results,
    }
    ns.output.write_text(json.dumps(payload, indent=2) + '\n')
    print(json.dumps({'visited_files': visited, 'output': str(ns.output)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
