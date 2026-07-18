with open("src/actool_linux/imagestack.py", "r") as f:
    im_lines = f.readlines()
for i in range(len(im_lines)):
    if "child_width = width // scale" in im_lines[i] or "child_width = width // (scale or 1)" in im_lines[i] or "child_width = width // (scale if scale is not None else 1)" in im_lines[i]:
        im_lines[i] = "    child_width = (width or 0) // scale\n"
    if "child_height = height // scale" in im_lines[i] or "child_height = height // (scale or 1)" in im_lines[i] or "child_height = height // (scale if scale is not None else 1)" in im_lines[i]:
        im_lines[i] = "    child_height = (height or 0) // scale\n"
    if "for i in range(width * height):" in im_lines[i]:
        im_lines[i] = "        for i in range((width or 0) * (height or 0)):\n"

with open("src/actool_linux/imagestack.py", "w") as f:
    f.writelines(im_lines)

with open("src/actool_linux/lzfse_optimized.py", "r") as f:
    lz_lines = f.readlines()
for i in range(len(lz_lines)):
    if "def _encode_literals(self, data: bytes)" in lz_lines[i] or "def _encode_literals(self, data: bytes | bytearray) -> None:" in lz_lines[i]:
        lz_lines[i] = "    def _encode_literals(self, data: bytes | bytearray) -> None:\n        data = bytes(data)\n"
    if "self._encode_literals(" in lz_lines[i] and "bytes(" not in lz_lines[i]:
        lz_lines[i] = lz_lines[i].replace("chunk", "bytes(chunk)")

with open("src/actool_linux/lzfse_optimized.py", "w") as f:
    f.writelines(lz_lines)

