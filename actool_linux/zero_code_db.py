"""Zero-code database support for CoreUI 850+.

This module provides support for zero-code bezel and glyph databases,
which are used in CoreUI 850+ for rendering UI elements without
requiring bitmap assets.
"""

from typing import Dict, List, Optional, Tuple
from typing import Any
import struct


class ZeroCodeBezel:
    """A zero-code bezel definition.

    Zero-code bezels define UI elements (buttons, panels, etc.) using
    vector graphics and procedural rendering instead of bitmaps.
    """

    def __init__(self, name: str, width: int, height: int):
        self.name = name
        self.width = width
        self.height = height
        self.layers: List['ZeroCodeLayer'] = []
        self.effects: List['ZeroCodeEffect'] = []

    def add_layer(self, layer: 'ZeroCodeLayer'):
        """Add a layer to the bezel."""
        self.layers.append(layer)

    def add_effect(self, effect: 'ZeroCodeEffect'):
        """Add an effect to the bezel."""
        self.effects.append(effect)

    def serialize(self) -> bytes:
        """Serialize the bezel to binary format."""
        output = bytearray()

        # Header
        output.extend(struct.pack('<I', len(self.name)))
        output.extend(self.name.encode('utf-8'))
        output.extend(struct.pack('<II', self.width, self.height))

        # Layers
        output.extend(struct.pack('<I', len(self.layers)))
        for layer in self.layers:
            output.extend(layer.serialize())

        # Effects
        output.extend(struct.pack('<I', len(self.effects)))
        for effect in self.effects:
            output.extend(effect.serialize())

        return bytes(output)

    @classmethod
    def deserialize(cls, data: bytes) -> 'ZeroCodeBezel':
        """Deserialize a bezel from binary format."""
        offset = 0

        # Header
        name_len = struct.unpack_from('<I', data, offset)[0]
        offset += 4
        name = data[offset:offset + name_len].decode('utf-8')
        offset += name_len
        width, height = struct.unpack_from('<II', data, offset)
        offset += 8

        bezel = cls(name, width, height)

        # Layers
        layer_count = struct.unpack_from('<I', data, offset)[0]
        offset += 4
        for _ in range(layer_count):
            layer, offset = ZeroCodeLayer.deserialize(data, offset)
            bezel.add_layer(layer)

        # Effects
        effect_count = struct.unpack_from('<I', data, offset)[0]
        offset += 4
        for _ in range(effect_count):
            effect, offset = ZeroCodeEffect.deserialize(data, offset)
            bezel.add_effect(effect)

        return bezel


class ZeroCodeLayer:
    """A layer in a zero-code bezel."""

    def __init__(self, layer_type: str, bounds: Tuple[int, int, int, int]):
        self.layer_type = layer_type  # 'fill', 'stroke', 'gradient', etc.
        self.bounds = bounds  # (x, y, width, height)
        self.properties: Dict[str, Any] = {}

    def set_property(self, key: str, value: Any):
        """Set a layer property."""
        self.properties[key] = value

    def serialize(self) -> bytes:
        """Serialize the layer to binary format."""
        output = bytearray()

        # Type
        output.extend(struct.pack('<I', len(self.layer_type)))
        output.extend(self.layer_type.encode('utf-8'))

        # Bounds
        output.extend(struct.pack('<iiii', *self.bounds))

        # Properties
        output.extend(struct.pack('<I', len(self.properties)))
        for key, value in self.properties.items():
            output.extend(struct.pack('<I', len(key)))
            output.extend(key.encode('utf-8'))
            # Serialize value based on type
            if isinstance(value, int):
                output.extend(struct.pack('<BI', 0, value))
            elif isinstance(value, float):
                output.extend(struct.pack('<Bf', 1, value))
            elif isinstance(value, str):
                output.extend(struct.pack('<BI', 2, len(value)))
                output.extend(value.encode('utf-8'))
            elif isinstance(value, bytes):
                output.extend(struct.pack('<BI', 3, len(value)))
                output.extend(value)

        return bytes(output)

    @classmethod
    def deserialize(cls, data: bytes, offset: int) -> Tuple['ZeroCodeLayer', int]:
        """Deserialize a layer from binary format."""
        # Type
        type_len = struct.unpack_from('<I', data, offset)[0]
        offset += 4
        layer_type = data[offset:offset + type_len].decode('utf-8')
        offset += type_len

        # Bounds
        bounds = struct.unpack_from('<iiii', data, offset)
        offset += 16

        layer = cls(layer_type, bounds)

        # Properties
        prop_count = struct.unpack_from('<I', data, offset)[0]
        offset += 4
        for _ in range(prop_count):
            key_len = struct.unpack_from('<I', data, offset)[0]
            offset += 4
            key = data[offset:offset + key_len].decode('utf-8')
            offset += key_len

            prop_type = data[offset]
            offset += 1

            if prop_type == 0:  # int
                value = struct.unpack_from('<I', data, offset)[0]
                offset += 4
            elif prop_type == 1:  # float
                value = struct.unpack_from('<f', data, offset)[0]
                offset += 4
            elif prop_type == 2:  # str
                str_len = struct.unpack_from('<I', data, offset)[0]
                offset += 4
                value = data[offset:offset + str_len].decode('utf-8')
                offset += str_len
            elif prop_type == 3:  # bytes
                bytes_len = struct.unpack_from('<I', data, offset)[0]
                offset += 4
                value = data[offset:offset + bytes_len]
                offset += bytes_len

            layer.set_property(key, value)

        return layer, offset


class ZeroCodeEffect:
    """An effect applied to a zero-code bezel."""

    def __init__(self, effect_type: str):
        self.effect_type = effect_type  # 'shadow', 'blur', 'glow', etc.
        self.parameters: Dict[str, Any] = {}

    def set_parameter(self, key: str, value: Any):
        """Set an effect parameter."""
        self.parameters[key] = value

    def serialize(self) -> bytes:
        """Serialize the effect to binary format."""
        output = bytearray()

        # Type
        output.extend(struct.pack('<I', len(self.effect_type)))
        output.extend(self.effect_type.encode('utf-8'))

        # Parameters
        output.extend(struct.pack('<I', len(self.parameters)))
        for key, value in self.parameters.items():
            output.extend(struct.pack('<I', len(key)))
            output.extend(key.encode('utf-8'))
            # Serialize value (same as layer properties)
            if isinstance(value, int):
                output.extend(struct.pack('<BI', 0, value))
            elif isinstance(value, float):
                output.extend(struct.pack('<Bf', 1, value))
            elif isinstance(value, str):
                output.extend(struct.pack('<BI', 2, len(value)))
                output.extend(value.encode('utf-8'))

        return bytes(output)

    @classmethod
    def deserialize(cls, data: bytes, offset: int) -> Tuple['ZeroCodeEffect', int]:
        """Deserialize an effect from binary format."""
        # Type
        type_len = struct.unpack_from('<I', data, offset)[0]
        offset += 4
        effect_type = data[offset:offset + type_len].decode('utf-8')
        offset += type_len

        effect = cls(effect_type)

        # Parameters
        param_count = struct.unpack_from('<I', data, offset)[0]
        offset += 4
        for _ in range(param_count):
            key_len = struct.unpack_from('<I', data, offset)[0]
            offset += 4
            key = data[offset:offset + key_len].decode('utf-8')
            offset += key_len

            param_type = data[offset]
            offset += 1

            if param_type == 0:  # int
                value = struct.unpack_from('<I', data, offset)[0]
                offset += 4
            elif param_type == 1:  # float
                value = struct.unpack_from('<f', data, offset)[0]
                offset += 4
            elif param_type == 2:  # str
                str_len = struct.unpack_from('<I', data, offset)[0]
                offset += 4
                value = data[offset:offset + str_len].decode('utf-8')
                offset += str_len

            effect.set_parameter(key, value)

        return effect, offset


class ZeroCodeGlyph:
    """A zero-code glyph definition (for text rendering)."""

    def __init__(self, character: str, width: int):
        self.character = character
        self.width = width
        self.paths: List[bytes] = []  # Vector path data

    def add_path(self, path_data: bytes):
        """Add a vector path to the glyph."""
        self.paths.append(path_data)

    def serialize(self) -> bytes:
        """Serialize the glyph to binary format."""
        output = bytearray()

        # Character and width
        output.extend(self.character.encode('utf-8'))
        output.extend(struct.pack('<I', self.width))

        # Paths
        output.extend(struct.pack('<I', len(self.paths)))
        for path in self.paths:
            output.extend(struct.pack('<I', len(path)))
            output.extend(path)

        return bytes(output)


class ZeroCodeDatabase:
    """Container for zero-code bezel and glyph databases."""

    def __init__(self):
        self.bezels: Dict[str, ZeroCodeBezel] = {}
        self.glyphs: Dict[str, ZeroCodeGlyph] = {}

    def add_bezel(self, bezel: ZeroCodeBezel):
        """Add a bezel to the database."""
        self.bezels[bezel.name] = bezel

    def add_glyph(self, glyph: ZeroCodeGlyph):
        """Add a glyph to the database."""
        self.glyphs[glyph.character] = glyph

    def get_bezel(self, name: str) -> Optional[ZeroCodeBezel]:
        """Get a bezel by name."""
        return self.bezels.get(name)

    def get_glyph(self, character: str) -> Optional[ZeroCodeGlyph]:
        """Get a glyph by character."""
        return self.glyphs.get(character)

    def serialize_bezels(self) -> bytes:
        """Serialize all bezels to binary format."""
        output = bytearray()

        # Count
        output.extend(struct.pack('<I', len(self.bezels)))

        # Bezels
        for bezel in self.bezels.values():
            bezel_data = bezel.serialize()
            output.extend(struct.pack('<I', len(bezel_data)))
            output.extend(bezel_data)

        return bytes(output)

    def serialize_glyphs(self) -> bytes:
        """Serialize all glyphs to binary format."""
        output = bytearray()

        # Count
        output.extend(struct.pack('<I', len(self.glyphs)))

        # Glyphs
        for glyph in self.glyphs.values():
            glyph_data = glyph.serialize()
            output.extend(struct.pack('<I', len(glyph_data)))
            output.extend(glyph_data)

        return bytes(output)
