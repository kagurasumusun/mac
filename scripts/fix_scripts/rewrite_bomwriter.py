import re

with open("src/actool_linux/bomwriter.py", "r") as f:
    content = f.read()

new_build = '''    def build(self) -> bytes:
        import io
        out = io.BytesIO()
        out.write(b"BOMStore")
        out.write(struct.pack(">3I", 1, 1, 0))
        
        blocks_data = []
        for ident in range(1, self.next_id):
            if ident in self.blocks:
                blocks_data.append(self.blocks[ident])
            else:
                blocks_data.append(b"")
        
        index_offset = 512
        for data in blocks_data:
            index_offset += len(data)
            
        out.write(struct.pack(">4I", 512, len(blocks_data) + 1, self.next_id, index_offset))
        out.write(b"\\0" * (512 - out.tell()))
        
        offsets = []
        current_offset = 512
        for data in blocks_data:
            out.write(data)
            offsets.append((current_offset, len(data)))
            current_offset += len(data)
            
        out.write(struct.pack(">I", len(blocks_data) + 1))
        out.write(struct.pack(">2I", 0, 0))
        for ident, (offset, length) in enumerate(offsets, 1):
            out.write(struct.pack(">2I", offset, length))
            
        return out.getvalue()
'''

content = re.sub(r'    def build\(self\) -> bytes:.*?(?=\n\n|\Z)', new_build, content, flags=re.DOTALL)

with open("src/actool_linux/bomwriter.py", "w") as f:
    f.write(content)
