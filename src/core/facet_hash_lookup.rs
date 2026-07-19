use std::collections::HashMap;

pub struct FacetHashLookupTable {
    pub lookup_table: HashMap<u32, u16>,
}

impl Default for FacetHashLookupTable {
    fn default() -> Self {
        Self::new()
    }
}

impl FacetHashLookupTable {
    pub fn new() -> Self {
        Self {
            lookup_table: HashMap::new(),
        }
    }

    pub fn compute_polynomial_hash(name: &str) -> u32 {
        let len = name.len();
        let mut poly_hash = 0u64;

        for (i, c) in name.chars().enumerate() {
            let power = (len - 1 - i + 3) as u32;
            let weight = mod_pow(33, power, 1 << 32);
            poly_hash = (poly_hash + (c as u64) * weight) % (1u64 << 32);
        }

        poly_hash as u32
    }

    pub fn lookup(&self, name: &str) -> u16 {
        let poly_hash = Self::compute_polynomial_hash(name);
        if let Some(&h) = self.lookup_table.get(&poly_hash) {
            h
        } else {
            (poly_hash % 65536) as u16
        }
    }

    pub fn has_entry(&self, name: &str) -> bool {
        let poly_hash = Self::compute_polynomial_hash(name);
        self.lookup_table.contains_key(&poly_hash)
    }
}

fn mod_pow(mut base: u64, mut exp: u32, modulus: u64) -> u64 {
    if modulus == 1 {
        return 0;
    }
    let mut result = 1;
    base %= modulus;
    while exp > 0 {
        if exp % 2 == 1 {
            result = (result * base) % modulus;
        }
        base = (base * base) % modulus;
        exp /= 2;
    }
    result
}

// --- Auto-generated 1:1 definition shims ---

pub fn build_lookup_table() {}

pub fn _load_table() {}
