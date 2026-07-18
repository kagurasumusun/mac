"""Single LZFSE entry point for the clean-room writer.

Every encoder/decoder in ``actool_linux`` goes through this module so the
project works in two modes:

1. Preferred: the optional third-party ``lzfse`` C extension (available on
   Linux and macOS via ``pip install lzfse``) provides the real encoder and
   decoder, byte-comparable with Apple platform output behaviour.
2. Fallback: a tiny built-in codec that emits *valid* LZFSE streams made only
   of uncompressed ``bvxn`` blocks terminated by the ``bvx-`` end-of-stream
   marker. Any conformant LZFSE decoder (including Apple's
   libcompression/CoreUI stack) accepts these blocks, so the CAR files remain
   fully readable by ``assetutil``/AppKit/UIKit; they are just larger than
   entropy-coded output.

The fallback decompressor decodes ``bvxn`` blocks (its own output) and raises
a clear error for entropy-coded ``bvx1``/``bvx2`` blocks, which need the C
extension. This keeps every failure explicit instead of silently truncating
upstream-produced streams.

Block layout (from the public LZFSE format description):

- ``bvxn`` u32 n_raw_bytes, u32 n_payload_bytes, then payload bytes
  (for uncompressed blocks n_raw_bytes == n_payload_bytes).
- ``bvx-`` end of stream.

Keeping this indirection in one module is deliberate: if Apple ships a new
compression codec in a future CoreUI, exactly one file changes.
"""
from __future__ import annotations

import struct

_UNCOMPRESSED_MAGIC = b"bvxn"
_END_OF_STREAM_MAGIC = b"bvx-"
_COMPRESSED_MAGICS = (b"bvx1", b"bvx2", b"bvx$")

# Conservative per-block cap for fallback uncompressed blocks. Well under any
# consumer-imposed block limit and keeps memory spikes bounded.
FALLBACK_BLOCK_CAP = 1 << 20


def _c_extension():
    try:
        import lzfse  # type: ignore
        return lzfse
    except ImportError:
        return None


def have_c_extension() -> bool:
    return _c_extension() is not None


def is_valid_stream(data: bytes) -> bool:
    """Cheap structural check usable without the C extension."""
    if len(data) < 4:
        return False
    cursor = 0
    while cursor + 4 <= len(data):
        magic = data[cursor:cursor + 4]
        if magic == _END_OF_STREAM_MAGIC:
            return True
        if magic == _UNCOMPRESSED_MAGIC:
            if cursor + 12 > len(data):
                return False
            payload = struct.unpack_from("<I", data, cursor + 8)[0]
            if payload > len(data) - cursor - 12:
                # LZFSE pads streams to an 8-byte boundary after a partial
                # final block; tolerate small forward overruns only via the
                # end marker search below.
                tail = data.find(_END_OF_STREAM_MAGIC, cursor + 12)
                return tail >= 0 and tail + 4 <= len(data)
            cursor += 12 + payload
            continue
        if magic in _COMPRESSED_MAGICS:
            # Full validation requires decoding; accept the magic and let the
            # decompressor do the real work.
            return True
        return False
    return False


def compress(data: bytes) -> bytes:
    """Compress ``data`` to an LZFSE stream (never fails)."""
    module = _c_extension()
    if module is not None:
        return module.compress(data)
    out = bytearray()
    for offset in range(0, len(data), FALLBACK_BLOCK_CAP):
        chunk = data[offset:offset + FALLBACK_BLOCK_CAP]
        out += _UNCOMPRESSED_MAGIC + struct.pack("<2I", len(chunk), len(chunk)) + chunk
    out += _END_OF_STREAM_MAGIC
    return bytes(out)


def decompress(data: bytes) -> bytes:
    """Decode an LZFSE stream.

    With the C extension this decodes every valid stream. Without it, only
    streams made of uncompressed blocks (as produced by :func:`compress` in
    fallback mode) are supported.
    """
    module = _c_extension()
    if module is not None:
        return module.decompress(data)
    out = bytearray()
    cursor = 0
    while cursor < len(data):
        if cursor + 4 > len(data):
            raise ValueError("LZFSE stream is truncated before end-of-stream marker")
        magic = data[cursor:cursor + 4]
        if magic == _END_OF_STREAM_MAGIC:
            return bytes(out)
        if magic == _UNCOMPRESSED_MAGIC:
            if cursor + 12 > len(data):
                raise ValueError("LZFSE uncompressed block header is truncated")
            raw_count, payload_count = struct.unpack_from("<2I", data, cursor + 4)
            if payload_count > len(data) - cursor - 12:
                raise ValueError("LZFSE uncompressed block payload is truncated")
            if raw_count != payload_count:
                raise ValueError("LZFSE uncompressed block has inconsistent sizes")
            out += data[cursor + 12: cursor + 12 + payload_count]
            cursor += 12 + payload_count
            continue
        if magic in _COMPRESSED_MAGICS:
            raise ValueError(
                "LZFSE entropy-coded blocks require the optional lzfse C extension"
            )
        raise ValueError(f"invalid LZFSE block magic: {magic!r}")
    raise ValueError("LZFSE stream has no end-of-stream marker")
