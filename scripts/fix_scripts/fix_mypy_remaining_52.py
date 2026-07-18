with open("src/actool_linux/imagestack.py", "r") as f:
    im_lines = f.readlines()
for i in range(len(im_lines)):
    if "h * scale" in im_lines[i] and "scale" in im_lines[i]:
        im_lines[i] = im_lines[i].replace("h * scale", "h * (scale or 1)")
    if "w * scale" in im_lines[i] and "scale" in im_lines[i]:
        im_lines[i] = im_lines[i].replace("w * scale", "w * (scale or 1)")

with open("src/actool_linux/imagestack.py", "w") as f:
    f.writelines(im_lines)

with open("src/actool_linux/lzfse_optimized.py", "r") as f:
    lz_lines = f.readlines()
for i in range(len(lz_lines)):
    if "def _encode_literals(self, data: bytes | bytearray) -> None:" in lz_lines[i] or "def _encode_literals(self, data: bytes) -> None:" in lz_lines[i]:
        lz_lines[i] = "    def _encode_literals(self, data: bytes | bytearray) -> None:\n        data = bytes(data)\n"
    if "self._encode_literals(" in lz_lines[i] and "bytearray" not in lz_lines[i] and "bytes" not in lz_lines[i]:
        lz_lines[i] = lz_lines[i].replace("chunk", "bytes(chunk)")
with open("src/actool_linux/lzfse_optimized.py", "w") as f:
    f.writelines(lz_lines)

