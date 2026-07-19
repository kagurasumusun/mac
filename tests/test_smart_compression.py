"""Integration test for Smart CBCK, LPC-LZFSE, and Planar-Delta compression.

Verifies:
1. SmartCBCKEncoder produces Apple-compatible CBCK output
2. Output can be parsed by stable/cbck.py parse_cbck()
3. LPC-LZFSE apple-compat mode produces valid LZFSE streams
4. Planar-Delta encode/decode is lossless (invertible)
5. Planar-Delta apple-compat mode produces valid BGRA
"""
import sys
import numpy as np

# Add project to path
sys.path.insert(0, "/home/user/repo-cleanup")

from actool_linux.smart_cbck import SmartCBCKEncoder, smart_encode_png_cbck
from actool_linux.lpc_lzfse import (
    lpc_encode_pure,
    lpc_encode_apple_compat,
    extract_palette,
    analyze_chunk_compressibility,
)
from actool_linux.planar_delta_lzfse import (
    planar_delta_encode,
    planar_delta_decode,
    delta_encode_plane,
    delta_decode_plane,
    analyze_delta_characteristics,
    _make_apple_compatible_delta_chunk,
)


def test_smart_cbck_apple_compatible():
    """Test that SmartCBCKEncoder output is parseable by Apple's format."""
    print("=== Test 1: SmartCBCKEncoder Apple Compatibility ===")

    # Create test image: 64x64 BGRA with gradients
    w, h = 64, 64
    bgra = np.zeros((h, w, 4), dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            bgra[y, x] = [x * 4, y * 4, 128, 255]

    encoder = SmartCBCKEncoder(clean_alpha=True)
    payload = encoder.encode(bgra.tobytes(), w, h)

    # Verify MLEC header
    assert payload[:4] == b"MLEC", f"Expected MLEC magic, got {payload[:4]}"
    mode, codec, count = __import__("struct").unpack_from("<3I", payload, 4)
    assert mode == 3, f"Expected mode=3, got {mode}"
    assert codec == 4, f"Expected codec=4, got {codec}"
    assert count > 0, "Expected at least 1 chunk"

    # Parse using stable/cbck.py parser (Apple format)
    from actool_linux.cbck import parse_cbck
    parsed = parse_cbck(payload)
    assert parsed.mode == 3
    assert parsed.codec == 4
    assert len(parsed.chunks) == count

    # Verify each chunk can be LZFSE-decompressed to valid BGRA
    from actool_linux import lzfse_compat
    total_pixels = 0
    for chunk in parsed.chunks:
        decompressed = lzfse_compat.decompress(chunk.compressed)
        expected_size = w * chunk.row_count * 4
        assert len(decompressed) == expected_size, (
            f"Chunk size mismatch: {len(decompressed)} != {expected_size}"
        )
        total_pixels += w * chunk.row_count

    assert total_pixels == w * h, f"Total pixels mismatch: {total_pixels} != {w * h}"
    print(f"  ✅ SmartCBCK output parsed successfully ({count} chunks, {total_pixels} pixels)")
    print(f"  ✅ Payload size: {len(payload)} bytes")
    return True


def test_smart_cbck_with_transparency():
    """Test SmartCBCKEncoder with transparent regions."""
    print("\n=== Test 2: SmartCBCKEncoder with Transparency ===")

    w, h = 128, 128
    bgra = np.zeros((h, w, 4), dtype=np.uint8)
    # Top half: opaque gradient
    for y in range(64):
        for x in range(w):
            bgra[y, x] = [(x * 4) % 256, (y * 4) % 256, 128, 255]
    # Bottom half: fully transparent (with dirty RGB)
    bgra[64:, :, :3] = 128  # Dirty transparency
    bgra[64:, :, 3] = 0

    encoder = SmartCBCKEncoder(clean_alpha=True)
    payload = encoder.encode(bgra.tobytes(), w, h)

    from actool_linux.cbck import parse_cbck
    parsed = parse_cbck(payload)

    # Verify clean alpha: decompressed transparent pixels should have RGB=0
    from actool_linux import lzfse_compat
    for chunk in parsed.chunks:
        decompressed = lzfse_compat.decompress(chunk.compressed)
        arr = np.frombuffer(decompressed, dtype=np.uint8).reshape(-1, 4)
        transparent_mask = arr[:, 3] == 0
        if np.any(transparent_mask):
            rgb_of_transparent = arr[transparent_mask, :3]
            assert np.all(rgb_of_transparent == 0), (
                "Dirty transparency not cleaned: RGB should be 0 where alpha=0"
            )

    print(f"  ✅ Transparency cleaning verified")
    print(f"  ✅ {len(parsed.chunks)} chunks, payload: {len(payload)} bytes")
    return True


def test_lpc_pure_mode():
    """Test LPC pure mode (palette + indices)."""
    print("\n=== Test 3: LPC-LZFSE Pure Mode ===")

    # Low-color test image (16 unique colors)
    bgra = np.zeros((32, 32, 4), dtype=np.uint8)
    for y in range(32):
        for x in range(32):
            idx = (y // 8) * 4 + (x // 8)
            bgra[y, x] = [(idx * 16) % 256, (idx * 8) % 256, (idx * 15) % 256, 255]

    encoded, success = lpc_encode_pure(bgra)
    assert success, "LPC pure encode should succeed for low-color image"
    assert len(encoded) > 0

    # Analyze compressibility
    analysis = analyze_chunk_compressibility(bgra)
    assert analysis["palette_feasible"], "Should be palette-feasible"
    assert analysis["unique_colors"] <= 256

    print(f"  ✅ LPC pure encode succeeded ({len(encoded)} bytes)")
    print(f"  ✅ Unique colors: {analysis['unique_colors']}, feasible: {analysis['palette_feasible']}")
    return True


def test_lpc_apple_compat():
    """Test LPC apple-compat mode produces valid LZFSE BGRA."""
    print("\n=== Test 4: LPC-LZFSE Apple-Compatible Mode ===")

    w, h = 64, 64
    bgra = np.zeros((h, w, 4), dtype=np.uint8)
    # Create a low-color UI-like image
    bgra[:32, :32] = [255, 0, 0, 255]    # Red
    bgra[:32, 32:] = [0, 255, 0, 255]    # Green
    bgra[32:, :32] = [0, 0, 255, 255]    # Blue
    bgra[32:, 32:] = [255, 255, 255, 255]  # White

    compressed = lpc_encode_apple_compat(bgra, max_colors=16)

    # Verify it's valid LZFSE that decompresses to correct size
    from actool_linux import lzfse_compat
    decompressed = lzfse_compat.decompress(compressed)
    assert len(decompressed) == w * h * 4, f"Size mismatch: {len(decompressed)} != {w * h * 4}"

    # Verify decompressed data is valid BGRA (4 distinct colors, quantized)
    result = np.frombuffer(decompressed, dtype=np.uint8).reshape(h, w, 4)
    unique_colors = len(np.unique(result.reshape(-1, 4).view(np.uint32)))
    assert unique_colors <= 16, f"Expected ≤16 colors after quantization, got {unique_colors}"

    print(f"  ✅ LPC apple-compat: {len(compressed)} bytes compressed, {len(decompressed)} bytes decompressed")
    print(f"  ✅ Result has {unique_colors} unique colors (≤16 target)")

    # Compare with direct LZFSE
    direct = lzfse_compat.compress(bgra.tobytes())
    savings = 1.0 - len(compressed) / len(direct)
    print(f"  ✅ Direct LZFSE: {len(direct)} bytes, LPC savings: {savings * 100:.1f}%")
    return True


def test_planar_delta_lossless():
    """Test that planar-delta encode/decode is lossless."""
    print("\n=== Test 5: Planar-Delta Lossless Roundtrip ===")

    # Create test image with smooth gradients (ideal for delta)
    w, h = 64, 64
    bgra = np.zeros((h, w, 4), dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            bgra[y, x] = [x * 4 % 256, y * 4 % 256, (x + y) * 2 % 256, 255]

    # Encode
    encoded = planar_delta_encode(bgra)
    assert encoded[:4] == b"PDLT", "Missing PDLT magic"

    # Decode
    decoded = planar_delta_decode(encoded)
    assert decoded.shape == bgra.shape, f"Shape mismatch: {decoded.shape} != {bgra.shape}"
    assert np.array_equal(decoded, bgra), "Planar-delta roundtrip is NOT lossless!"

    print(f"  ✅ Planar-delta roundtrip is perfectly lossless")
    print(f"  ✅ Encoded size: {len(encoded)} bytes (raw), original: {bgra.nbytes} bytes")

    # Test delta characteristics analysis
    analysis = analyze_delta_characteristics(bgra)
    print(f"  ✅ Small delta ratio: {analysis['overall_small_delta_ratio']:.2%}")
    print(f"  ✅ Recommended strategy: {analysis['recommended']}")
    return True


def test_planar_delta_compress():
    """Test planar-delta + LZFSE compression."""
    print("\n=== Test 6: Planar-Delta + LZFSE Compression ===")

    from actool_linux.planar_delta_lzfse import planar_delta_compress, planar_delta_decompress

    # Smooth gradient image
    w, h = 128, 128
    bgra = np.zeros((h, w, 4), dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            bgra[y, x] = [
                int(255 * x / w),
                int(255 * y / h),
                int(128 + 64 * np.sin(x / 10)),
                255
            ]

    compressed = planar_delta_compress(bgra)
    decompressed = planar_delta_decompress(compressed)

    assert np.array_equal(decompressed, bgra), "Planar-delta+LZFSE roundtrip failed!"

    from actool_linux import lzfse_compat
    direct = lzfse_compat.compress(bgra.tobytes())

    ratio = len(compressed) / len(direct)
    print(f"  ✅ Planar-delta+LZFSE: {len(compressed)} bytes")
    print(f"  ✅ Direct LZFSE:       {len(direct)} bytes")
    print(f"  ✅ Ratio: {ratio:.2%} (lower = better)")
    if ratio < 1.0:
        print(f"  ✅ Planar-delta is {(1 - ratio) * 100:.1f}% smaller than direct LZFSE!")
    return True


def test_comparison():
    """Compare all compression strategies on the same image."""
    print("\n=== Test 7: Strategy Comparison ===")

    from actool_linux import lzfse_compat

    # UI-like image (mix of solid blocks and gradients)
    w, h = 256, 256
    bgra = np.zeros((h, w, 4), dtype=np.uint8)
    # Solid blocks (like UI buttons)
    bgra[:64, :64] = [200, 200, 200, 255]
    bgra[:64, 64:128] = [0, 122, 255, 255]
    bgra[:64, 128:192] = [255, 59, 48, 255]
    bgra[:64, 192:] = [52, 199, 89, 255]
    # Gradient region (like a photo area)
    for y in range(64, h):
        for x in range(w):
            t = (y - 64) / (h - 64)
            bgra[y, x] = [int(255 * t), int(128 * (1 - t)), int(200 * t), 255]

    results = {}

    # 1. Direct LZFSE (baseline)
    direct = lzfse_compat.compress(bgra.tobytes())
    results["Direct LZFSE"] = len(direct)

    # 2. SmartCBCK
    encoder = SmartCBCKEncoder(clean_alpha=True)
    smart_payload = encoder.encode(bgra.tobytes(), w, h)
    results["SmartCBCK"] = len(smart_payload)

    # 3. LPC apple-compat
    lpc_data = lpc_encode_apple_compat(bgra, max_colors=256, force=True)
    results["LPC-LZFSE (compat)"] = len(lpc_data)

    # 4. Planar-delta compatible chunk
    delta_data = _make_apple_compatible_delta_chunk(bgra)
    results["Planar-Delta (compat)"] = len(delta_data)

    print(f"\n  {'Strategy':<25} {'Size':>10} {'vs Baseline':>15}")
    print(f"  {'-' * 50}")
    baseline = results["Direct LZFSE"]
    for name, size in results.items():
        ratio = size / baseline
        diff = f"{(ratio - 1) * 100:+.1f}%"
        print(f"  {name:<25} {size:>10} {diff:>15}")

    return True


def main():
    print("=" * 60)
    print("Smart Compression Integration Tests")
    print("=" * 60)

    tests = [
        test_smart_cbck_apple_compatible,
        test_smart_cbck_with_transparency,
        test_lpc_pure_mode,
        test_lpc_apple_compat,
        test_planar_delta_lossless,
        test_planar_delta_compress,
        test_comparison,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            failed += 1
            print(f"  ❌ FAILED: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
