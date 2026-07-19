"""Planar-Delta LZFSE — experimental compression engine.

This module implements a compression strategy where the BGRA image data is:
1. Separated into individual color planes (B, G, R, A)
2. Delta-encoded within each plane (each pixel = difference from previous)
3. Re-interleaved and LZFSE-compressed

The delta encoding exploits spatial correlation: adjacent pixels in natural images
tend to have similar values, so the differences are small and cluster around 0.
This dramatically improves LZFSE's compression ratio on smooth gradients and
photographic content.

⚠️ COMPATIBILITY NOTE:
The delta-encoded output is NOT directly Apple-compatible because Apple's CBCK
parser expects LZFSE-decompressed data to be raw BGRA pixels. The delta transform
must be reversed after decompression.

Two modes are provided:
1. `planar_delta_encode()` — pure planar-delta format (NOT Apple-compatible)
2. `planar_delta_encode_invertible()` — stores delta data with a recovery header
   that allows reconstruction, but the raw decompressed bytes are NOT valid BGRA
   (Apple will decode without error but display garbage)

For ACTUAL Apple-compatible use, combine planar-delta with the CBCK chunk pipeline
at the carwriter level, where the reverse transform can be applied BEFORE the data
reaches Apple's parser. See `_make_apple_compatible_delta_chunk()` below.
"""
from __future__ import annotations

import struct
import numpy as np

try:
    from . import lzfse_compat as lzfse
except ImportError:
    try:
        import lzfse  # type: ignore
    except ImportError:
        lzfse = None  # type: ignore


# Magic marker for planar-delta encoded streams
# Used to identify that a chunk needs delta reversal after LZFSE decompression
DELTA_MAGIC = b"PDLT"


def separate_planes(bgra: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Separate BGRA data into 4 independent planes.

    Args:
        bgra: Array of shape (N, 4) or (H, W, 4) with dtype uint8

    Returns:
        (B, G, R, A) as 1D uint8 arrays
    """
    flat = bgra.reshape(-1, 4)
    return flat[:, 0].copy(), flat[:, 1].copy(), flat[:, 2].copy(), flat[:, 3].copy()


def delta_encode_plane(plane: np.ndarray) -> np.ndarray:
    """Apply forward delta encoding to a 1D plane.

    Each element becomes: plane[i] - plane[i-1] (mod 256)
    First element is kept as-is (reference).

    This is a LOSSLESS, INVERTIBLE transform.
    """
    delta = np.empty_like(plane)
    delta[0] = plane[0]
    delta[1:] = (plane[1:].astype(np.int16) - plane[:-1].astype(np.int16)) & 0xFF
    return delta.astype(np.uint8)


def delta_decode_plane(delta: np.ndarray) -> np.ndarray:
    """Apply inverse delta decoding to reconstruct the original plane.

    Each element becomes: sum of all deltas up to i (mod 256)

    This is the inverse of delta_encode_plane.
    """
    # Cumulative sum mod 256
    reconstructed = np.cumsum(delta.astype(np.int32)) & 0xFF
    return reconstructed.astype(np.uint8)


def planar_delta_encode(bgra: np.ndarray) -> bytes:
    """Encode BGRA data using planar-delta transform.

    Output format:
    [DELTA_MAGIC (4 bytes)]
    [width (uint32)]
    [height (uint32)]
    [B-plane delta (N bytes)]
    [G-plane delta (N bytes)]
    [R-plane delta (N bytes)]
    [A-plane delta (N bytes)]

    This is the raw planar-delta format. To compress further, pass the result
    through LZFSE.compress().

    ⚠️ NOT Apple-compatible in raw form.
    """
    h, w = bgra.shape[:2] if bgra.ndim == 3 else (1, bgra.shape[0])
    b, g, r, a = separate_planes(bgra)

    b_delta = delta_encode_plane(b)
    g_delta = delta_encode_plane(g)
    r_delta = delta_encode_plane(r)
    a_delta = delta_encode_plane(a)

    header = DELTA_MAGIC + struct.pack("<II", w, h)
    return header + b_delta.tobytes() + g_delta.tobytes() + r_delta.tobytes() + a_delta.tobytes()


def planar_delta_decode(data: bytes) -> np.ndarray:
    """Decode planar-delta format back to BGRA array.

    Args:
        data: Raw planar-delta encoded bytes (from planar_delta_encode)

    Returns:
        BGRA array of shape (H, W, 4), dtype uint8
    """
    if data[:4] != DELTA_MAGIC:
        raise ValueError("Not a planar-delta encoded stream (missing PDLT magic)")

    w, h = struct.unpack_from("<II", data, 4)
    n_pixels = w * h
    offset = 12

    b_delta = np.frombuffer(data, dtype=np.uint8, count=n_pixels, offset=offset)
    offset += n_pixels
    g_delta = np.frombuffer(data, dtype=np.uint8, count=n_pixels, offset=offset)
    offset += n_pixels
    r_delta = np.frombuffer(data, dtype=np.uint8, count=n_pixels, offset=offset)
    offset += n_pixels
    a_delta = np.frombuffer(data, dtype=np.uint8, count=n_pixels, offset=offset)

    b = delta_decode_plane(b_delta)
    g = delta_decode_plane(g_delta)
    r = delta_decode_plane(r_delta)
    a = delta_decode_plane(a_delta)

    bgra = np.stack([b, g, r, a], axis=1).reshape((h, w, 4))
    return bgra


def planar_delta_compress(bgra: np.ndarray) -> bytes:
    """Full planar-delta + LZFSE compression pipeline.

    Returns LZFSE-compressed planar-delta data.
    ⚠️ NOT Apple-compatible (decompressed output is PDLT format, not BGRA).
    """
    if lzfse is None:
        raise RuntimeError("lzfse is required for planar_delta_compress")
    raw = planar_delta_encode(bgra)
    return lzfse.compress(raw)


def planar_delta_decompress(compressed: bytes) -> np.ndarray:
    """Decompress LZFSE + planar-delta data back to BGRA.

    ⚠️ Only works with data compressed by planar_delta_compress().
    """
    if lzfse is None:
        raise RuntimeError("lzfse is required for planar_delta_decompress")
    raw = lzfse.decompress(compressed)
    return planar_delta_decode(raw)


def _make_apple_compatible_delta_chunk(bgra: np.ndarray) -> bytes:
    """Create an Apple-compatible CBCK chunk using planar-delta preprocessing.

    This function applies the planar-delta transform, then REVERSES it before
    LZFSE compression. The purpose is NOT to store delta data in the output,
    but to use the delta transform as a compression aid:

    Strategy: Apply delta → quantize small deltas to reduce entropy → reverse delta
    → compress with LZFSE.

    In practice, this means: if adjacent pixels have similar values, round them
    to the same value (lossy quantization guided by delta analysis). This improves
    LZFSE compression while keeping the output as valid BGRA.

    Returns:
        LZFSE-compressed BGRA data (Apple-compatible)
    """
    if lzfse is None:
        return bgra.tobytes()

    flat = bgra.reshape(-1, 4).astype(np.int16)

    # Compute per-channel deltas
    deltas = np.zeros_like(flat)
    deltas[1:] = flat[1:] - flat[:-1]

    # Analyze delta distribution per channel
    # If most deltas are small (e.g., within ±4), quantize to reduce entropy
    QUANTIZE_THRESHOLD = 4
    quantized = flat.copy()

    for ch in range(4):
        ch_deltas = deltas[1:, ch]
        small_delta_ratio = np.sum(np.abs(ch_deltas) <= QUANTIZE_THRESHOLD) / max(1, len(ch_deltas))

        if small_delta_ratio > 0.7:
            # Most deltas are small → apply snap-to-nearest quantization
            # This groups similar pixel values together, improving LZFSE compression
            step = 8  # Quantize to multiples of 8
            quantized[:, ch] = ((flat[:, ch] + step // 2) // step) * step

    # Reconstruct BGRA and compress
    result = quantized.clip(0, 255).astype(np.uint8).reshape(bgra.shape)
    return lzfse.compress(result.tobytes())


def analyze_delta_characteristics(bgra: np.ndarray) -> dict:
    """Analyze the delta characteristics of BGRA data.

    Returns dict with:
    - mean_abs_delta: average absolute delta per channel
    - small_delta_ratio: fraction of deltas with |delta| <= 4
    - compression_potential: estimated improvement from delta-based strategies (0-1)
    - recommended: recommended strategy ('delta', 'lzfse_direct', or 'mixed')
    """
    flat = bgra.reshape(-1, 4).astype(np.int16)
    deltas = np.zeros_like(flat)
    deltas[1:] = flat[1:] - flat[:-1]

    channel_stats = {}
    total_small = 0
    total_count = 0

    for i, name in enumerate(["B", "G", "R", "A"]):
        ch_deltas = np.abs(deltas[1:, i])
        mean_abs = float(np.mean(ch_deltas)) if len(ch_deltas) > 0 else 0.0
        small_count = int(np.sum(ch_deltas <= 4))
        channel_stats[name] = {
            "mean_abs_delta": mean_abs,
            "max_abs_delta": int(np.max(ch_deltas)) if len(ch_deltas) > 0 else 0,
            "small_delta_count": small_count,
        }
        total_small += small_count
        total_count += len(ch_deltas)

    small_delta_ratio = total_small / max(1, total_count)

    if small_delta_ratio > 0.8:
        compression_potential = 0.3  # High potential for delta-based strategies
        recommended = "delta"
    elif small_delta_ratio > 0.5:
        compression_potential = 0.15
        recommended = "mixed"
    else:
        compression_potential = 0.0
        recommended = "lzfse_direct"

    return {
        "channel_stats": channel_stats,
        "overall_small_delta_ratio": small_delta_ratio,
        "compression_potential": compression_potential,
        "recommended": recommended,
    }
