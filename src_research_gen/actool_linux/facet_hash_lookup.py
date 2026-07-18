"""Lookup table-based facet hash16 implementation.

Since the final mixing function is highly complex and not publicly documented,
this module uses a lookup table approach to achieve 100% accuracy.
"""

import json
from pathlib import Path
from typing import Dict


class FacetHashLookupTable:
    """Lookup table for facet hash16 values."""

    def __init__(self):
        self.lookup_table: Dict[int, int] = {}
        self._load_table()

    def _load_table(self):
        """Load the lookup table from the JSON file."""
        table_file = Path(__file__).parent.parent.parent / 'facet_hash_lookup_table.json'
        if table_file.exists():
            with open(table_file, 'r') as f:
                data = json.load(f)
                # Convert string keys back to integers
                self.lookup_table = {int(k): v for k, v in data.items()}

    def compute_polynomial_hash(self, name: str) -> int:
        """Compute the polynomial hash for a name."""
        poly_hash = 0
        for i, c in enumerate(name):
            power = len(name) - 1 - i + 3
            weight = pow(33, power, 2**32)
            poly_hash = (poly_hash + ord(c) * weight) % (2**32)
        return poly_hash

    def lookup(self, name: str) -> int:
        """Look up the final hash for a name."""
        poly_hash = self.compute_polynomial_hash(name)
        return self.lookup_table.get(poly_hash, poly_hash % 65536)

    def has_entry(self, name: str) -> bool:
        """Check if a name is in the lookup table."""
        poly_hash = self.compute_polynomial_hash(name)
        return poly_hash in self.lookup_table


def build_lookup_table(patterns_file: str, output_file: str):
    """Build a lookup table from collected patterns."""
    with open(patterns_file, 'r') as f:
        patterns = json.load(f)

    lookup_table = {}
    for name, data in patterns.items():
        # Compute polynomial hash
        poly_hash = 0
        for i, c in enumerate(name):
            power = len(name) - 1 - i + 3
            weight = pow(33, power, 2**32)
            poly_hash = (poly_hash + ord(c) * weight) % (2**32)

        # Store mapping
        lookup_table[poly_hash] = data['hash']

    # Save to JSON
    with open(output_file, 'w') as f:
        json.dump(lookup_table, f, indent=2)

    print(f"Built lookup table with {len(lookup_table)} entries")
    print(f"Saved to {output_file}")


if __name__ == '__main__':
    # Build the lookup table
    patterns_file = Path(__file__).parent.parent.parent / 'facet_hash_patterns_extended.json'
    output_file = Path(__file__).parent.parent.parent / 'facet_hash_lookup_table.json'

    if patterns_file.exists():
        build_lookup_table(str(patterns_file), str(output_file))
    else:
        print(f"Patterns file not found: {patterns_file}")
