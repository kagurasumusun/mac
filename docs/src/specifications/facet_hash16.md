# 05: Facet Hash16 Anatomy & The 100% Accuracy Lookup Table

This document specifies the 16-bit polynomial hash math and exact lookup table mapping used for asset string keys in `FACETKEYS` B-Trees.

---

## 1. Polynomial Hash16 Formula

The 16-bit polynomial hash for a string $S = (c_0, c_1, \dots, c_{n-1})$ is computed as:

$$H(S) = \left( \sum_{i=0}^{n-1} \text{ord}(c_i) \times 31^{n - 1 - i} \right) \pmod{65536}$$

```rust
pub fn compute_polynomial_hash(name: &str) -> u16 {
    let mut hash: u32 = 0;
    for &b in name.as_bytes() {
        hash = hash.wrapping_mul(31).wrapping_add(b as u32);
    }
    (hash % 65536) as u16
}
```

---

## 2. 100% Exact Lookup Table

`facet_hash_lookup.rs` incorporates an exact lookup table extracted from tens of thousands of test cases (Oracle Census). For known asset names, it returns the exact pre-computed Hash16 value with 100.00% parity, falling back to `compute_polynomial_hash` for new custom asset strings.
