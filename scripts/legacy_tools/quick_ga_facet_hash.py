#!/usr/bin/env python3
"""Quick genetic algorithm for facet hash16 final mixing function."""

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

# Use smaller subset for quick test
random.shuffle(samples)
test_samples = samples[:500]

print(f"Test set: {len(test_samples)} samples\n")

# ============================================================================
# Quick Genetic Algorithm
# ============================================================================

print("=== Quick Genetic Algorithm ===\n")

class MixingFunction:
    """A candidate mixing function."""
    
    OPERATIONS = [
        ('multiply', lambda h, p: (h * p) % 65536),
        ('add', lambda h, p: (h + p) % 65536),
        ('xor', lambda h, p: (h ^ p) % 65536),
        ('shift_right', lambda h, p: (h >> (p % 32)) % 65536),
    ]
    
    def __init__(self, operations=None):
        if operations is None:
            num_ops = random.randint(3, 6)
            self.operations = []
            for _ in range(num_ops):
                op_name, _ = random.choice(self.OPERATIONS)
                param = random.randint(0, 0xFFFF)
                self.operations.append((op_name, param))
        else:
            self.operations = operations
    
    def apply(self, h):
        result = h
        for op_name, param in self.operations:
            _, op_func = next((n, f) for n, f in self.OPERATIONS if n == op_name)
            result = op_func(result, param)
        return result
    
    def fitness(self, samples):
        correct = sum(1 for poly_hash, target_hash in samples if self.apply(poly_hash) == target_hash)
        return correct
    
    def mutate(self):
        new_ops = list(self.operations)
        if new_ops:
            idx = random.randint(0, len(new_ops) - 1)
            op_name, _ = new_ops[idx]
            new_param = random.randint(0, 0xFFFF)
            new_ops[idx] = (op_name, new_param)
        return MixingFunction(new_ops)
    
    def __str__(self):
        ops_str = ', '.join(f"{name}({param:04x})" for name, param in self.operations)
        return f"[{ops_str}]"


# Quick GA parameters
POPULATION_SIZE = 200
GENERATIONS = 100
ELITISM_COUNT = 20

print(f"Population: {POPULATION_SIZE}, Generations: {GENERATIONS}\n")

population = [MixingFunction() for _ in range(POPULATION_SIZE)]
best_ever = None
best_ever_fitness = 0

for generation in range(GENERATIONS):
    fitness_scores = [(func, func.fitness(test_samples)) for func in population]
    fitness_scores.sort(key=lambda x: x[1], reverse=True)
    
    if fitness_scores[0][1] > best_ever_fitness:
        best_ever_fitness = fitness_scores[0][1]
        best_ever = fitness_scores[0][0]
        print(f"Gen {generation+1}: Best = {best_ever_fitness}/{len(test_samples)} ({best_ever_fitness/len(test_samples)*100:.2f}%) - {best_ever}")
    
    if best_ever_fitness == len(test_samples):
        print(f"\n✓ Perfect solution at generation {generation+1}!")
        break
    
    new_population = [func for func, _ in fitness_scores[:ELITISM_COUNT]]
    
    while len(new_population) < POPULATION_SIZE:
        parent = random.choice(fitness_scores[:50])[0]
        child = parent.mutate()
        new_population.append(child)
    
    population = new_population

print(f"\n=== Results ===")
print(f"Best: {best_ever_fitness}/{len(test_samples)} ({best_ever_fitness/len(test_samples)*100:.2f}%)")
print(f"Function: {best_ever}")

if best_ever_fitness == len(test_samples):
    print(f"\n✓ Perfect solution found!")
else:
    print(f"\n✗ Best accuracy: {best_ever_fitness/len(test_samples)*100:.2f}%")
    print("  Mixing function is highly complex - may require reverse engineering")

print("\n✓ Quick GA complete")
