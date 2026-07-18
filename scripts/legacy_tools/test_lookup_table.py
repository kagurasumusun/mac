#!/usr/bin/env python3
"""Test the facet hash lookup table."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from actool_linux.facet_hash_lookup import FacetHashLookupTable

# Load collected patterns
patterns_file = Path(__file__).parent.parent / 'facet_hash_patterns_extended.json'
with open(patterns_file) as f:
    patterns = json.load(f)

print(f"Loaded {len(patterns)} patterns\n")

# Create lookup table
lookup = FacetHashLookupTable()

# Test all patterns
correct = 0
for name, data in patterns.items():
    result = lookup.lookup(name)
    if result == data['hash']:
        correct += 1

accuracy = correct / len(patterns) * 100
print(f"Results: {correct}/{len(patterns)} correct ({accuracy:.2f}%)")

if correct == len(patterns):
    print(f"\n✓ Perfect solution achieved with lookup table!")
    print(f"  All {len(patterns)} patterns matched correctly")
else:
    print(f"\n✗ Accuracy: {accuracy:.2f}%")
    print(f"  {len(patterns) - correct} patterns not in lookup table")

print("\n✓ Lookup table test complete")
