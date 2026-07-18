with open("src/actool_linux/carwriter.py", "r") as f:
    lines = f.readlines()

for i in range(len(lines)):
    line = lines[i]
    if "index = decoded[y * width + x] if interlace else _packed_sample(decoded[y * packed_stride:(y + 1) * packed_stride], x, depth)" in line:
        lines[i] = line.replace("decoded[y * packed_stride:(y + 1) * packed_stride]", "bytes(decoded[y * packed_stride:(y + 1) * packed_stride])")
    if "def _facet_value(attribute: int, value: object) -> int:" in line:
        pass
    if "def _facet_value(attribute: int, value: object)" in line:
        pass

with open("src/actool_linux/carwriter.py", "w") as f:
    f.writelines(lines)
