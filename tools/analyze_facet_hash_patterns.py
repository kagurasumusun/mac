#!/usr/bin/env python3
"""Analyze collected facet hash16 patterns to deduce the final mixing function."""

import json
from pathlib import Path
from collections import defaultdict
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from actool_linux.carwriter import _identifier

# Load collected patterns
patterns_file = Path(__file__).parent.parent / 'facet_hash_patterns_extended.json'
with open(patterns_file) as f:
    patterns = json.load(f)

print(f"Loaded {len(patterns)} patterns\n")

# Group by length
by_length = defaultdict(list)
for name, data in patterns.items():
    by_length[data['length']].append((name, data['hash']))

# Analyze patterns for each length
print("=== Pattern Analysis by Length ===\n")

for length in sorted(by_length.keys()):
    samples = by_length[length]
    if len(samples) < 10:
        continue
    
    print(f"Length {length}: {len(samples)} samples")
    
    # Calculate hash differences for consecutive characters
    char_diffs = defaultdict(list)
    for name, hash_val in samples:
        for i in range(len(name) - 1):
            c1, c2 = name[i], name[i+1]
            if c1 != c2:
                # Find a similar name with c1 and c2 swapped
                swapped = name[:i] + c2 + c1 + name[i+2:]
                if swapped in patterns:
                    diff = (patterns[swapped]['hash'] - hash_val) % 65536
                    char_diffs[(c1, c2, i)].append(diff)
    
    # Show most common differences
    if char_diffs:
        print(f"  Character swap differences (first 10):")
        for (c1, c2, pos), diffs in sorted(char_diffs.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
            if len(diffs) > 1:
                avg_diff = sum(diffs) / len(diffs)
                print(f"    '{c1}'<->'{c2}' at pos {pos}: {len(diffs)} samples, avg diff={avg_diff:.1f}")
    
    # Analyze hash distribution
    hashes = [h for _, h in samples]
    print(f"  Hash distribution:")
    print(f"    Min: {min(hashes)}, Max: {max(hashes)}, Range: {max(hashes) - min(hashes)}")
    print(f"    Mean: {sum(hashes)/len(hashes):.1f}, StdDev: {(sum((h - sum(hashes)/len(hashes))**2 for h in hashes) / len(hashes))**0.5:.1f}")
    print()

# Try to deduce the mixing function
print("\n=== Attempting to Deduce Final Mixing Function ===\n")

# Hypothesis: The hash is computed as:
# 1. Polynomial hash: h = sum(c[i] * 33^(n-1-i+3)) mod 2^32
# 2. Final mixing: h = mix(h) mod 2^16

# Test different mixing functions
def test_mixing_function(name, hash_val, mix_func):
    """Test if a mixing function produces the expected hash."""
    # Compute polynomial hash
    poly_hash = 0
    for i, c in enumerate(name):
        power = len(name) - 1 - i + 3
        weight = pow(33, power, 2**32)
        poly_hash = (poly_hash + ord(c) * weight) % (2**32)
    
    # Apply mixing
    mixed = mix_func(poly_hash)
    
    return mixed == hash_val

# Test various mixing functions
mixing_functions = [
    ("identity", lambda h: h % 65536),
    ("xor_shift", lambda h: ((h ^ (h >> 16)) * 0x85ebca6b) % 65536),
    ("multiply_shift", lambda h: ((h * 0x5bd1e995) >> 16) % 65536),
    ("avalanche", lambda h: ((h ^ (h >> 15)) * 0x1b873593) % 65536),
    ("murmur3_final", lambda h: (
        (h ^ (h >> 16)) * 0x85ebca6b ^ (((h ^ (h >> 16)) * 0x85ebca6b) >> 13)
    ) * 0xc2b2ae35 % 65536),
]

# Test each function on a subset of samples
test_samples = list(patterns.items())[:100]

print("Testing mixing functions on 100 samples:\n")
for func_name, mix_func in mixing_functions:
    matches = sum(1 for name, data in test_samples 
                  if test_mixing_function(name, data['hash'], mix_func))
    print(f"  {func_name:20s}: {matches:3d}/100 matches ({matches}%)")

print("\n✓ Analysis complete")
