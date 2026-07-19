"""Smart CBCK Encoder — Apple-compatible optimized bitmap compression.

This module implements an intelligent CBCK encoder that:
1. Uses AI (Micro-NN) to analyze chunk entropy and choose optimal compression strategy
2. Applies row-based chunking (Apple-compatible format)
3. Optionally uses pre-processing (alpha cleaning, color simplification) to improve compression
4. Outputs valid Apple CBCK format (MLEC mode=3, codec=4 with KCBC chunks)

The output is byte-compatible with Apple's assetutil / CoreUI parser.
"""
from __future__ import annotations
import struct
import json
import numpy as np
from pathlib import Path

try:
    from . import lzfse_compat as lzfse
except ImportError:
    try:
        import lzfse  # type: ignore
    except ImportError:
        lzfse = None  # type: ignore


# Apple's observed chunk raw-cap (from carwriter.py): 0x155555 bytes
APPLE_CBCK_RAW_CAP = 0x155555


class SmartCBCKEncoder:
    """Apple-compatible smart CBCK encoder with AI-driven chunk optimization.

    Unlike the experimental QuadTree variant, this encoder produces output
    that is fully parseable by Apple's CoreUI stack (stable/cbck.py parse_cbck).
    """

    # Strategy constants
    STRATEGY_LZFSE = 0       # Standard LZFSE compression
    STRATEGY_CLEAN_ALPHA = 1 # Clean dirty transparency then LZFSE
    STRATEGY_AGGRESSIVE = 2  # Color simplification + LZFSE

    def __init__(self, clean_alpha: bool = True, chunk_raw_cap: int = APPLE_CBCK_RAW_CAP):
        """Initialize the smart encoder.

        Args:
            clean_alpha: If True, zero out RGB in fully-transparent pixels (improves compression)
            chunk_raw_cap: Maximum raw bytes per chunk (Apple uses ~0x155555)
        """
        self.clean_alpha = clean_alpha
        self.chunk_raw_cap = chunk_raw_cap
        self._load_ai_model()

    def _load_ai_model(self) -> None:
        """Load the micro-AI model weights for strategy prediction."""
        try:
            weights_path = Path(__file__).resolve().parent.parent / "data" / "micro_ai_weights.json"
            with open(weights_path, "r") as f:
                w = json.load(f)
            self._W1 = np.array(w["W1"], dtype=np.float32)
            self._b1 = np.array(w["b1"], dtype=np.float32)
            self._W2 = np.array(w["W2"], dtype=np.float32)
            self._b2 = np.array(w["b2"], dtype=np.float32)
            self.ai_ready = True
        except Exception:
            self.ai_ready = False

    def _predict_strategy(self, chunk_bgra: bytes, width: int, height: int) -> int:
        """Predict the optimal compression strategy for a chunk using the micro-AI.

        Features extracted:
        - alpha_zero_ratio: fraction of fully-transparent pixels
        - unique_color_ratio: estimated color diversity (sampled)
        - edge_density: simple gradient magnitude

        Returns:
            Strategy constant (STRATEGY_LZFSE, STRATEGY_CLEAN_ALPHA, or STRATEGY_AGGRESSIVE)
        """
        total_pixels = width * height
        if total_pixels == 0:
            return self.STRATEGY_LZFSE

        arr = np.frombuffer(chunk_bgra, dtype=np.uint8).reshape((height, width, 4))

        # Feature 1: alpha zero ratio
        alpha_zero_ratio = float(np.sum(arr[:, :, 3] == 0)) / total_pixels

        # Feature 2: unique color ratio (sampled for speed)
        sample_step = max(1, total_pixels // 256)
        sample = arr.reshape(-1, 4)[::sample_step]
        unique_colors = len(np.unique(sample.view(np.uint32).flatten()))
        unique_color_ratio = min(1.0, unique_colors / max(1, len(sample)))

        # Feature 3: edge density (simple horizontal diff)
        gray = arr[:, :, :3].mean(axis=2).astype(np.float32)
        if width > 1:
            edge_density = float(np.sum(np.abs(np.diff(gray, axis=1)))) / (total_pixels * 255)
        else:
            edge_density = 0.0

        if not self.ai_ready:
            # Fallback heuristics when AI model is not available
            if alpha_zero_ratio > 0.8:
                return self.STRATEGY_CLEAN_ALPHA
            if unique_color_ratio < 0.05:
                return self.STRATEGY_AGGRESSIVE
            return self.STRATEGY_LZFSE

        # Neural network inference: 3 features → hidden(16, ReLU) → 3 outputs
        X = np.array([alpha_zero_ratio, unique_color_ratio, edge_density], dtype=np.float32)
        z1 = X @ self._W1 + self._b1
        a1 = np.maximum(0, z1)  # ReLU
        z2 = a1 @ self._W2 + self._b2
        return int(np.argmax(z2))

    @staticmethod
    def _clean_dirty_transparency(bgra: bytearray) -> bytearray:
        """Zero out RGB channels where alpha is 0.

        This is a lossless optimization: transparent pixels' RGB values don't
        affect rendering, so setting them to 0 improves LZFSE compression.
        Apple's own tools perform this normalization.
        """
        arr = np.frombuffer(bgra, dtype=np.uint8).reshape(-1, 4)
        mask = arr[:, 3] == 0
        arr[mask, 0:3] = 0
        return bytearray(arr.tobytes())

    def _compute_rows_per_chunk(self, width: int, height: int) -> list[tuple[int, int]]:
        """Compute optimal row-based chunking respecting Apple's raw cap.

        Returns list of (y_offset, row_count) tuples.
        """
        row_bytes = width * 4
        rows_per = max(1, self.chunk_raw_cap // row_bytes)

        bands: list[tuple[int, int]] = []
        y = 0
        while y < height:
            rows = min(rows_per, height - y)
            bands.append((y, rows))
            y += rows
        return bands

    def encode_chunk(
        self,
        bgra_data: bytes,
        width: int,
        height: int,
        y_offset: int = 0,
        rows: int | None = None,
    ) -> bytes:
        """Encode a single row-band chunk into Apple-compatible KCBC format.

        Args:
            bgra_data: BGRA pixel data for the chunk (width * rows * 4 bytes)
            width: Image width in pixels
            height: Not used directly (rows is the chunk height)
            y_offset: Y offset of this chunk in the full image
            rows: Number of rows in this chunk

        Returns:
            KCBC chunk bytes (magic + header + LZFSE stream)
        """
        if rows is None:
            rows = len(bgra_data) // (width * 4)

        chunk = bytearray(bgra_data)

        if self.clean_alpha:
            chunk = self._clean_dirty_transparency(chunk)

        # Apply AI-predicted strategy
        strategy = self._predict_strategy(bytes(chunk), width, rows)

        if strategy == self.STRATEGY_AGGRESSIVE:
            # Additional color simplification: reduce precision of near-identical colors
            # This is lossy but perceptually negligible for low-entropy regions
            arr = np.frombuffer(chunk, dtype=np.uint8).reshape(-1, 4)
            # Round RGB to nearest 4 (loses 2 bits per channel — acceptable for low-entropy)
            arr[:, 0] = (arr[:, 0] >> 2) << 2
            arr[:, 1] = (arr[:, 1] >> 2) << 2
            arr[:, 2] = (arr[:, 2] >> 2) << 2
            chunk = bytearray(arr.tobytes())

        # Compress with LZFSE (Apple-compatible)
        compressed = lzfse.compress(bytes(chunk))

        # Build KCBC chunk: magic(4) + reserved0(4) + reserved1(4) + rows(4) + length(4) + data
        return (
            b"KCBC"
            + struct.pack("<4I", 0, 0, rows, len(compressed))
            + compressed
        )

    def encode(self, bgra_data: bytes, width: int, height: int) -> bytes:
        """Encode a full BGRA image into Apple-compatible CBCK payload.

        Args:
            bgra_data: Full BGRA pixel data (width * height * 4 bytes)
            width: Image width
            height: Image height

        Returns:
            Complete MLEC payload (mode=3, codec=4) with KCBC chunks
        """
        if lzfse is None:
            raise RuntimeError("lzfse is required for SmartCBCKEncoder")

        bands = self._compute_rows_per_chunk(width, height)
        row_bytes = width * 4

        chunks: list[bytes] = []
        for y, rows in bands:
            offset = y * row_bytes
            chunk_data = bgra_data[offset:offset + rows * row_bytes]
            kcbc = self.encode_chunk(chunk_data, width, height, y_offset=y, rows=rows)
            chunks.append(kcbc)

        payload = b"MLEC" + struct.pack("<3I", 3, 4, len(chunks)) + b"".join(chunks)
        return payload


def smart_encode_png_cbck(
    bgra_premultiplied: bytes,
    width: int,
    height: int,
    filename: str,
    *,
    scale: int = 1,
    clean_alpha: bool = True,
) -> bytes:
    """High-level function: encode BGRA data into a complete CSI rendition with smart CBCK.

    This is the drop-in replacement for carwriter._csi_png_cbck() when --optimize=smart is active.

    Args:
        bgra_premultiplied: Premultiplied BGRA pixel data
        width: Image width
        height: Image height
        filename: Rendition filename (for ISTC header)
        scale: Display scale factor
        clean_alpha: Whether to clean dirty transparency

    Returns:
        Complete CSI bytes (ISTC header + TLVs + MLEC payload)
    """
    encoder = SmartCBCKEncoder(clean_alpha=clean_alpha)
    payload = encoder.encode(bgra_premultiplied, width, height)

    # Build ISTC header + TLVs (same structure as _csi_png_cbck)
    tlvs = b"".join((
        struct.pack("<2I5I", 1001, 20, 1, 0, 0, width, height),
        struct.pack("<2I7I", 1003, 28, 1, 0, 0, 0, 0, width, height),
        struct.pack("<2I8s", 1004, 8, b"\0\0\0\0\0\0\x80?"),
        struct.pack("<2II", 1006, 4, 1),
        struct.pack("<2II", 1007, 4, width * 4),
    ))

    header = bytearray(184)
    header[:4] = b"ISTC"
    struct.pack_into("<5I", header, 4, 1, 0, width, height, scale * 100)
    header[24:28] = b"BGRA"
    struct.pack_into("<I", header, 28, 1)
    struct.pack_into("<I2H", header, 32, 0, 12, 0)

    # Filename field (128 bytes, null-padded)
    fname_bytes = filename.encode("utf-8")[:127]
    header[40:40 + len(fname_bytes)] = fname_bytes

    struct.pack_into("<4I", header, 168, len(tlvs), 1, 0, len(payload))
    return bytes(header) + tlvs + payload
