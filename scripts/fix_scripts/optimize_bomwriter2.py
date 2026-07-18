import re

with open("src/actool_linux/bomwriter.py", "r") as f:
    content = f.read()

new_build = '''    def build(self) -> bytes:
        import io
        cursor = 0x200
        chunks: list[tuple[int, bytes]] = []
        locations: dict[int, tuple[int, int]] = {}
        for block in self._blocks:
            cursor = self._align(cursor)
            chunks.append((cursor, block.data))
            locations[block.identifier] = (cursor, len(block.data))
            cursor += len(block.data)

        cursor = self._align(cursor)
        variables_offset = cursor
        variables = bytearray(struct.pack(">I", len(self._variables)))
        for name, identifier in self._variables:
            encoded = name.encode("utf-8")
            variables += struct.pack(">IB", identifier, len(encoded)) + encoded
        variables_length = len(variables)
        chunks.append((variables_offset, bytes(variables)))

        cursor = self._align(variables_offset + variables_length)
        index_offset = cursor
        capacity = 1
        while capacity <= len(self._blocks):
            capacity *= 2
        capacity = max(16, capacity)
        index = bytearray(struct.pack(">I", capacity))
        index += struct.pack(">II", 0, 0)
        for identifier in range(1, capacity):
            index += struct.pack(">II", *locations.get(identifier, (0, 0)))
        # Observed BOMStore files carry a five-word free-list trailer.
        index += b"\\0" * 20
        index_length = len(index)
        chunks.append((index_offset, bytes(index)))

        total = index_offset + index_length
        out = io.BytesIO()
        header = struct.pack(
            ">8s6I", b"BOMStore", 1, len(self._blocks),
            index_offset, index_length, variables_offset, variables_length,
        )
        out.write(header)
        for offset, data in chunks:
            out.seek(offset)
            out.write(data)
        
        # pad to total if needed
        out.seek(total - 1)
        out.write(b"\\0")
        return out.getvalue()
'''

content = re.sub(r'    def build\(self\) -> bytes:.*?(?=\n\n|\Z)', new_build, content, flags=re.DOTALL)
content = content.replace("\\0", "\0")

with open("src/actool_linux/bomwriter.py", "w") as f:
    f.write(content)
