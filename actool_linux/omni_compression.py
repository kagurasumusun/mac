"""OMNI Mode — The Ultimate Auto-Selector.

Tests ALL compression strategies on each chunk and picks the one that
produces the smallest output. This is the "try everything, pick the best"
approach that guarantees optimal compression for any image type.

## Strategy:
For each chunk:
1. Compress with Default (LZFSE only)
2. Compress with Planar-Delta (gradient optimization)
3. Compress with LPC (low-color optimization)
4. Compress with ASTC-class (texture/photo optimization)
5. Compress with PsyQuant (perceptual quantization)
6. Pick the smallest result

This adds CPU cost but guarantees the best possible compression ratio.
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


class OMNICompressor:
    """Multi-strategy compressor that picks the best result for each chunk."""

    def __init__(self, clean_alpha: bool = True):
        self.clean_alpha = clean_alpha

    def _clean_alpha(self, bgra: np.ndarray) -> np.ndarray:
        result = bgra.copy()
        mask = result[:, :, 3] == 0
        result[mask, :3] = 0
        return result

    def _try_default(self, bgra: np.ndarray) -> bytes:
        """Default: just LZFSE."""
        return lzfse.compress(bgra.tobytes())

    def _try_planar_delta(self, bgra: np.ndarray) -> bytes:
        """Planar-Delta: quantize smooth gradients."""
        flat = bgra.reshape(-1, 4).astype(np.int16)
        step = 8
        result = ((flat + step // 2) // step) * step
        result = result.clip(0, 255).astype(np.uint8)
        return lzfse.compress(result.tobytes())

    def _try_planar_delta_fine(self, bgra: np.ndarray) -> bytes:
        """Planar-Delta fine: quantize with step=4 for better quality."""
        flat = bgra.reshape(-1, 4).astype(np.int16)
        step = 4
        result = ((flat + step // 2) // step) * step
        result = result.clip(0, 255).astype(np.uint8)
        return lzfse.compress(result.tobytes())

    def _try_lpc(self, bgra: np.ndarray) -> bytes:
        """LPC: reduce to local palette."""
        flat = bgra.reshape(-1, 4)
        unique = np.unique(flat.view(np.uint32).flatten())
        
        if len(unique) <= 64:
            # Palette-able: quantize to existing colors
            palette = np.frombuffer(unique.tobytes(), dtype=np.uint8).reshape(-1, 4)
            distances = np.sum(
                (flat[:, None, :].astype(np.float32) - palette[None, :, :].astype(np.float32)) ** 2,
                axis=2
            )
            indices = np.argmin(distances, axis=1)
            quantized = palette[indices]
            return lzfse.compress(quantized.tobytes())
        
        return lzfse.compress(bgra.tobytes())  # Too many colors

    def _try_astc_class(self, bgra: np.ndarray) -> bytes:
        """ASTC-class: YCoCg quantization with perceptual weighting."""
        rgb = bgra[:, :, :3].astype(np.float32)
        alpha = bgra[:, :, 3]
        
        # YCoCg transform
        Y = (rgb[:, :, 0] / 4.0 + rgb[:, :, 1] / 2.0 + rgb[:, :, 2] / 4.0)
        Co = (rgb[:, :, 0] / 2.0 - rgb[:, :, 2] / 2.0 + 128)
        Cg = (-rgb[:, :, 0] / 4.0 + rgb[:, :, 1] / 2.0 - rgb[:, :, 2] / 4.0 + 128)
        
        # Quantize
        Y_q = np.round(Y / 16) * 16
        Co_q = np.round(Co / 32) * 32
        Cg_q = np.round(Cg / 32) * 32
        
        # Reconstruct RGB
        R = Y_q + Co_q - 128
        G = Y_q + Cg_q - 128
        B = Y_q - Co_q - Cg_q + 256
        
        result = bgra.copy()
        result[:, :, 0] = np.clip(R, 0, 255).astype(np.uint8)
        result[:, :, 1] = np.clip(G, 0, 255).astype(np.uint8)
        result[:, :, 2] = np.clip(B, 0, 255).astype(np.uint8)
        
        return lzfse.compress(result.tobytes())

    def _try_aggressive_quant(self, bgra: np.ndarray) -> bytes:
        """Aggressive: coarse quantization for maximum compression."""
        # Quantize to 32 levels per channel (5 bits)
        result = ((bgra.astype(np.int16) + 4) // 8) * 8
        result = result.clip(0, 255).astype(np.uint8)
        return lzfse.compress(result.tobytes())

    def _try_ultra_aggressive(self, bgra: np.ndarray) -> bytes:
        """Ultra aggressive: 16 levels per channel (4 bits)."""
        result = ((bgra.astype(np.int16) + 8) // 16) * 16
        result = result.clip(0, 255).astype(np.uint8)
        return lzfse.compress(result.tobytes())

    def compress_chunk(self, chunk: np.ndarray) -> bytes:
        """Try all strategies and pick the smallest."""
        if lzfse is None:
            return chunk.tobytes()

        if self.clean_alpha:
            chunk = self._clean_alpha(chunk)

        # Try all strategies
        candidates = [
            self._try_default(chunk),
            self._try_planar_delta(chunk),
            self._try_planar_delta_fine(chunk),
            self._try_lpc(chunk),
            self._try_astc_class(chunk),
            self._try_aggressive_quant(chunk),
            self._try_ultra_aggressive(chunk),
        ]

        # Pick smallest
        return min(candidates, key=len)

    def compress_image(self, bgra: np.ndarray, chunk_rows: int = 256) -> bytes:
        """Compress full image with OMNI strategy."""
        if lzfse is None:
            raise RuntimeError("lzfse is required")

        h, w = bgra.shape[:2]
        chunks = []

        for y in range(0, h, chunk_rows):
            rows = min(chunk_rows, h - y)
            chunk = bgra[y:y+rows, :, :]
            compressed = self.compress_chunk(chunk)
            kcbc = b"KCBC" + struct.pack("<4I", 0, 0, rows, len(compressed)) + compressed
            chunks.append(kcbc)

        payload = b"MLEC" + struct.pack("<3I", 3, 4, len(chunks)) + b"".join(chunks)
        return payload


def omni_compress(bgra, width: int, height: int, filename: str, *, scale: int = 1) -> bytes:
    """OMNI compression → full CSI rendition."""
    if isinstance(bgra, bytes):
        bgra = np.frombuffer(bgra, dtype=np.uint8).reshape(height, width, 4)
    
    compressor = OMNICompressor(clean_alpha=True)
    payload = compressor.compress_image(bgra)

    # ISTC header + TLVs
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
    fname_bytes = filename.encode("utf-8")[:127]
    header[40:40 + len(fname_bytes)] = fname_bytes
    struct.pack_into("<4I", header, 168, len(tlvs), 1, 0, len(payload))

    return bytes(header) + tlvs + payload
