#!/usr/bin/env python3
"""Large-scale genetic algorithm for facet hash16 final mixing function."""

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

# Split into training and validation sets
random.shuffle(samples)
train_size = int(len(samples) * 0.8)
train_samples = samples[:train_size]
val_samples = samples[train_size:]

print(f"Training set: {len(train_samples)} samples")
print(f"Validation set: {len(val_samples)} samples\n")

# ============================================================================
# Large-Scale Genetic Algorithm
# ============================================================================

print("=== Large-Scale Genetic Algorithm ===\n")

class MixingFunction:
    """A candidate mixing function represented as a sequence of operations."""
    
    OPERATIONS = [
        ('multiply', lambda h, p: (h * p) % 65536),
        ('add', lambda h, p: (h + p) % 65536),
        ('xor', lambda h, p: (h ^ p) % 65536),
        ('shift_right', lambda h, p: (h >> (p % 32)) % 65536),
        ('shift_left', lambda h, p: ((h << (p % 32)) & 0xFFFFFFFF) % 65536),
        ('rotate_right', lambda h, p: ((h >> (p % 32)) | (h << (32 - (p % 32)))) % 65536),
        ('and', lambda h, p: (h & p) % 65536),
        ('or', lambda h, p: (h | p) % 65536),
        ('not_xor', lambda h, p: ((~h) ^ p) % 65536),
        ('multiply_add', lambda h, p: ((h * (p >> 8)) + (p & 0xFF)) % 65536),
    ]
    
    def __init__(self, operations=None):
        if operations is None:
            # Random initialization: 4-8 operations
            num_ops = random.randint(4, 8)
            self.operations = []
            for _ in range(num_ops):
                op_name, op_func = random.choice(self.OPERATIONS)
                param = random.randint(0, 0xFFFF)
                self.operations.append((op_name, param))
        else:
            self.operations = operations
    
    def apply(self, h):
        """Apply the mixing function to a hash value."""
        result = h
        for op_name, param in self.operations:
            _, op_func = next((n, f) for n, f in self.OPERATIONS if n == op_name)
            result = op_func(result, param)
        return result
    
    def fitness(self, samples):
        """Calculate fitness (number of correct predictions)."""
        correct = 0
        for poly_hash, target_hash in samples:
            if self.apply(poly_hash) == target_hash:
                correct += 1
        return correct
    
    def mutate(self):
        """Create a mutated copy."""
        new_ops = list(self.operations)
        
        # Random mutation
        mutation_type = random.choice(['modify', 'add', 'remove', 'swap', 'replace'])
        
        if mutation_type == 'modify' and new_ops:
            # Modify a random operation
            idx = random.randint(0, len(new_ops) - 1)
            op_name, _ = new_ops[idx]
            new_param = random.randint(0, 0xFFFF)
            new_ops[idx] = (op_name, new_param)
        
        elif mutation_type == 'add' and len(new_ops) < 10:
            # Add a random operation
            op_name, _ = random.choice(self.OPERATIONS)
            param = random.randint(0, 0xFFFF)
            new_ops.append((op_name, param))
        
        elif mutation_type == 'remove' and len(new_ops) > 3:
            # Remove a random operation
            idx = random.randint(0, len(new_ops) - 1)
            new_ops.pop(idx)
        
        elif mutation_type == 'swap' and len(new_ops) >= 2:
            # Swap two operations
            idx1, idx2 = random.sample(range(len(new_ops)), 2)
            new_ops[idx1], new_ops[idx2] = new_ops[idx2], new_ops[idx1]
        
        elif mutation_type == 'replace' and new_ops:
            # Replace a random operation with a different one
            idx = random.randint(0, len(new_ops) - 1)
            op_name, op_func = random.choice(self.OPERATIONS)
            param = random.randint(0, 0xFFFF)
            new_ops[idx] = (op_name, param)
        
        return MixingFunction(new_ops)
    
    def crossover(self, other):
        """Create a child by crossing over with another function."""
        # Two-point crossover
        if len(self.operations) < 2 or len(other.operations) < 2:
            return MixingFunction()
        
        split1 = random.randint(1, len(self.operations) - 1)
        split2 = random.randint(1, len(other.operations) - 1)
        
        new_ops = self.operations[:split1] + other.operations[split2:]
        return MixingFunction(new_ops)
    
    def __str__(self):
        ops_str = ', '.join(f"{name}({param:04x})" for name, param in self.operations)
        return f"MixingFunction([{ops_str}])"


# Large-scale genetic algorithm parameters
POPULATION_SIZE = 1000
GENERATIONS = 500  # Reduced from 1000 for time constraints
ELITISM_COUNT = 50
MUTATION_RATE = 0.4

# Initialize population
print(f"Initializing population of {POPULATION_SIZE} individuals...")
population = [MixingFunction() for _ in range(POPULATION_SIZE)]

best_ever = None
best_ever_fitness = 0

print(f"Running genetic algorithm for {GENERATIONS} generations...\n")

for generation in range(GENERATIONS):
    # Evaluate fitness
    fitness_scores = [(func, func.fitness(train_samples)) for func in population]
    fitness_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Track best
    if fitness_scores[0][1] > best_ever_fitness:
        best_ever_fitness = fitness_scores[0][1]
        best_ever = fitness_scores[0][0]
        print(f"Generation {generation+1}: New best fitness = {best_ever_fitness}/{len(train_samples)} ({best_ever_fitness/len(train_samples)*100:.2f}%)")
        print(f"  {best_ever}")
    
    # Early stopping if perfect solution found
    if best_ever_fitness == len(train_samples):
        print(f"\n✓ Perfect solution found at generation {generation+1}!")
        break
    
    # Selection and reproduction
    new_population = []
    
    # Elitism: keep top individuals
    for func, _ in fitness_scores[:ELITISM_COUNT]:
        new_population.append(func)
    
    # Generate rest through crossover and mutation
    while len(new_population) < POPULATION_SIZE:
        # Tournament selection
        parent1 = max(random.sample(fitness_scores[:100], 5), key=lambda x: x[1])[0]
        parent2 = max(random.sample(fitness_scores[:100], 5), key=lambda x: x[1])[0]
        
        # Crossover
        child = parent1.crossover(parent2)
        
        # Mutation
        if random.random() < MUTATION_RATE:
            child = child.mutate()
        
        new_population.append(child)
    
    population = new_population
    
    # Progress update
    if (generation + 1) % 50 == 0:
        print(f"Generation {generation+1}: Best fitness = {best_ever_fitness}/{len(train_samples)} ({best_ever_fitness/len(train_samples)*100:.2f}%)")

print(f"\n=== Large-Scale Genetic Algorithm Results ===")
print(f"Best fitness: {best_ever_fitness}/{len(train_samples)} ({best_ever_fitness/len(train_samples)*100:.2f}%)")
print(f"Best function: {best_ever}")

# Validate on validation set
val_fitness = best_ever.fitness(val_samples)
print(f"Validation fitness: {val_fitness}/{len(val_samples)} ({val_fitness/len(val_samples)*100:.2f}%)")

if best_ever_fitness == len(train_samples) and val_fitness == len(val_samples):
    print(f"\n✓ Perfect solution found!")
    print(f"Operations:")
    for op_name, param in best_ever.operations:
        print(f"  {op_name}: {param} (0x{param:04x})")
else:
    print(f"\n✗ No perfect solution found. Best accuracy: {best_ever_fitness/len(train_samples)*100:.2f}%")
    print("  Even with large-scale GA, the mixing function remains elusive.")
    print("  This strongly suggests:")
    print("  - The function uses lookup tables")
    print("  - Or involves cryptographic operations")
    print("  - Or is a completely different algorithm (not sequential operations)")
    print("  - Reverse engineering of Apple binary may be necessary")

print("\n✓ Large-scale genetic algorithm complete")
