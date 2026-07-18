from __future__ import annotations

from dataclasses import dataclass
import struct


ROOT_STYLE_KIND_NAMES = {
    0: 'fill-or-gradient',
    2: 'icon-group',
}

GROUP_STYLE_KIND_NAMES = {
    0: 'indirect-or-default-style',
    1: 'named-style-reference',
}


ROOT_STYLE_INFERRED_ROLES = {
    (0, 217): 'named-color-fill',
    (0, 247): 'named-gradient-fill',
    (2, 246): 'icon-group-depth',
}


class IconStackError(ValueError):
    pass


@dataclass(frozen=True)
class IconStackRootStyleEntry:
    kind: int
    value: float
    enabled: int
    reserved_hex: str

    @property
    def inferred_kind_name(self) -> str:
        return ROOT_STYLE_KIND_NAMES.get(self.kind, f'unknown({self.kind})')

    def inferred_role_for_referenced_part(self, referenced_part: int) -> str:
        role = ROOT_STYLE_INFERRED_ROLES.get((self.kind, referenced_part))
        if role is not None:
            return role
        if self.kind == 0 and referenced_part == 246:
            return 'group-default' if self.value == 0.0 else 'group-exception'
        return f'unknown(kind={self.kind},part={referenced_part})'


@dataclass(frozen=True)
class IconStackRootStyleList:
    entries: tuple[IconStackRootStyleEntry, ...]


@dataclass(frozen=True)
class IconStackAuxEntry:
    u32_1: int
    f32_1: float
    u32_2: int
    f32_2: float
    u32_3: int


@dataclass(frozen=True)
class IconStackAuxList:
    entries: tuple[IconStackAuxEntry, ...]


@dataclass(frozen=True)
class IconStackGroupStyleReference:
    count: int
    kind: int
    name: str

    @property
    def inferred_kind_name(self) -> str:
        return GROUP_STYLE_KIND_NAMES.get(self.kind, f'unknown({self.kind})')

    @property
    def inferred_name_kind(self) -> str:
        if self.name == '':
            return 'blank'
        if '/Color-' in self.name:
            return 'color'
        if '/Gradient-' in self.name:
            return 'gradient'
        return 'other'


@dataclass(frozen=True)
class NamedGradientStop:
    position: float
    name: str


@dataclass(frozen=True)
class NamedGradientPayload:
    signature: str
    stop_count: int
    mode: int
    scalar_1: float
    scalar_2: float
    scalar_3: float
    scalar_4: float
    scalar_5: float
    stops: tuple[NamedGradientStop, ...]


def build_iconstack_root_style_list(entries: list[IconStackRootStyleEntry]) -> bytes:
    raw = bytearray(struct.pack('<2I', len(entries), 0))
    for entry in entries:
        reserved = bytes.fromhex(entry.reserved_hex)
        if len(reserved) != 4:
            raise IconStackError('icon stack root style entry reserved bytes must be 4 bytes')
        if not 0 <= entry.enabled <= 255:
            raise IconStackError('icon stack root style entry enabled must fit in one byte')
        raw += struct.pack('<IfB', entry.kind, entry.value, entry.enabled)
        raw += reserved
    return bytes(raw)


def parse_iconstack_root_style_list(raw: bytes | bytearray | memoryview) -> IconStackRootStyleList:
    data = bytes(raw)
    if len(data) < 8:
        raise IconStackError('icon stack root style list is truncated')
    count, reserved = struct.unpack_from('<2I', data)
    if reserved != 0:
        raise IconStackError('icon stack root style list reserved field is nonzero')
    cursor = 8
    entries: list[IconStackRootStyleEntry] = []
    for _ in range(count):
        if cursor + 13 > len(data):
            raise IconStackError('icon stack root style entry is truncated')
        kind = struct.unpack_from('<I', data, cursor)[0]
        value = struct.unpack_from('<f', data, cursor + 4)[0]
        enabled = data[cursor + 8]
        reserved_hex = data[cursor + 9:cursor + 13].hex()
        entries.append(IconStackRootStyleEntry(kind, value, enabled, reserved_hex))
        cursor += 13
    if cursor != len(data):
        raise IconStackError('icon stack root style list has trailing bytes')
    return IconStackRootStyleList(tuple(entries))


def build_iconstack_aux_list(entries: list[IconStackAuxEntry]) -> bytes:
    raw = bytearray(struct.pack('<2I', len(entries), 0))
    for entry in entries:
        raw += struct.pack('<IfIfI', entry.u32_1, entry.f32_1, entry.u32_2, entry.f32_2, entry.u32_3)
    return bytes(raw)


def parse_iconstack_aux_list(raw: bytes | bytearray | memoryview) -> IconStackAuxList:
    data = bytes(raw)
    if len(data) < 8:
        raise IconStackError('icon stack auxiliary list is truncated')
    count, reserved = struct.unpack_from('<2I', data)
    if reserved != 0:
        raise IconStackError('icon stack auxiliary list reserved field is nonzero')
    cursor = 8
    entries: list[IconStackAuxEntry] = []
    for _ in range(count):
        if cursor + 20 > len(data):
            raise IconStackError('icon stack auxiliary entry is truncated')
        u32_1 = struct.unpack_from('<I', data, cursor)[0]
        f32_1 = struct.unpack_from('<f', data, cursor + 4)[0]
        u32_2 = struct.unpack_from('<I', data, cursor + 8)[0]
        f32_2 = struct.unpack_from('<f', data, cursor + 12)[0]
        u32_3 = struct.unpack_from('<I', data, cursor + 16)[0]
        entries.append(IconStackAuxEntry(u32_1, f32_1, u32_2, f32_2, u32_3))
        cursor += 20
    if cursor != len(data):
        raise IconStackError('icon stack auxiliary list has trailing bytes')
    return IconStackAuxList(tuple(entries))


def build_iconstack_group_style_reference(reference: IconStackGroupStyleReference) -> bytes:
    name_bytes = reference.name.encode('utf-8') + b'\0'
    return struct.pack('<5I', reference.count, 0, reference.kind, 0, len(name_bytes)) + name_bytes


def parse_iconstack_group_style_reference(raw: bytes | bytearray | memoryview) -> IconStackGroupStyleReference:
    data = bytes(raw)
    if len(data) < 20:
        raise IconStackError('icon stack group style reference is truncated')
    count, reserved0, kind, reserved1, name_length = struct.unpack_from('<5I', data)
    if reserved0 != 0 or reserved1 != 0:
        raise IconStackError('icon stack group style reference reserved field is nonzero')
    end = 20 + name_length
    if end > len(data):
        raise IconStackError('icon stack group style reference name is truncated')
    name_bytes = data[20:end]
    if end != len(data):
        raise IconStackError('icon stack group style reference has trailing bytes')
    if not name_bytes.endswith(b'\0'):
        raise IconStackError('icon stack group style reference name is not NUL terminated')
    name = name_bytes[:-1].decode('utf-8', 'replace')
    return IconStackGroupStyleReference(count, kind, name)


def build_named_gradient_payload(payload: NamedGradientPayload) -> bytes:
    if payload.stop_count != len(payload.stops):
        raise IconStackError('named gradient stop_count does not match the number of stops')
    if len(payload.signature.encode('latin-1', 'strict')) != 4:
        raise IconStackError('named gradient signature must be exactly 4 latin-1 bytes')
    raw = bytearray()
    raw += payload.signature.encode('latin-1', 'strict')
    raw += struct.pack('<2I', payload.stop_count, payload.mode)
    raw += struct.pack('<5f', payload.scalar_1, payload.scalar_2, payload.scalar_3, payload.scalar_4, payload.scalar_5)
    if payload.stops:
        first = payload.stops[0]
        raw += struct.pack('<f', first.position)
        first_name = first.name.encode('utf-8') + b'\0'
        raw += struct.pack('<I', len(first_name))
        raw += first_name
        for stop in payload.stops[1:]:
            name = stop.name.encode('utf-8') + b'\0'
            raw += struct.pack('<fI', stop.position, len(name))
            raw += name
    return bytes(raw)


def parse_named_gradient_payload(raw: bytes | bytearray | memoryview) -> NamedGradientPayload:
    data = bytes(raw)
    if len(data) < 40:
        raise IconStackError('named gradient payload is truncated')
    signature = data[:4].decode('latin-1')
    stop_count, mode = struct.unpack_from('<2I', data, 4)
    scalar_1, scalar_2, scalar_3, scalar_4, scalar_5 = struct.unpack_from('<5f', data, 12)
    first_position = struct.unpack_from('<f', data, 32)[0]
    cursor = 36
    stops: list[NamedGradientStop] = []
    if stop_count:
        if cursor + 4 > len(data):
            raise IconStackError('named gradient first stop length is truncated')
        name_length = struct.unpack_from('<I', data, cursor)[0]
        cursor += 4
        if cursor + name_length > len(data):
            raise IconStackError('named gradient first stop name is truncated')
        name_bytes = data[cursor:cursor + name_length]
        cursor += name_length
        if not name_bytes.endswith(b'\0'):
            raise IconStackError('named gradient stop name is not NUL terminated')
        stops.append(NamedGradientStop(first_position, name_bytes[:-1].decode('utf-8', 'replace')))
        for _ in range(stop_count - 1):
            if cursor + 8 > len(data):
                raise IconStackError('named gradient stop entry is truncated')
            position = struct.unpack_from('<f', data, cursor)[0]
            name_length = struct.unpack_from('<I', data, cursor + 4)[0]
            cursor += 8
            if cursor + name_length > len(data):
                raise IconStackError('named gradient stop name is truncated')
            name_bytes = data[cursor:cursor + name_length]
            cursor += name_length
            if not name_bytes.endswith(b'\0'):
                raise IconStackError('named gradient stop name is not NUL terminated')
            stops.append(NamedGradientStop(position, name_bytes[:-1].decode('utf-8', 'replace')))
    if cursor != len(data):
        raise IconStackError('named gradient payload has trailing bytes')
    return NamedGradientPayload(signature, stop_count, mode, scalar_1, scalar_2, scalar_3, scalar_4, scalar_5, tuple(stops))
