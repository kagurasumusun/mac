"""Complete implementation of texture references, named gradients, and icon stacks.

This module provides full support for advanced CAR file features:
- Texture references (RTXT payloads)
- Named gradients (ARGG payloads)
- Icon stacks (layered icons with rendering properties)
from typing import any
"""

from typing import Dict, List, Optional, Tuple
import struct


# ============================================================================
# Texture References (RTXT)
# ============================================================================

class TextureReference:
    """A texture reference pointing to external texture data.

    RTXT payloads reference textures stored elsewhere in the CAR file
    or in external resources.
    """

    def __init__(self, texture_name: str, width: int, height: int):
        self.texture_name = texture_name
        self.width = width
        self.height = height
        self.key_pairs: List[Tuple[int, int]] = []
        self.payload_value: int = 0
        self.u32_2: int = 0
        self.u32_3: int = 0
        self.u32_4: int = 0

    def add_key_pair(self, attribute: int, value: int):
        """Add a key pair to the texture reference."""
        self.key_pairs.append((attribute, value))

    def serialize(self) -> bytes:
        """Serialize to RTXT binary format."""
        output = bytearray()

        # Magic
        output.extend(b'RTXT')

        # Texture name
        name_bytes = self.texture_name.encode('utf-8')
        output.extend(struct.pack('<I', len(name_bytes)))
        output.extend(name_bytes)

        # Dimensions
        output.extend(struct.pack('<II', self.width, self.height))

        # Payload metadata
        output.extend(struct.pack('<IIII',
                                  self.payload_value,
                                  self.u32_2,
                                  self.u32_3,
                                  self.u32_4))

        # Key pairs
        output.extend(struct.pack('<I', len(self.key_pairs)))
        for attr, val in self.key_pairs:
            output.extend(struct.pack('<II', attr, val))

        return bytes(output)

    @classmethod
    def deserialize(cls, data: bytes) -> 'TextureReference':
        """Deserialize from RTXT binary format."""
        if data[:4] != b'RTXT':
            raise ValueError("Invalid RTXT magic")

        offset = 4

        # Texture name
        name_len = struct.unpack_from('<I', data, offset)[0]
        offset += 4
        texture_name = data[offset:offset + name_len].decode('utf-8')
        offset += name_len

        # Dimensions
        width, height = struct.unpack_from('<II', data, offset)
        offset += 8

        # Payload metadata
        payload_value, u32_2, u32_3, u32_4 = struct.unpack_from('<IIII', data, offset)
        offset += 16

        # Key pairs
        key_pair_count = struct.unpack_from('<I', data, offset)[0]
        offset += 4

        tex_ref = cls(texture_name, width, height)
        tex_ref.payload_value = payload_value
        tex_ref.u32_2 = u32_2
        tex_ref.u32_3 = u32_3
        tex_ref.u32_4 = u32_4

        for _ in range(key_pair_count):
            attr, val = struct.unpack_from('<II', data, offset)
            offset += 8
            tex_ref.add_key_pair(attr, val)

        return tex_ref


# ============================================================================
# Named Gradients (ARGG)
# ============================================================================

class GradientStop:
    """A color stop in a gradient."""

    def __init__(self, position: float, color_name: str):
        self.position = position  # 0.0 to 1.0
        self.color_name = color_name

    def serialize(self) -> bytes:
        """Serialize the gradient stop."""
        output = bytearray()
        output.extend(struct.pack('<f', self.position))
        name_bytes = self.color_name.encode('utf-8')
        output.extend(struct.pack('<I', len(name_bytes)))
        output.extend(name_bytes)
        return bytes(output)

    @classmethod
    def deserialize(cls, data: bytes, offset: int) -> Tuple['GradientStop', int]:
        """Deserialize a gradient stop."""
        position = struct.unpack_from('<f', data, offset)[0]
        offset += 4

        name_len = struct.unpack_from('<I', data, offset)[0]
        offset += 4
        color_name = data[offset:offset + name_len].decode('utf-8')
        offset += name_len

        return cls(position, color_name), offset


class NamedGradient:
    """A named gradient definition (ARGG payload).

    Named gradients define reusable gradient fills that can be
    referenced by name throughout the CAR file.
    """

    def __init__(self, name: str):
        self.name = name
        self.signature: bytes = b'ARGG'
        self.stop_count: int = 0
        self.mode: int = 0  # 0 = linear, 1 = radial
        self.scalar_1: float = 0.0
        self.scalar_2: float = 0.5
        self.scalar_3: float = 0.0
        self.scalar_4: float = 0.5
        self.scalar_5: float = 1.0
        self.stops: List[GradientStop] = []

    def add_stop(self, position: float, color_name: str):
        """Add a color stop to the gradient."""
        self.stops.append(GradientStop(position, color_name))
        self.stop_count = len(self.stops)

    def serialize(self) -> bytes:
        """Serialize to ARGG binary format."""
        output = bytearray()

        # Signature
        output.extend(self.signature)

        # Header
        output.extend(struct.pack('<I', self.stop_count))
        output.extend(struct.pack('<I', self.mode))

        # Scalars (gradient geometry parameters)
        output.extend(struct.pack('<fffff',
                                  self.scalar_1,
                                  self.scalar_2,
                                  self.scalar_3,
                                  self.scalar_4,
                                  self.scalar_5))

        # Stops
        for stop in self.stops:
            output.extend(stop.serialize())

        return bytes(output)

    @classmethod
    def deserialize(cls, data: bytes) -> 'NamedGradient':
        """Deserialize from ARGG binary format."""
        if data[:4] != b'ARGG':
            raise ValueError("Invalid ARGG signature")

        offset = 4

        # Header
        stop_count, mode = struct.unpack_from('<II', data, offset)
        offset += 8

        # Scalars
        scalars = struct.unpack_from('<fffff', data, offset)
        offset += 20

        gradient = cls("")
        gradient.stop_count = stop_count
        gradient.mode = mode
        gradient.scalar_1, gradient.scalar_2, gradient.scalar_3, \
            gradient.scalar_4, gradient.scalar_5 = scalars

        # Stops
        for _ in range(stop_count):
            stop, offset = GradientStop.deserialize(data, offset)
            gradient.stops.append(stop)

        return gradient


# ============================================================================
# Icon Stacks
# ============================================================================

class IconStackLayer:
    """A layer in an icon stack."""

    def __init__(self, layer_name: str, opacity: float = 1.0):
        self.layer_name = layer_name
        self.opacity = opacity
        self.origin_x: int = 0
        self.origin_y: int = 0
        self.width: int = 0
        self.height: int = 0
        self.referenced_key: List[Tuple[int, int]] = []

    def set_bounds(self, x: int, y: int, width: int, height: int):
        """Set the layer bounds."""
        self.origin_x = x
        self.origin_y = y
        self.width = width
        self.height = height

    def add_referenced_key(self, attribute: int, value: int):
        """Add a referenced key pair."""
        self.referenced_key.append((attribute, value))

    def serialize(self) -> bytes:
        """Serialize the layer."""
        output = bytearray()

        # Layer name
        name_bytes = self.layer_name.encode('utf-8')
        output.extend(struct.pack('<I', len(name_bytes)))
        output.extend(name_bytes)

        # Opacity
        output.extend(struct.pack('<f', self.opacity))

        # Bounds
        output.extend(struct.pack('<iiii',
                                  self.origin_x,
                                  self.origin_y,
                                  self.width,
                                  self.height))

        # Referenced keys
        output.extend(struct.pack('<I', len(self.referenced_key)))
        for attr, val in self.referenced_key:
            output.extend(struct.pack('<II', attr, val))

        return bytes(output)

    @classmethod
    def deserialize(cls, data: bytes, offset: int) -> Tuple['IconStackLayer', int]:
        """Deserialize a layer."""
        # Layer name
        name_len = struct.unpack_from('<I', data, offset)[0]
        offset += 4
        layer_name = data[offset:offset + name_len].decode('utf-8')
        offset += name_len

        # Opacity
        opacity = struct.unpack_from('<f', data, offset)[0]
        offset += 4

        # Bounds
        origin_x, origin_y, width, height = struct.unpack_from('<iiii', data, offset)
        offset += 16

        layer = cls(layer_name, opacity)
        layer.set_bounds(origin_x, origin_y, width, height)

        # Referenced keys
        key_count = struct.unpack_from('<I', data, offset)[0]
        offset += 4
        for _ in range(key_count):
            attr, val = struct.unpack_from('<II', data, offset)
            offset += 8
            layer.add_referenced_key(attr, val)

        return layer, offset


class IconStackRenderingProperties:
    """Rendering properties for an icon stack."""

    def __init__(self):
        self.entries: List[Dict[str, any]] = []

    def add_entry(self, kind: int, value: float, inferred_kind_name: str = ""):
        """Add a rendering property entry."""
        self.entries.append({
            'kind': kind,
            'value': value,
            'inferred_kind_name': inferred_kind_name
        })

    def serialize(self) -> bytes:
        """Serialize rendering properties."""
        output = bytearray()

        output.extend(struct.pack('<I', len(self.entries)))
        for entry in self.entries:
            output.extend(struct.pack('<If', entry['kind'], entry['value']))
            name_bytes = str(entry['inferred_kind_name']).encode('utf-8')
            output.extend(struct.pack('<I', len(name_bytes)))
            output.extend(name_bytes)

        return bytes(output)

    @classmethod
    def deserialize(cls, data: bytes, offset: int) -> Tuple['IconStackRenderingProperties', int]:
        """Deserialize rendering properties."""
        props = cls()

        entry_count = struct.unpack_from('<I', data, offset)[0]
        offset += 4

        for _ in range(entry_count):
            kind, value = struct.unpack_from('<If', data, offset)
            offset += 8

            name_len = struct.unpack_from('<I', data, offset)[0]
            offset += 4
            inferred_kind_name = data[offset:offset + name_len].decode('utf-8')
            offset += name_len

            props.add_entry(kind, value, inferred_kind_name)

        return props, offset


class IconStack:
    """An icon stack with multiple layers and rendering properties.

    Icon stacks allow composing complex icons from multiple layers
    with advanced rendering effects.
    """

    def __init__(self, name: str):
        self.name = name
        self.layers: List[IconStackLayer] = []
        self.rendering_properties: Optional[IconStackRenderingProperties] = None
        self.auxiliary_data: List[bytes] = []

    def add_layer(self, layer: IconStackLayer):
        """Add a layer to the icon stack."""
        self.layers.append(layer)

    def set_rendering_properties(self, props: IconStackRenderingProperties):
        """Set rendering properties for the icon stack."""
        self.rendering_properties = props

    def add_auxiliary_data(self, data: bytes):
        """Add auxiliary data to the icon stack."""
        self.auxiliary_data.append(data)

    def serialize(self) -> bytes:
        """Serialize the icon stack."""
        output = bytearray()

        # Name
        name_bytes = self.name.encode('utf-8')
        output.extend(struct.pack('<I', len(name_bytes)))
        output.extend(name_bytes)

        # Layers
        output.extend(struct.pack('<I', len(self.layers)))
        for layer in self.layers:
            layer_data = layer.serialize()
            output.extend(struct.pack('<I', len(layer_data)))
            output.extend(layer_data)

        # Rendering properties
        if self.rendering_properties:
            output.extend(struct.pack('<B', 1))  # Has properties
            props_data = self.rendering_properties.serialize()
            output.extend(struct.pack('<I', len(props_data)))
            output.extend(props_data)
        else:
            output.extend(struct.pack('<B', 0))  # No properties

        # Auxiliary data
        output.extend(struct.pack('<I', len(self.auxiliary_data)))
        for aux_data in self.auxiliary_data:
            output.extend(struct.pack('<I', len(aux_data)))
            output.extend(aux_data)

        return bytes(output)

    @classmethod
    def deserialize(cls, data: bytes) -> 'IconStack':
        """Deserialize an icon stack."""
        offset = 0

        # Name
        name_len = struct.unpack_from('<I', data, offset)[0]
        offset += 4
        name = data[offset:offset + name_len].decode('utf-8')
        offset += name_len

        stack = cls(name)

        # Layers
        layer_count = struct.unpack_from('<I', data, offset)[0]
        offset += 4
        for _ in range(layer_count):
            layer_len = struct.unpack_from('<I', data, offset)[0]
            offset += 4
            layer, _ = IconStackLayer.deserialize(data, offset)
            offset += layer_len
            stack.add_layer(layer)

        # Rendering properties
        has_props = data[offset]
        offset += 1
        if has_props:
            props_len = struct.unpack_from('<I', data, offset)[0]
            offset += 4
            props, _ = IconStackRenderingProperties.deserialize(data, offset)
            offset += props_len
            stack.set_rendering_properties(props)

        # Auxiliary data
        aux_count = struct.unpack_from('<I', data, offset)[0]
        offset += 4
        for _ in range(aux_count):
            aux_len = struct.unpack_from('<I', data, offset)[0]
            offset += 4
            aux_data = data[offset:offset + aux_len]
            offset += aux_len
            stack.add_auxiliary_data(aux_data)

        return stack


# ============================================================================
# Utility Functions
# ============================================================================

def create_linear_gradient(name: str, stops: List[Tuple[float, str]]) -> NamedGradient:
    """Create a linear gradient with the given stops."""
    gradient = NamedGradient(name)
    gradient.mode = 0  # Linear
    gradient.scalar_1 = 0.0  # Start X
    gradient.scalar_2 = 0.5  # Start Y
    gradient.scalar_3 = 0.0  # End X
    gradient.scalar_4 = 0.5  # End Y
    gradient.scalar_5 = 1.0  # Intensity

    for position, color_name in stops:
        gradient.add_stop(position, color_name)

    return gradient


def create_radial_gradient(name: str, stops: List[Tuple[float, str]],
                           center_x: float = 0.5, center_y: float = 0.5,
                           radius: float = 0.5) -> NamedGradient:
    """Create a radial gradient with the given stops."""
    gradient = NamedGradient(name)
    gradient.mode = 1  # Radial
    gradient.scalar_1 = center_x
    gradient.scalar_2 = center_y
    gradient.scalar_3 = radius
    gradient.scalar_4 = 0.0
    gradient.scalar_5 = 1.0

    for position, color_name in stops:
        gradient.add_stop(position, color_name)

    return gradient


def create_simple_icon_stack(name: str, layer_names: List[str]) -> IconStack:
    """Create a simple icon stack with stacked layers."""
    stack = IconStack(name)

    for i, layer_name in enumerate(layer_names):
        layer = IconStackLayer(layer_name, opacity=1.0)
        # Stack layers vertically
        layer.set_bounds(0, i * 10, 100, 10)
        stack.add_layer(layer)

    return stack
