from __future__ import annotations

from dataclasses import dataclass
import struct

from .bom import BOMError


@dataclass(frozen=True)
class TLV:
    tag: int
    value: bytes


@dataclass(frozen=True)
class CSIHeader:
    version: int
    flags: int
    width: int
    height: int
    scale_factor: int
    pixel_format: str
    color_space_id: int
    modification_time: int
    layout: int
    name: str
    tlvs: tuple[TLV, ...]
    rendition_data: bytes

    @property
    def scale(self) -> float:
        return self.scale_factor / 100.0


TLV_NAMES = {
    0x3E9: "slices",
    0x3EB: "metrics",
    0x3EC: "blend-mode-and-opacity",
    0x3ED: "uti",
    0x3EE: "exif-orientation",
    0x3F0: "external-tags",
    0x3F1: "frame",
}


def parse_csi(raw: bytes | bytearray | memoryview) -> CSIHeader:
    data = bytes(raw)
    if len(data) < 184:
        raise BOMError(f"CSI rendition is truncated: expected at least 184 bytes, got {len(data)}")
    if data[:4] == b"ISTC":
        order = "<"
    elif data[:4] == b"CTSI":
        order = ">"
    else:
        raise BOMError(f"invalid CSI magic: {data[:4]!r}")
    version, flags, width, height, scale = struct.unpack_from(order + "5I", data, 4)
    if version != 1:
        raise BOMError(f"unsupported CSI version: {version}")
    pixel_raw = data[24:28]
    pixel_format = bytes(reversed(pixel_raw)).decode("latin-1") if order == "<" else pixel_raw.decode("latin-1")
    color_space = struct.unpack_from(order + "I", data, 28)[0] & 0xF
    modification_time = struct.unpack_from(order + "I", data, 32)[0]
    layout, zero = struct.unpack_from(order + "2H", data, 36)
    name = data[40:168].split(b"\0", 1)[0].decode("utf-8", "replace")
    tlv_length, _unknown, _zero, rendition_length = struct.unpack_from(order + "4I", data, 168)
    if tlv_length > len(data) - 184:
        raise BOMError("CSI TLV area extends beyond the rendition block")
    rendition_offset = 184 + tlv_length
    if rendition_length > len(data) - rendition_offset:
        raise BOMError("CSI rendition payload extends beyond the rendition block")
    tlvs: list[TLV] = []
    cursor = 184
    tlv_end = rendition_offset
    while cursor < tlv_end:
        if cursor + 8 > tlv_end:
            raise BOMError("CSI TLV header is truncated")
        tag, length = struct.unpack_from(order + "2I", data, cursor)
        cursor += 8
        if length > tlv_end - cursor:
            raise BOMError("CSI TLV value is truncated")
        tlvs.append(TLV(tag, data[cursor:cursor + length]))
        cursor += length
    return CSIHeader(
        version, flags, width, height, scale, pixel_format, color_space,
        modification_time, layout, name, tuple(tlvs),
        data[rendition_offset:rendition_offset + rendition_length],
    )
