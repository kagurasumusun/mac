#!/usr/bin/env python3
"""Massive search for facet hash16 final mixing function with ML approach."""

import json
from pathlib import Path
import sys
import random
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from actool_linux.carwriter import _identifier

# Load collected patterns
patterns_file = Path(__file__).parent.parent / 'facet_hash_patterns_extended.json'
with open(patterns_file) as f:
    patterns = json.load(f)

print(f"Loaded {len(patterns)} patterns\n")

# Use larger subset for testing
test_samples = list(patterns.items())[:500]

print("=== Massive Search for Final Mixing Function ===\n")

# Compute polynomial hashes for all samples
poly_hashes = {}
for name, data in test_samples:
    poly_hash = 0
    for i, c in enumerate(name):
        power = len(name) - 1 - i + 3
        weight = pow(33, power, 2**32)
        poly_hash = (poly_hash + ord(c) * weight) % (2**32)
    poly_hashes[name] = poly_hash

# Generate massive set of candidate functions
def generate_massive_functions():
    """Generate a very large set of candidate mixing functions."""
    functions = []
    
    # Constants (expanded set)
    constants = [
        0x1234, 0x5678, 0x9ABC, 0xDEF0, 0x1357, 0x2468,
        0x85ebca6b, 0xc2b2ae35, 0x1b873593, 0xcc9e2d51,
        0x27d4eb2f, 0x165b5a15, 0x9e3779b1, 0x517cc1b7,
        34848, 6049, 5152, 35937, 0xFFFF, 0x10000,
        0x5bd1e995, 0xe6546b64, 0x25452545, 0x9e3779b9
    ]
    
    # Multipliers (expanded set)
    multipliers = [
        34848, 6049, 5152, 35937, 0x85ebca6b, 0xc2b2ae35,
        0x1b873593, 0xcc9e2d51, 0x27d4eb2f, 0x165b5a15,
        0x9e3779b1, 0x517cc1b7, 0x5bd1e995, 0xe6546b64,
        0x25452545, 0x9e3779b9, 0x27D4EB2F, 0x165B5A15
    ]
    
    # Shift amounts
    shifts = [0, 4, 8, 12, 16, 20, 24, 28]
    
    # Generate combinations (massive expansion)
    for mult in multipliers:
        for add in constants:
            # h_final = (h * mult + add) mod 65536
            functions.append((
                f"mult_add_{mult:08x}_{add:04x}",
                lambda h, m=mult, a=add: ((h * m) + a) % 65536
            ))
        
        for xor_val in constants:
            # h_final = ((h ^ xor_val) * mult) mod 65536
            functions.append((
                f"xor_mult_{xor_val:04x}_{mult:08x}",
                lambda h, x=xor_val, m=mult: ((h ^ x) * m) % 65536
            ))
            
            # h_final = ((h * mult) ^ xor_val) mod 65536
            functions.append((
                f"mult_xor_{mult:08x}_{xor_val:04x}",
                lambda h, m=mult, x=xor_val: ((h * m) ^ x) % 65536
            ))
        
        for shift in shifts:
            # h_final = ((h >> shift) * mult) mod 65536
            functions.append((
                f"shift_mult_{shift}_{mult:08x}",
                lambda h, s=shift, m=mult: ((h >> s) * m) % 65536
            ))
            
            # h_final = ((h << shift) * mult) mod 65536
            functions.append((
                f"lshift_mult_{shift}_{mult:08x}",
                lambda h, s=shift, m=mult: (((h << s) & 0xFFFFFFFF) * m) % 65536
            ))
    
    # More complex functions (expanded)
    for mult1 in multipliers[:10]:
        for mult2 in multipliers[:10]:
            for add in constants[:5]:
                # h_final = (((h * mult1) + add) * mult2) mod 65536
                functions.append((
                    f"complex_{mult1:08x}_{add:04x}_{mult2:08x}",
                    lambda h, m1=mult1, a=add, m2=mult2: 
                        ((((h * m1) % 65536) + a) * m2) % 65536
                ))
    
    # Avalanche-style functions (expanded)
    for const in constants[:10]:
        # Multiple avalanche variants
        functions.append((
            f"avalanche1_{const:08x}",
            lambda h, c=const: (
                ((h ^ (h >> 16)) * c) ^ ((((h ^ (h >> 16)) * c) >> 13))
            ) % 65536
        ))
        
        functions.append((
            f"avalanche2_{const:08x}",
            lambda h, c=const: (
                ((h * c) ^ ((h * c) >> 11)) * 0x85ebca6b
            ) % 65536
        ))
        
        functions.append((
            f"avalanche3_{const:08x}",
            lambda h, c=const: (
                (h ^ (h >> 7)) * c ^ ((h ^ (h >> 7)) * c >> 15)
            ) % 65536
        ))
    
    # Random search functions
    for i in range(100):
        seed = random.randint(0, 0xFFFFFFFF)
        functions.append((
            f"random_{seed:08x}",
            lambda h, s=seed: (((h * s) ^ (h >> 13)) * 0x5bd1e995) % 65536
        ))
    
    return functions

# Test all functions
functions = generate_massive_functions()
print(f"Testing {len(functions)} candidate functions...\n")

best_matches = []
best_count = 0

for func_name, mix_func in functions:
    matches = 0
    
    for name, data in test_samples:
        poly_hash = poly_hashes[name]
        
        try:
            mixed = mix_func(poly_hash)
            if mixed == data['hash']:
                matches += 1
        except:
            pass
    
    if matches > best_count:
        best_count = matches
        best_matches = [(func_name, matches)]
        print(f"  {func_name:60s}: {matches:3d}/500 matches ({matches/5:.1f}%)")
    elif matches == best_count and matches > 0:
        best_matches.append((func_name, matches))
    
    if matches == len(test_samples):
        print(f"\n✓ Found perfect match: {func_name}")
        break

print(f"\n=== Best Matches ===")
print(f"Top match count: {best_count}/500 ({best_count/5:.1f}%)")
print(f"Number of functions with this score: {len(best_matches)}")

if best_matches:
    print(f"\nTop 5 functions:")
    for func_name, matches in best_matches[:5]:
        print(f"  {func_name:60s}: {matches}/500")

if best_count < len(test_samples):
    print(f"\n✗ No perfect match found. Best match has {best_count/5:.1f}% accuracy.")
    print("  The mixing function likely involves:")
    print("  - Non-linear operations (modular arithmetic, lookup tables)")
    print("  - State-dependent computation")
    print("  - Or a completely different algorithm")
else:
    print(f"\n✓ Perfect match found!")

print("\n✓ Massive search complete")
