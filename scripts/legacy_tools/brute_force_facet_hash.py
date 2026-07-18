#!/usr/bin/env python3
"""Brute-force search for facet hash16 final mixing function."""

import json
from pathlib import Path
import sys
from itertools import product

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from actool_linux.carwriter import _identifier

# Load collected patterns
patterns_file = Path(__file__).parent.parent / 'facet_hash_patterns_extended.json'
with open(patterns_file) as f:
    patterns = json.load(f)

print(f"Loaded {len(patterns)} patterns\n")

# Use a subset for faster testing
test_samples = list(patterns.items())[:200]

print("=== Brute-Force Search for Final Mixing Function ===\n")

# Generate candidate mixing functions
def generate_mixing_functions():
    """Generate a large set of candidate mixing functions."""
    functions = []
    
    # Constants to try
    constants = [0x1234, 0x5678, 0x9ABC, 0xDEF0, 0x1357, 0x2468, 
                 0x85ebca6b, 0xc2b2ae35, 0x1b873593, 0xcc9e2d51,
                 34848, 6049, 5152, 35937]
    
    # Multipliers to try
    multipliers = [34848, 6049, 5152, 35937, 0x85ebca6b, 0xc2b2ae35,
                   0x1b873593, 0xcc9e2d51, 0x27d4eb2f, 0x165b5a15]
    
    # Shift amounts
    shifts = [0, 8, 16, 24]
    
    # Generate combinations
    for mult in multipliers:
        for add in constants:
            # h_final = (h * mult + add) mod 65536
            functions.append((
                f"multiply_add_{mult:08x}_{add:04x}",
                lambda h, m=mult, a=add: ((h * m) + a) % 65536
            ))
        
        for xor_val in constants:
            # h_final = ((h ^ xor_val) * mult) mod 65536
            functions.append((
                f"xor_multiply_{xor_val:04x}_{mult:08x}",
                lambda h, x=xor_val, m=mult: ((h ^ x) * m) % 65536
            ))
            
            # h_final = ((h * mult) ^ xor_val) mod 65536
            functions.append((
                f"multiply_xor_{mult:08x}_{xor_val:04x}",
                lambda h, m=mult, x=xor_val: ((h * m) ^ x) % 65536
            ))
        
        for shift in shifts:
            # h_final = ((h >> shift) * mult) mod 65536
            functions.append((
                f"shift_multiply_{shift}_{mult:08x}",
                lambda h, s=shift, m=mult: ((h >> s) * m) % 65536
            ))
    
    # More complex functions
    for mult1 in multipliers[:5]:
        for mult2 in multipliers[:5]:
            # h_final = (((h * mult1) % 65536) * mult2) % 65536
            functions.append((
                f"double_multiply_{mult1:08x}_{mult2:08x}",
                lambda h, m1=mult1, m2=mult2: (((h * m1) % 65536) * m2) % 65536
            ))
    
    # Avalanche-style functions
    for const in constants[:5]:
        # h = h ^ (h >> 16); h = h * const; h = h ^ (h >> 13)
        functions.append((
            f"avalanche_{const:08x}",
            lambda h, c=const: (
                ((h ^ (h >> 16)) * c) ^ ((((h ^ (h >> 16)) * c) >> 13))
            ) % 65536
        ))
    
    return functions

# Test all functions
functions = generate_mixing_functions()
print(f"Testing {len(functions)} candidate functions...\n")

best_match = None
best_count = 0

for func_name, mix_func in functions:
    matches = 0
    
    for name, data in test_samples:
        # Compute polynomial hash
        poly_hash = 0
        for i, c in enumerate(name):
            power = len(name) - 1 - i + 3
            weight = pow(33, power, 2**32)
            poly_hash = (poly_hash + ord(c) * weight) % (2**32)
        
        # Apply mixing
        try:
            mixed = mix_func(poly_hash)
            if mixed == data['hash']:
                matches += 1
        except:
            pass
    
    if matches > best_count:
        best_count = matches
        best_match = func_name
        print(f"  {func_name:50s}: {matches:3d}/200 matches ({matches/2:.1f}%)")
        
        if matches == len(test_samples):
            print(f"\n✓ Found perfect match: {func_name}")
            break

print(f"\n=== Best Match ===")
print(f"Function: {best_match}")
print(f"Matches: {best_count}/200 ({best_count/2:.1f}%)")

if best_count < len(test_samples):
    print(f"\n✗ No perfect match found. Best match has {best_count/2:.1f}% accuracy.")
    print("  The mixing function may be more complex or involve additional state.")
else:
    print(f"\n✓ Perfect match found!")

print("\n✓ Brute-force search complete")
