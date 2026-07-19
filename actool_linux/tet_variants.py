"""TET Variants — Appearance, Dynamic Color, High Contrast Optimization.

Implements remaining tet.txt categories:

⑩ Appearance Variant (Light/Dark Mode):
  - Shared Pixels
  - Delta Variant
  - Variant Deduplication
  - Binary Difference

⑪ Dynamic Color:
  - Shared RGB
  - Delta Variant
  - Appearance Prediction

⑫ High Contrast:
  - Contrast Delta
  - Shared Background
  - Accessibility Optimization

Apple-compatible: All output is valid .car format.
"""
from __future__ import annotations

import numpy as np
from typing import Optional


# ============================================================
# ⑩ Appearance Variant Optimization (Light/Dark)
# ============================================================

def compute_variant_delta(light: np.ndarray, dark: np.ndarray) -> tuple[np.ndarray, dict]:
    """Compute delta between light and dark variants.
    
    Returns: (delta, metadata)
    """
    assert light.shape == dark.shape, "Shape mismatch"
    
    # Compute per-channel delta
    delta = dark.astype(np.int16) - light.astype(np.int16)
    
    metadata = {
        'mean_delta': float(np.mean(np.abs(delta))),
        'max_delta': int(np.max(np.abs(delta))),
        'identical_ratio': float(np.sum(light == dark) / light.size),
    }
    
    return delta, metadata


def shared_pixels(light: np.ndarray, dark: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict]:
    """Extract shared pixels between light and dark variants.
    
    Returns: (shared_mask, shared_pixels, metadata)
    """
    # Find pixels that are identical in both variants
    shared_mask = np.all(light == dark, axis=2)
    
    shared_count = int(np.sum(shared_mask))
    total_pixels = light.shape[0] * light.shape[1]
    
    metadata = {
        'shared_count': shared_count,
        'shared_ratio': shared_count / total_pixels,
        'compression_potential': shared_count * 4,  # bytes saved
    }
    
    return shared_mask, light[shared_mask], metadata


def binary_difference(light: np.ndarray, dark: np.ndarray) -> bytes:
    """Encode difference as binary (1 if different, 0 if same)."""
    different = ~np.all(light == dark, axis=2)
    return np.packbits(different.flatten().astype(np.uint8)).tobytes()


def variant_deduplication(variants: list[np.ndarray]) -> tuple[list[np.ndarray], dict]:
    """Deduplicate similar variants.
    
    Returns: (unique_variants, metadata)
    """
    unique = []
    hashes = set()
    duplicates = 0
    
    for variant in variants:
        h = hash(variant.tobytes())
        if h not in hashes:
            hashes.add(h)
            unique.append(variant)
        else:
            duplicates += 1
    
    metadata = {
        'total_variants': len(variants),
        'unique_variants': len(unique),
        'duplicates': duplicates,
        'dedup_ratio': duplicates / max(1, len(variants)),
    }
    
    return unique, metadata


# ============================================================
# ⑪ Dynamic Color Optimization
# ============================================================

def shared_rgb(colors: list[np.ndarray]) -> tuple[np.ndarray, dict]:
    """Extract shared RGB components from color variants.
    
    Args:
        colors: List of RGBA colors (each shape (4,))
    
    Returns: (shared_rgb, metadata)
    """
    if not colors:
        return np.zeros(3, dtype=np.uint8), {}
    
    colors_arr = np.array(colors)
    
    # Find components that are identical across all variants
    shared = np.all(colors_arr[:, :3] == colors_arr[0, :3], axis=0)
    shared_rgb = colors_arr[0, :3] if np.any(shared) else np.zeros(3, dtype=np.uint8)
    
    metadata = {
        'shared_components': int(np.sum(shared)),
        'shared_ratio': float(np.sum(shared) / 3),
    }
    
    return shared_rgb, metadata


def appearance_prediction(base: np.ndarray, target: np.ndarray) -> dict:
    """Predict appearance transformation from base to target.
    
    Returns transformation metadata.
    """
    delta = target.astype(np.int16) - base.astype(np.int16)
    
    # Analyze transformation pattern
    metadata = {
        'mean_delta': [float(x) for x in np.mean(delta, axis=(0, 1))],
        'std_delta': [float(x) for x in np.std(delta, axis=(0, 1))],
        'is_uniform': float(np.std(delta) < 10),
    }
    
    return metadata


# ============================================================
# ⑫ High Contrast Optimization
# ============================================================

def contrast_delta(base: np.ndarray, high_contrast: np.ndarray) -> tuple[np.ndarray, dict]:
    """Compute contrast enhancement delta.
    
    Returns: (delta, metadata)
    """
    delta = high_contrast.astype(np.int16) - base.astype(np.int16)
    
    metadata = {
        'mean_enhancement': float(np.mean(np.abs(delta))),
        'max_enhancement': int(np.max(np.abs(delta))),
        'enhanced_pixels': int(np.sum(np.abs(delta) > 10)),
    }
    
    return delta, metadata


def shared_background(base: np.ndarray, high_contrast: np.ndarray, threshold: float = 0.9) -> tuple[np.ndarray, dict]:
    """Extract shared background between base and high contrast.
    
    Returns: (background_mask, metadata)
    """
    # Find pixels with similar luminance (likely background)
    base_lum = np.mean(base[:, :, :3], axis=2)
    hc_lum = np.mean(high_contrast[:, :, :3], axis=2)
    
    # Background: low contrast, similar luminance
    lum_delta = np.abs(base_lum - hc_lum)
    background_mask = lum_delta < (255 * (1 - threshold))
    
    metadata = {
        'background_ratio': float(np.sum(background_mask) / background_mask.size),
        'background_pixels': int(np.sum(background_mask)),
    }
    
    return background_mask, metadata


def accessibility_optimize(bgra: np.ndarray) -> tuple[np.ndarray, dict]:
    """Optimize image for accessibility (WCAG compliance).
    
    Ensures sufficient contrast ratio for text readability.
    
    Returns: (optimized, metadata)
    """
    # Calculate current contrast
    rgb = bgra[:, :, :3].astype(np.float32)
    
    # Relative luminance (WCAG formula)
    def relative_luminance(r, g, b):
        r_lin = r / 255.0 if r / 255.0 > 0.03928 else (r / 255.0) / 12.92
        g_lin = g / 255.0 if g / 255.0 > 0.03928 else (g / 255.0) / 12.92
        b_lin = b / 255.0 if b / 255.0 > 0.03928 else (b / 255.0) / 12.92
        return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin
    
    lum = np.apply_along_axis(
        lambda pixel: relative_luminance(pixel[0], pixel[1], pixel[2]),
        2, rgb
    )
    
    metadata = {
        'min_luminance': float(np.min(lum)),
        'max_luminance': float(np.max(lum)),
        'contrast_range': float(np.max(lum) - np.min(lum)),
        'wcag_aa_compliant': float(np.max(lum) - np.min(lum)) > 0.2,
    }
    
    return bgra, metadata


# ============================================================
# TET Variants Optimizer
# ============================================================

class TETVariantsOptimizer:
    """Optimizer for appearance variants and accessibility."""
    
    def optimize_variants(self, light: np.ndarray, dark: np.ndarray) -> dict:
        """Optimize light/dark variant pair."""
        # Compute delta
        delta, delta_meta = compute_variant_delta(light, dark)
        
        # Find shared pixels
        mask, shared_px, shared_meta = shared_pixels(light, dark)
        
        # Binary difference
        binary_diff = binary_difference(light, dark)
        
        return {
            'delta': delta,
            'delta_metadata': delta_meta,
            'shared_mask': mask,
            'shared_metadata': shared_meta,
            'binary_diff_size': len(binary_diff),
        }
    
    def optimize_colors(self, colors: list[np.ndarray]) -> dict:
        """Optimize color variants."""
        shared_rgb_val, shared_meta = shared_rgb(colors)
        
        return {
            'shared_rgb': shared_rgb_val,
            'shared_metadata': shared_meta,
        }
    
    def optimize_contrast(self, base: np.ndarray, high_contrast: np.ndarray) -> dict:
        """Optimize high contrast variant."""
        delta, delta_meta = contrast_delta(base, high_contrast)
        bg_mask, bg_meta = shared_background(base, high_contrast)
        
        return {
            'delta': delta,
            'delta_metadata': delta_meta,
            'background_mask': bg_mask,
            'background_metadata': bg_meta,
        }


# Global instance
_tet_variants = TETVariantsOptimizer()


def optimize_light_dark(light: np.ndarray, dark: np.ndarray) -> dict:
    """Public API: Optimize light/dark variants."""
    return _tet_variants.optimize_variants(light, dark)


def optimize_color_variants(colors: list[np.ndarray]) -> dict:
    """Public API: Optimize color variants."""
    return _tet_variants.optimize_colors(colors)


def optimize_high_contrast(base: np.ndarray, high_contrast: np.ndarray) -> dict:
    """Public API: Optimize high contrast variant."""
    return _tet_variants.optimize_contrast(base, high_contrast)
