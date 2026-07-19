"""Test SmartCBCKEncoder basic functionality."""
from actool_linux.smart_cbck import SmartCBCKEncoder
import struct
import numpy as np


def test_smart_cbck_basic_encode():
    """Test that SmartCBCKEncoder can encode a simple image."""
    data = np.zeros((128, 128, 4), dtype=np.uint8)
    data[10:30, 10:30] = [255, 0, 0, 255]  # Red square (UI element)
    data[60:100, 60:100] = [0, 255, 0, 255]  # Green square (UI element)

    encoder = SmartCBCKEncoder(clean_alpha=True)
    encoded = encoder.encode(data.tobytes(), 128, 128)

    # Verify MLEC header
    assert encoded[:4] == b"MLEC"
    mode, codec, count = struct.unpack_from("<3I", encoded, 4)
    assert mode == 3
    assert codec == 4
    assert count >= 1


def test_smart_cbck_apple_parseable():
    """Test that SmartCBCKEncoder output is parseable by Apple's CBCK parser."""
    data = np.zeros((64, 64, 4), dtype=np.uint8)
    data[:32, :] = [200, 100, 50, 255]
    data[32:, :] = [0, 0, 0, 0]  # Transparent

    encoder = SmartCBCKEncoder(clean_alpha=True)
    encoded = encoder.encode(data.tobytes(), 64, 64)

    from actool_linux.cbck import parse_cbck
    parsed = parse_cbck(encoded)
    assert parsed.mode == 3
    assert parsed.codec == 4
    assert len(parsed.chunks) >= 1


def test_smart_cbck_transparency_cleaning():
    """Test that dirty transparency is cleaned (RGB zeroed where alpha=0)."""
    data = np.full((32, 32, 4), 128, dtype=np.uint8)  # Dirty: RGB=128 everywhere
    data[:, :, 3] = 0  # All transparent

    encoder = SmartCBCKEncoder(clean_alpha=True)
    encoded = encoder.encode(data.tobytes(), 32, 32)

    from actool_linux.cbck import parse_cbck
    from actool_linux import lzfse_compat

    parsed = parse_cbck(encoded)
    for chunk in parsed.chunks:
        decompressed = lzfse_compat.decompress(chunk.compressed)
        arr = np.frombuffer(decompressed, dtype=np.uint8).reshape(-1, 4)
        # All pixels are transparent, so RGB should be cleaned to 0
        assert np.all(arr[:, :3] == 0), "Dirty transparency not cleaned"
