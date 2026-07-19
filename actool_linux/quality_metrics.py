"""Quality Metrics — Perceptual quality evaluation for lossy compression.

This module provides quality metrics to ensure compression doesn't degrade
perceptual quality beyond acceptable thresholds.

Key metrics:
1. PSNR (Peak Signal-to-Noise Ratio) — standard metric
2. ΔE (CIE76) — perceptual color difference
3. SSIM (Structural Similarity) — structural quality
4. Edge Preservation Score — edge quality maintenance

Quality thresholds (visually indistinguishable):
- PSNR > 40dB: Excellent (virtually lossless)
- ΔE < 2.3: Just Noticeable Difference threshold
- SSIM > 0.95: Excellent structural similarity
"""
from __future__ import annotations

import numpy as np


def compute_psnr(original: np.ndarray, compressed: np.ndarray) -> float:
    """Compute Peak Signal-to-Noise Ratio.

    Args:
        original: Original image (H, W, C), uint8
        compressed: Compressed image (H, W, C), uint8

    Returns:
        PSNR in dB (higher is better, >40dB is excellent)
    """
    mse = np.mean((original.astype(np.float32) - compressed.astype(np.float32)) ** 2)
    if mse == 0:
        return float('inf')
    max_pixel = 255.0
    psnr = 20 * np.log10(max_pixel / np.sqrt(mse))
    return float(psnr)


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """Convert RGB to CIE Lab color space.

    Args:
        rgb: RGB array (..., 3), uint8 or float

    Returns:
        Lab array (..., 3), float
    """
    # RGB to XYZ
    rgb_f = rgb.astype(np.float32) / 255.0
    
    # sRGB to linear
    mask = rgb_f > 0.04045
    rgb_f[mask] = ((rgb_f[mask] + 0.055) / 1.055) ** 2.4
    rgb_f[~mask] = rgb_f[~mask] / 12.92
    
    # Linear RGB to XYZ (D65)
    r, g, b = rgb_f[..., 0], rgb_f[..., 1], rgb_f[..., 2]
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041
    
    # XYZ to Lab
    xn, yn, zn = 0.95047, 1.0, 1.08883  # D65 reference
    x, y, z = x / xn, y / yn, z / zn
    
    def f(t):
        mask = t > 0.008856
        result = np.zeros_like(t)
        result[mask] = t[mask] ** (1/3)
        result[~mask] = 7.787 * t[~mask] + 16/116
        return result
    
    L = 116 * f(y) - 16
    a = 500 * (f(x) - f(y))
    b = 200 * (f(y) - f(z))
    
    return np.stack([L, a, b], axis=-1)


def compute_delta_e(original: np.ndarray, compressed: np.ndarray) -> float:
    """Compute CIE76 ΔE (color difference).

    Args:
        original: Original RGB image (H, W, 3), uint8
        compressed: Compressed RGB image (H, W, 3), uint8

    Returns:
        Mean ΔE (lower is better, <2.3 is imperceptible)
    """
    lab_orig = rgb_to_lab(original[..., :3])
    lab_comp = rgb_to_lab(compressed[..., :3])
    
    delta_e = np.sqrt(np.sum((lab_orig - lab_comp) ** 2, axis=-1))
    return float(np.mean(delta_e))


def compute_ssim(original: np.ndarray, compressed: np.ndarray) -> float:
    """Compute Structural Similarity Index (SSIM).

    Simplified implementation using mean/variance.

    Args:
        original: Original image (H, W, C), uint8
        compressed: Compressed image (H, W, C), uint8

    Returns:
        SSIM value (0-1, higher is better, >0.95 is excellent)
    """
    orig_f = original.astype(np.float32)
    comp_f = compressed.astype(np.float32)
    
    # Constants
    C1 = (0.01 * 255) ** 2
    C2 = (0.03 * 255) ** 2
    
    # Mean
    mu_orig = np.mean(orig_f)
    mu_comp = np.mean(comp_f)
    
    # Variance
    sigma_orig_sq = np.var(orig_f)
    sigma_comp_sq = np.var(comp_f)
    
    # Covariance
    sigma_orig_comp = np.mean((orig_f - mu_orig) * (comp_f - mu_comp))
    
    # SSIM
    numerator = (2 * mu_orig * mu_comp + C1) * (2 * sigma_orig_comp + C2)
    denominator = (mu_orig ** 2 + mu_comp ** 2 + C1) * (sigma_orig_sq + sigma_comp_sq + C2)
    
    ssim = numerator / denominator
    return float(ssim)


def compute_edge_preservation(original: np.ndarray, compressed: np.ndarray) -> float:
    """Compute edge preservation score.

    Measures how well edges are maintained after compression.

    Args:
        original: Original image (H, W, C), uint8
        compressed: Compressed image (H, W, C), uint8

    Returns:
        Edge preservation score (0-1, higher is better)
    """
    # Convert to grayscale
    if original.ndim == 3:
        orig_gray = np.mean(original[..., :3].astype(np.float32), axis=2)
        comp_gray = np.mean(compressed[..., :3].astype(np.float32), axis=2)
    else:
        orig_gray = original.astype(np.float32)
        comp_gray = compressed.astype(np.float32)
    
    # Sobel edge detection
    def sobel(img):
        gx = np.abs(np.diff(img, axis=1))
        gy = np.abs(np.diff(img, axis=0))
        return gx, gy
    
    orig_gx, orig_gy = sobel(orig_gray)
    comp_gx, comp_gy = sobel(comp_gray)
    
    # Edge magnitude
    orig_mag = np.sqrt(orig_gx ** 2 + orig_gy ** 2)
    comp_mag = np.sqrt(comp_gx ** 2 + comp_gy ** 2)
    
    # Correlation
    if np.std(orig_mag) == 0 or np.std(comp_mag) == 0:
        return 1.0
    
    correlation = np.corrcoef(orig_mag.flatten(), comp_mag.flatten())[0, 1]
    return float(max(0, correlation))


def evaluate_quality(original: np.ndarray, compressed: np.ndarray) -> dict:
    """Comprehensive quality evaluation.

    Args:
        original: Original image (H, W, C), uint8
        compressed: Compressed image (H, W, C), uint8

    Returns:
        Dictionary with quality metrics
    """
    # Ensure same shape
    assert original.shape == compressed.shape, "Shape mismatch"
    
    # RGB channels for color metrics
    if original.shape[2] == 4:
        orig_rgb = original[..., :3]
        comp_rgb = compressed[..., :3]
    else:
        orig_rgb = original
        comp_rgb = compressed
    
    psnr = compute_psnr(original, compressed)
    delta_e = compute_delta_e(orig_rgb, comp_rgb)
    ssim = compute_ssim(original, compressed)
    edge_pres = compute_edge_preservation(original, compressed)
    
    # Quality classification
    if psnr > 40 and delta_e < 2.3 and ssim > 0.95:
        quality = "EXCELLENT"
    elif psnr > 30 and delta_e < 5.0 and ssim > 0.90:
        quality = "GOOD"
    elif psnr > 20 and delta_e < 10.0 and ssim > 0.80:
        quality = "ACCEPTABLE"
    else:
        quality = "POOR"
    
    return {
        "psnr": psnr,
        "delta_e": delta_e,
        "ssim": ssim,
        "edge_preservation": edge_pres,
        "quality": quality,
    }


def is_quality_acceptable(original: np.ndarray, compressed: np.ndarray, 
                          min_psnr: float = 35.0, max_delta_e: float = 3.0) -> bool:
    """Check if compressed quality is acceptable.

    Args:
        original: Original image
        compressed: Compressed image
        min_psnr: Minimum acceptable PSNR (default: 35dB)
        max_delta_e: Maximum acceptable ΔE (default: 3.0)

    Returns:
        True if quality is acceptable
    """
    quality = evaluate_quality(original, compressed)
    return quality["psnr"] >= min_psnr and quality["delta_e"] <= max_delta_e
