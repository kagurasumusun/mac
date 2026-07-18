#!/usr/bin/env python3
"""Collect facet hash16 patterns for len >= 4 names."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from actool_linux.carwriter import _identifier

# Test cases with len >= 4
test_names = [
    # len=4
    "test", "icon", "logo", "image", "banner", "button", "label",
    "Test", "Icon", "Logo", "Image", "TEST", "ICON",
    "test1", "icon1", "logo1",
    "aaaa", "bbbb", "cccc", "ABCD", "abcd",
    
    # len=5
    "hello", "world", "swift", "apple", "macos",
    "Hello", "World", "Swift", "Apple",
    "hello1", "world1",
    "aaaaa", "bbbbb", "ABCDE", "abcde",
    
    # len=6
    "github", "xcode", "ios", "watchos",
    "GitHub", "Xcode",
    "aaaaaa", "bbbbbb", "ABCDEF", "abcdef",
    
    # len=7+
    "developer", "framework", "application",
    "Developer", "Framework",
    "aaaaaaa", "bbbbbbb",
]

print("Collecting facet hash16 patterns for len >= 4:\n")

# Group by length
from collections import defaultdict
by_length = defaultdict(list)

for name in test_names:
    if len(name) >= 4:
        hash_val = _identifier(name)
        by_length[len(name)].append((name, hash_val))

# Print results
for length in sorted(by_length.keys()):
    print(f"\n=== Length {length} ===")
    for name, hash_val in sorted(by_length[length], key=lambda x: x[1]):
        print(f"  '{name:15s}' -> {hash_val:5d} (0x{hash_val:04x})")

# Analyze patterns
print("\n\n=== Pattern Analysis ===")
for length in sorted(by_length.keys()):
    hashes = [h for _, h in by_length[length]]
    print(f"\nLength {length}: {len(hashes)} samples")
    print(f"  Min: {min(hashes):5d}, Max: {max(hashes):5d}, Range: {max(hashes) - min(hashes)}")
    
    # Check for common differences
    diffs = []
    for i in range(len(hashes) - 1):
        diff = (hashes[i+1] - hashes[i]) % 65536
        diffs.append(diff)
    
    if diffs:
        from collections import Counter
        diff_counts = Counter(diffs)
        print(f"  Most common differences: {diff_counts.most_common(5)}")

print("\n✓ Collection complete")
