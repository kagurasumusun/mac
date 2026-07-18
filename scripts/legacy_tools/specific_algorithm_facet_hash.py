#!/usr/bin/env python3
"""Test specific algorithm for facet hash16 final mixing function."""

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

# ============================================================================
# Specific Algorithm Implementation
# ============================================================================

print("=== Testing Specific Algorithm ===\n")

def swap_bytes_16bit(value):
    """Swap upper and lower 8 bits of 16-bit value."""
    return ((value & 0xFF) << 8) | ((value >> 8) & 0xFF)

def specific_mixing_function(poly_hash, constant=0x9E37):
    """
    Specific mixing algorithm:
    1. XOR with constant
    2. Swap bytes (8-bit swap)
    3. Right shift 3 bits and XOR
    4. Multiply by special constant (golden ratio prime)
    5. Right shift 7 bits and XOR
    """
    # Work with 16-bit values
    h = poly_hash % 65536
    
    # Step 1: XOR with constant
    h = (h ^ constant) & 0xFFFF
    
    # Step 2: Swap bytes (8-bit swap)
    h = swap_bytes_16bit(h)
    
    # Step 3: Right shift 3 bits and XOR
    h = (h ^ (h >> 3)) & 0xFFFF
    
    # Step 4: Multiply by special constant (golden ratio prime: 0x9E37 = 40503)
    h = (h * 0x9E37) & 0xFFFF
    
    # Step 5: Right shift 7 bits and XOR
    h = (h ^ (h >> 7)) & 0xFFFF
    
    return h

# Test the algorithm
print("Testing algorithm with constant 0x9E37...\n")

correct = 0
for poly_hash, target_hash in samples:
    result = specific_mixing_function(poly_hash, 0x9E37)
    if result == target_hash:
        correct += 1

accuracy = correct / len(samples) * 100
print(f"Results: {correct}/{len(samples)} correct ({accuracy:.2f}%)")

if correct == len(samples):
    print(f"\n✓ Perfect solution found!")
    print(f"Algorithm: XOR(0x9E37) -> SwapBytes -> ShiftRight(3)+XOR -> Multiply(0x9E37) -> ShiftRight(7)+XOR")
else:
    print(f"\n✗ Accuracy: {accuracy:.2f}%")
    
    # Try different constants
    print("\n=== Testing Different Constants ===\n")
    
    # Golden ratio and prime constants
    test_constants = [
        0x9E37,  # Golden ratio
        0x9E3B,  # Prime
        0x9E3D,  # Prime
        0x9E3F,  # Prime
        0x85EB,  # Common hash constant
        0xC2B2,  # Common hash constant
        0x1B87,  # Common hash constant
        0xCC9E,  # Common hash constant
        0x5BD1,  # Common hash constant
        0xE654,  # Common hash constant
    ]
    
    best_constant = None
    best_accuracy = 0
    
    for constant in test_constants:
        correct = 0
        for poly_hash, target_hash in samples:
            result = specific_mixing_function(poly_hash, constant)
            if result == target_hash:
                correct += 1
        
        accuracy = correct / len(samples) * 100
        
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_constant = constant
        
        print(f"Constant 0x{constant:04X}: {correct}/{len(samples)} ({accuracy:.2f}%)")
    
    print(f"\nBest constant: 0x{best_constant:04X} with {best_accuracy:.2f}% accuracy")
    
    if best_accuracy == 100:
        print(f"\n✓ Perfect solution found!")
    else:
        print(f"\n✗ Best accuracy: {best_accuracy:.2f}%")
        print("  Algorithm structure may be correct but constant needs tuning")
        print("  Or algorithm needs modification")

print("\n✓ Specific algorithm test complete")
