#!/usr/bin/env python3
"""Exhaustive search for facet hash16 algorithm structure."""

import json
from pathlib import Path
import sys
import random

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from actool_linux.carwriter import _identifier

# Load collected patterns
patterns_file = Path(__file__).parent.parent / 'facet_hash_patterns_extended.json'
with open(patterns_file) as f:
    patterns = json.load(f)

print(f"Loaded {len(patterns)} patterns\n")

# Compute polynomial hashes for all samples
print("Computing polynomial hashes...")
samples = []
for name, data in patterns.items():
    poly_hash = 0
    for i, c in enumerate(name):
        power = len(name) - 1 - i + 3
        weight = pow(33, power, 2**32)
        poly_hash = (poly_hash + ord(c) * weight) % (2**32)
    samples.append((poly_hash, data['hash']))

print(f"Computed {len(samples)} samples\n")

# Use subset for faster testing
test_samples = samples[:500]

print(f"Test set: {len(test_samples)} samples\n")

# ============================================================================
# Exhaustive Algorithm Search
# ============================================================================

print("=== Exhaustive Algorithm Search ===\n")

def swap_bytes_16bit(value):
    """Swap upper and lower 8 bits."""
    return ((value & 0xFF) << 8) | ((value >> 8) & 0xFF)

def algorithm_variant_1(poly_hash, c1, c2, c3):
    """Variant 1: XOR -> Swap -> Shift+XOR -> Multiply -> Shift+XOR"""
    h = poly_hash % 65536
    h = (h ^ c1) & 0xFFFF
    h = swap_bytes_16bit(h)
    h = (h ^ (h >> 3)) & 0xFFFF
    h = (h * c2) & 0xFFFF
    h = (h ^ (h >> 7)) & 0xFFFF
    return h

def algorithm_variant_2(poly_hash, c1, c2, c3):
    """Variant 2: Multiply -> XOR -> Swap -> Shift+XOR"""
    h = poly_hash % 65536
    h = (h * c1) & 0xFFFF
    h = (h ^ c2) & 0xFFFF
    h = swap_bytes_16bit(h)
    h = (h ^ (h >> c3)) & 0xFFFF
    return h

def algorithm_variant_3(poly_hash, c1, c2, c3):
    """Variant 3: Shift+XOR -> Multiply -> XOR -> Swap"""
    h = poly_hash % 65536
    h = (h ^ (h >> c1)) & 0xFFFF
    h = (h * c2) & 0xFFFF
    h = (h ^ c3) & 0xFFFF
    h = swap_bytes_16bit(h)
    return h

def algorithm_variant_4(poly_hash, c1, c2, c3):
    """Variant 4: Swap -> Multiply -> Shift+XOR -> XOR"""
    h = poly_hash % 65536
    h = swap_bytes_16bit(h)
    h = (h * c1) & 0xFFFF
    h = (h ^ (h >> c2)) & 0xFFFF
    h = (h ^ c3) & 0xFFFF
    return h

def algorithm_variant_5(poly_hash, c1, c2, c3):
    """Variant 5: Simple - XOR -> Multiply -> XOR"""
    h = poly_hash % 65536
    h = (h ^ c1) & 0xFFFF
    h = (h * c2) & 0xFFFF
    h = (h ^ c3) & 0xFFFF
    return h

def test_algorithm(algo_func, c1, c2, c3):
    """Test an algorithm with given constants."""
    correct = 0
    for poly_hash, target_hash in test_samples:
        result = algo_func(poly_hash, c1, c2, c3)
        if result == target_hash:
            correct += 1
    return correct

# Test different algorithm variants with random constants
print("Testing algorithm variants with random constants...\n")

algorithms = [
    ("Variant 1 (XOR->Swap->Shift->Mult->Shift)", algorithm_variant_1),
    ("Variant 2 (Mult->XOR->Swap->Shift)", algorithm_variant_2),
    ("Variant 3 (Shift->Mult->XOR->Swap)", algorithm_variant_3),
    ("Variant 4 (Swap->Mult->Shift->XOR)", algorithm_variant_4),
    ("Variant 5 (XOR->Mult->XOR)", algorithm_variant_5),
]

best_overall = 0
best_algo = None
best_constants = None

for algo_name, algo_func in algorithms:
    print(f"Testing {algo_name}...")
    
    # Test with random constants
    for _ in range(100):
        c1 = random.randint(0, 0xFFFF)
        c2 = random.randint(1, 0xFFFF)  # Avoid 0 for multiplication
        c3 = random.randint(0, 0xFFFF)
        
        correct = test_algorithm(algo_func, c1, c2, c3)
        
        if correct > best_overall:
            best_overall = correct
            best_algo = algo_name
            best_constants = (c1, c2, c3)
            accuracy = correct / len(test_samples) * 100
            print(f"  New best: {correct}/{len(test_samples)} ({accuracy:.2f}%) with c1=0x{c1:04X}, c2=0x{c2:04X}, c3=0x{c3:04X}")
    
    print(f"  Best for this variant: {best_overall}/{len(test_samples)} ({best_overall/len(test_samples)*100:.2f}%)\n")

print(f"\n=== Overall Results ===")
print(f"Best algorithm: {best_algo}")
print(f"Best constants: c1=0x{best_constants[0]:04X}, c2=0x{best_constants[1]:04X}, c3=0x{best_constants[2]:04X}")
print(f"Best accuracy: {best_overall}/{len(test_samples)} ({best_overall/len(test_samples)*100:.2f}%)")

if best_overall == len(test_samples):
    print(f"\n✓ Perfect solution found!")
else:
    print(f"\n✗ Best accuracy: {best_overall/len(test_samples)*100:.2f}%")
    print("  Algorithm structure needs more exploration")
    print("  May need to try:")
    print("  - Different shift amounts")
    print("  - Multiple rounds")
    print("  - Lookup tables")
    print("  - Or reverse engineering")

print("\n✓ Exhaustive search complete")
