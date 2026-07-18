from __future__ import annotations

from dataclasses import dataclass
import struct


MAGIC = 0xCAFEF00D
MAX_PALETTE_COLORS = 0x1000


@dataclass(frozen=True)
class ThemePixelRendition:
    version: int
    compression_type: int
    raw_data: bytes


@dataclass(frozen=True)
class QuantizedImageData:
    version: int
    palette: tuple[bytes, ...]  # ARGB entries (4 bytes each)
    indices: bytes              # one byte per pixel after unpacking
    bits_per_index: int


class PaletteImageError(ValueError):
    pass


def _bit_width(palette_count: int) -> int:
    if not 1 <= palette_count <= MAX_PALETTE_COLORS:
        raise PaletteImageError("palette color count is out of range")
    # Public quantized-image grammar stores indices at discrete widths; the
    # 105-color public Timac fixture confirms 17..256 colors use whole bytes.
    for bits in (1, 2, 4, 8):
        if palette_count <= (1 << bits):
            return bits
    return 12


def parse_theme_pixel_rendition(raw: bytes | bytearray | memoryview) -> ThemePixelRendition:
    data = bytes(raw)
    if len(data) < 16:
        raise PaletteImageError("theme pixel rendition is truncated")
    if data[:4] == b"MLEC":
        order = "<"
    elif data[:4] == b"CELM":
        order = ">"
    else:
        raise PaletteImageError("invalid theme pixel rendition magic")
    version, compression_type, raw_length = struct.unpack_from(order + "3I", data, 4)
    if raw_length > len(data) - 16:
        raise PaletteImageError("theme pixel rendition raw payload is truncated")
    return ThemePixelRendition(version, compression_type, data[16:16 + raw_length])


def _unpack_row_indices(data: bytes, width: int, bits_per_index: int) -> bytes:
    row_bytes = (width * bits_per_index + 7) // 8
    if len(data) % row_bytes:
        raise PaletteImageError("quantized index plane has an invalid row length")
    out = bytearray()
    mask = (1 << bits_per_index) - 1
    for row in range(0, len(data), row_bytes):
        buf = int.from_bytes(data[row:row + row_bytes], "big")
        total_bits = row_bytes * 8
        for x in range(width):
            shift = total_bits - bits_per_index * (x + 1)
            out.append((buf >> shift) & mask)
    return bytes(out)


def _pack_row_indices(indices: bytes, width: int, bits_per_index: int) -> bytes:
    row_bytes = (width * bits_per_index + 7) // 8
    if len(indices) % width:
        raise PaletteImageError("unpacked quantized indices are not width-aligned")
    out = bytearray()
    for row in range(0, len(indices), width):
        buf = 0
        total_bits = row_bytes * 8
        for x, value in enumerate(indices[row:row + width]):
            if value >= (1 << bits_per_index):
                raise PaletteImageError("quantized index exceeds bit width")
            shift = total_bits - bits_per_index * (x + 1)
            buf |= int(value) << shift
        out += buf.to_bytes(row_bytes, "big")
    return bytes(out)


def decode_quantized_image_payload(raw_data: bytes, *, width: int, height: int, pixel_format: str = "ARGB") -> QuantizedImageData:
    from . import lzfse_compat
    if pixel_format not in ("ARGB", "RGBW"):
        raise PaletteImageError(f"unsupported quantized pixel format: {pixel_format}")
    decoded = lzfse_compat.decompress(bytes(raw_data))
    if len(decoded) < 10:
        raise PaletteImageError("decoded quantized payload is truncated")
    magic, version = struct.unpack_from("<2I", decoded, 0)
    if magic != MAGIC:
        raise PaletteImageError("decoded quantized payload has an invalid magic")
    if version >= 2:
        raise PaletteImageError("decoded quantized payload version is unsupported")
    palette_count = struct.unpack_from("<H", decoded, 8)[0]
    if not 1 <= palette_count <= MAX_PALETTE_COLORS:
        raise PaletteImageError("decoded quantized payload palette count is invalid")
    entry_size = 8 if pixel_format == "RGBW" else 4
    palette_size = palette_count * entry_size
    palette_start = 10
    palette_end = palette_start + palette_size
    if palette_end > len(decoded):
        raise PaletteImageError("decoded quantized payload palette is truncated")
    bits = _bit_width(palette_count)
    index_plane = decoded[palette_end:]
    row_bytes = (width * bits + 7) // 8
    expected = row_bytes * height
    if len(index_plane) != expected:
        raise PaletteImageError("decoded quantized payload index plane length is invalid")
    palette = tuple(decoded[palette_start + i:palette_start + i + entry_size] for i in range(0, palette_size, entry_size))
    return QuantizedImageData(version, palette, _unpack_row_indices(index_plane, width, bits), bits)


def encode_quantized_image_payload(palette_argb: bytes, indices: bytes, *, width: int, height: int, version: int = 1) -> bytes:
    from . import lzfse_compat
    if version not in (0, 1):
        raise PaletteImageError("quantized payload version must be 0 or 1")
    if len(palette_argb) % 4:
        raise PaletteImageError("palette ARGB buffer length must be divisible by 4")
    palette_count = len(palette_argb) // 4
    bits = _bit_width(palette_count)
    if len(indices) != width * height:
        raise PaletteImageError("quantized index count does not match width*height")
    if any(index >= palette_count for index in indices):
        raise PaletteImageError("quantized index references a missing palette entry")
    packed_indices = _pack_row_indices(indices, width, bits)
    payload = struct.pack("<2IH", MAGIC, version, palette_count) + bytes(palette_argb) + packed_indices
    return lzfse_compat.compress(payload)


def build_palette_img_wrapper(palette_argb: bytes, indices: bytes, *, width: int, height: int, version: int = 1) -> bytes:
    compressed = encode_quantized_image_payload(palette_argb, indices, width=width, height=height, version=version)
    return b"MLEC" + struct.pack("<3I", 0, 8, len(compressed)) + compressed
