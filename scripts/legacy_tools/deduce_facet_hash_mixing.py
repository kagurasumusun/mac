#!/usr/bin/env python3
"""Deduce the facet hash16 final mixing function using the 5152 pattern."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from actool_linux.carwriter import _identifier

# Load collected patterns
patterns_file = Path(__file__).parent.parent / 'facet_hash_patterns_extended.json'
with open(patterns_file) as f:
    patterns = json.load(f)

print(f"Loaded {len(patterns)} patterns\n")

# Key discovery: character swap differences at pos 0 are multiples of 5152
# 'a'<->'b' = 5152, 'a'<->'c' = 10304 = 5152*2, 'a'<->'d' = 15456 = 5152*3

# Hypothesis: The mixing function involves multiplication by a constant
# that results in 5152 when applied to the character difference (b-a = 1)

# Test: 5152 = 33^3 * k mod 65536
# 33^3 = 35937
# 5152 / 35937 = 0.143... (not an integer)

# Alternative: 5152 might be the result of a more complex operation
# Let's try to reverse-engineer it

print("=== Analyzing 5152 Pattern ===\n")

# 5152 in binary
print(f"5152 in binary: {bin(5152)}")
print(f"5152 = 2^5 * 161 = 32 * 161")
print(f"161 = 7 * 23")
print()

# Try to find a multiplier k such that:
# (1 * 33^3 * k) mod 65536 = 5152
# where 1 is the character difference (b - a)

# This means: 35937 * k ≡ 5152 (mod 65536)
# We need to find k

# Using extended Euclidean algorithm to find modular inverse
def extended_gcd(a, b):
    if a == 0:
        return b, 0, 1
    gcd, x1, y1 = extended_gcd(b % a, a)
    x = y1 - (b // a) * x1
    y = x1
    return gcd, x, y

def mod_inverse(a, m):
    gcd, x, _ = extended_gcd(a % m, m)
    if gcd != 1:
        return None  # No inverse exists
    return (x % m + m) % m

# Find k such that 35937 * k ≡ 5152 (mod 65536)
# k ≡ 5152 * 35937^(-1) (mod 65536)

inv_35937 = mod_inverse(35937, 65536)
if inv_35937:
    k = (5152 * inv_35937) % 65536
    print(f"35937^(-1) mod 65536 = {inv_35937}")
    print(f"k = 5152 * 35937^(-1) mod 65536 = {k}")
    print(f"Verification: 35937 * {k} mod 65536 = {(35937 * k) % 65536}")
    print()
    
    # Hypothesis: The final mixing function is:
    # h_final = (h_poly * k) mod 65536
    # where h_poly is the polynomial hash and k is the multiplier we found
    
    print(f"=== Testing Hypothesis: h_final = (h_poly * {k}) mod 65536 ===\n")
    
    # Test on a subset of samples
    test_samples = list(patterns.items())[:100]
    matches = 0
    
    for name, data in test_samples:
        # Compute polynomial hash
        poly_hash = 0
        for i, c in enumerate(name):
            power = len(name) - 1 - i + 3
            weight = pow(33, power, 2**32)
            poly_hash = (poly_hash + ord(c) * weight) % (2**32)
        
        # Apply mixing
        mixed = (poly_hash * k) % 65536
        
        if mixed == data['hash']:
            matches += 1
    
    print(f"Matches: {matches}/100 ({matches}%)")
    print()
    
    if matches > 0:
        print(f"✓ Found potential mixing multiplier: {k}")
        print(f"  Final mixing function: h_final = (h_poly * {k}) mod 65536")
    else:
        print("✗ Simple multiplication doesn't work, trying more complex functions...")
        print()
        
        # Try more complex functions
        complex_functions = [
            ("multiply_add", lambda h: ((h * k) + 0x1234) % 65536),
            ("xor_multiply", lambda h: ((h ^ 0x5678) * k) % 65536),
            ("multiply_xor", lambda h: ((h * k) ^ 0x9ABC) % 65536),
            ("double_multiply", lambda h: (((h * k) % 65536) * 0xDEF0) % 65536),
            ("shift_multiply", lambda h: (((h >> 16) * k) + ((h & 0xFFFF) * 0x1357)) % 65536),
        ]
        
        for func_name, mix_func in complex_functions:
            matches = sum(1 for name, data in test_samples
                         if mix_func(sum(ord(c) * pow(33, len(name) - 1 - i + 3, 2**32) 
                                      for i, c in enumerate(name)) % 2**32) == data['hash'])
            print(f"  {func_name:20s}: {matches:3d}/100 matches ({matches}%)")

else:
    print("✗ No modular inverse exists for 35937 mod 65536")
    print("  This means 35937 and 65536 are not coprime")
    print("  gcd(35937, 65536) = 1? Let's check...")
    
    import math
    gcd = math.gcd(35937, 65536)
    print(f"  gcd(35937, 65536) = {gcd}")
    
    if gcd == 1:
        print("  They are coprime, inverse should exist")
    else:
        print("  They are not coprime, simple linear function won't work")

print("\n✓ Analysis complete")
