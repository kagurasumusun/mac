#!/usr/bin/env python3
"""Extended facet hash16 pattern collection for len >= 4."""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from actool_linux.carwriter import _identifier

# Extended test cases with len >= 4
test_names = []

# len=4: systematic patterns
for c1 in 'abcdefghijklmnopqrstuvwxyz':
    for c2 in 'abcdefghijklmnopqrstuvwxyz':
        test_names.append(c1 + c2 + 'aa')
        test_names.append(c1 + c2 + 'ab')

# len=4: common words
common_4 = [
    "test", "icon", "logo", "image", "banner", "button", "label", "text",
    "menu", "item", "view", "cell", "list", "grid", "table", "form",
    "dialog", "window", "panel", "sheet", "alert", "popup", "modal",
    "header", "footer", "sidebar", "content", "main", "nav", "tab",
    "card", "tile", "badge", "chip", "tag", "pill", "dot", "line"
]
test_names.extend(common_4)

# len=5: systematic patterns
for c1 in 'abcdefghij':
    for c2 in 'abcdefghij':
        test_names.append(c1 + c2 + 'aaa')

# len=5: common words
common_5 = [
    "hello", "world", "swift", "apple", "macos", "ios", "watchos", "tvos",
    "xcode", "github", "button", "label", "image", "icon", "text",
    "alert", "sheet", "panel", "window", "dialog", "popup", "modal",
    "header", "footer", "sidebar", "content", "navigation", "toolbar"
]
test_names.extend(common_5)

# len=6-10: common words
longer_words = [
    "button", "label", "imageview", "textview", "scrollview",
    "collectionview", "tableview", "navigationbar", "toolbar",
    "tabbar", "sidebar", "splitview", "stackview", "gridview",
    "developer", "framework", "application", "document", "controller",
    "background", "foreground", "highlight", "selected", "disabled"
]
test_names.extend(longer_words)

# Remove duplicates and filter len >= 4
test_names = sorted(set(name for name in test_names if len(name) >= 4))

print(f"Collecting {len(test_names)} facet hash16 patterns for len >= 4...\n")

# Collect results
results = {}
for name in test_names:
    hash_val = _identifier(name)
    results[name] = {
        'hash': hash_val,
        'hash_hex': f"0x{hash_val:04x}",
        'length': len(name)
    }

# Group by length
from collections import defaultdict
by_length = defaultdict(list)
for name, data in results.items():
    by_length[data['length']].append((name, data['hash']))

# Print summary
print("=== Summary by Length ===\n")
for length in sorted(by_length.keys()):
    samples = by_length[length]
    hashes = [h for _, h in samples]
    print(f"Length {length}: {len(samples)} samples")
    print(f"  Min: {min(hashes):5d}, Max: {max(hashes):5d}, Range: {max(hashes) - min(hashes)}")
    
    # Show first 5 samples
    print(f"  First 5 samples:")
    for name, hash_val in sorted(samples, key=lambda x: x[1])[:5]:
        print(f"    '{name:15s}' -> {hash_val:5d} (0x{hash_val:04x})")
    print()

# Save to JSON
output_file = Path(__file__).parent.parent / 'facet_hash_patterns_extended.json'
with open(output_file, 'w') as f:
    json.dump(results, f, indent=2)

print(f"✓ Saved {len(results)} patterns to {output_file}")
print(f"✓ Collection complete")
