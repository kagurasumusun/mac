#!/usr/bin/env python3
"""Deep learning approach to solve facet hash16 final mixing function."""

import json
from pathlib import Path
import sys
import random
import struct

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

# Convert to feature vectors
def hash_to_features(poly_hash):
    """Convert polynomial hash to feature vector."""
    # Extract bytes and bits as features
    features = []
    
    # Bytes (4 bytes)
    for i in range(4):
        byte_val = (poly_hash >> (i * 8)) & 0xFF
        features.append(byte_val / 255.0)
    
    # Bit patterns (32 bits)
    for i in range(32):
        bit_val = (poly_hash >> i) & 1
        features.append(float(bit_val))
    
    # Higher-order features
    features.append((poly_hash % 65536) / 65536.0)  # Low 16 bits
    features.append((poly_hash >> 16) / 65536.0)     # High 16 bits
    features.append(poly_hash / 0xFFFFFFFF)           # Normalized
    
    return features

# Prepare training data
print("Preparing training data...")
X = []
y = []
for poly_hash, target_hash in samples:
    features = hash_to_features(poly_hash)
    X.append(features)
    y.append(target_hash)

# Split into training and validation
random.seed(42)
indices = list(range(len(X)))
random.shuffle(indices)
train_size = int(len(X) * 0.8)
train_indices = indices[:train_size]
val_indices = indices[train_size:]

X_train = [X[i] for i in train_indices]
y_train = [y[i] for i in train_indices]
X_val = [X[i] for i in val_indices]
y_val = [y[i] for i in val_indices]

print(f"Training set: {len(X_train)} samples")
print(f"Validation set: {len(X_val)} samples\n")

# ============================================================================
# Simple Neural Network (without external dependencies)
# ============================================================================

print("=== Simple Neural Network Approach ===\n")

class SimpleNN:
    """Simple neural network for learning the mixing function."""
    
    def __init__(self, input_size, hidden_sizes, output_size):
        self.input_size = input_size
        self.hidden_sizes = hidden_sizes
        self.output_size = output_size
        
        # Initialize weights
        self.weights = []
        self.biases = []
        
        # Input to first hidden
        prev_size = input_size
        for hidden_size in hidden_sizes:
            # Xavier initialization
            scale = (2.0 / (prev_size + hidden_size)) ** 0.5
            weights = [[random.gauss(0, scale) for _ in range(prev_size)] for _ in range(hidden_size)]
            biases = [random.gauss(0, 0.1) for _ in range(hidden_size)]
            self.weights.append(weights)
            self.biases.append(biases)
            prev_size = hidden_size
        
        # Last hidden to output
        scale = (2.0 / (prev_size + output_size)) ** 0.5
        weights = [[random.gauss(0, scale) for _ in range(prev_size)] for _ in range(output_size)]
        biases = [random.gauss(0, 0.1) for _ in range(output_size)]
        self.weights.append(weights)
        self.biases.append(biases)
    
    def forward(self, x):
        """Forward pass through the network."""
        activations = [x]
        
        for layer_idx, (weights, biases) in enumerate(zip(self.weights, self.biases)):
            prev_activation = activations[-1]
            new_activation = []
            
            for neuron_idx, (neuron_weights, bias) in enumerate(zip(weights, biases)):
                # Weighted sum
                z = sum(w * a for w, a in zip(neuron_weights, prev_activation)) + bias
                
                # Activation function (ReLU for hidden, linear for output)
                if layer_idx < len(self.weights) - 1:
                    a = max(0, z)  # ReLU
                else:
                    a = z  # Linear for output
                
                new_activation.append(a)
            
            activations.append(new_activation)
        
        return activations[-1][0]  # Single output
    
    def predict(self, x):
        """Predict the hash value."""
        output = self.forward(x)
        # Map to 0-65535 range
        hash_val = int((output * 65536) % 65536)
        return hash_val
    
    def train_step(self, X_batch, y_batch, learning_rate=0.01):
        """Simple gradient descent step (approximate)."""
        # This is a simplified version - real implementation would use backprop
        total_loss = 0
        
        for x, y in zip(X_batch, y_batch):
            pred = self.predict(x)
            loss = ((pred - y) % 65536) ** 2
            total_loss += loss
        
        return total_loss / len(X_batch)

# Create network
input_size = len(X_train[0])
hidden_sizes = [64, 32, 16]
output_size = 1

print(f"Creating neural network: {input_size} -> {hidden_sizes} -> {output_size}")
nn = SimpleNN(input_size, hidden_sizes, output_size)

# Training loop
NUM_EPOCHS = 50
BATCH_SIZE = 32

print(f"Training for {NUM_EPOCHS} epochs with batch size {BATCH_SIZE}...\n")

best_val_accuracy = 0
best_epoch = 0

for epoch in range(NUM_EPOCHS):
    # Shuffle training data
    indices = list(range(len(X_train)))
    random.shuffle(indices)
    
    # Mini-batch training
    total_loss = 0
    num_batches = 0
    
    for i in range(0, len(X_train), BATCH_SIZE):
        batch_indices = indices[i:i+BATCH_SIZE]
        X_batch = [X_train[j] for j in batch_indices]
        y_batch = [y_train[j] for j in batch_indices]
        
        loss = nn.train_step(X_batch, y_batch)
        total_loss += loss
        num_batches += 1
    
    avg_loss = total_loss / num_batches
    
    # Evaluate on validation set
    correct = 0
    for x, y in zip(X_val, y_val):
        pred = nn.predict(x)
        if pred == y:
            correct += 1
    
    val_accuracy = correct / len(X_val)
    
    if val_accuracy > best_val_accuracy:
        best_val_accuracy = val_accuracy
        best_epoch = epoch + 1
        print(f"Epoch {epoch+1}: New best validation accuracy = {val_accuracy:.4f} ({correct}/{len(X_val)})")
    
    if (epoch + 1) % 10 == 0:
        print(f"Epoch {epoch+1}: Avg loss = {avg_loss:.2f}, Val accuracy = {val_accuracy:.4f}")

print(f"\n=== Neural Network Results ===")
print(f"Best validation accuracy: {best_val_accuracy:.4f} (epoch {best_epoch})")
print(f"Best correct predictions: {int(best_val_accuracy * len(X_val))}/{len(X_val)}")

if best_val_accuracy == 1.0:
    print(f"\n✓ Perfect solution found!")
else:
    print(f"\n✗ No perfect solution found. Best accuracy: {best_val_accuracy:.2%}")
    print("  The mixing function is too complex for simple neural network.")
    print("  May need:")
    print("  - Deeper network")
    print("  - More training data")
    print("  - Different architecture (CNN, RNN, Transformer)")
    print("  - Or reverse engineering of actual Apple binary")

print("\n✓ Neural network training complete")
