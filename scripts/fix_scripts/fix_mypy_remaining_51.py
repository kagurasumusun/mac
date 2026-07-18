with open("src/actool_linux/lzfse_optimized.py", "r") as f:
    lz_lines = f.readlines()
for i in range(len(lz_lines)):
    if "def _encode_literals(self, data: bytes | bytearray) -> None:" in lz_lines[i]:
        pass
    if "self._encode_literals(chunk)" in lz_lines[i] and "bytearray" not in lz_lines[i] and "bytes" not in lz_lines[i]:
        lz_lines[i] = lz_lines[i].replace("chunk", "bytes(chunk)")
    elif "self._encode_literals(chunk[match_len:])" in lz_lines[i] and "bytearray" not in lz_lines[i] and "bytes" not in lz_lines[i]:
        lz_lines[i] = lz_lines[i].replace("chunk[match_len:]", "bytes(chunk[match_len:])")
with open("src/actool_linux/lzfse_optimized.py", "w") as f:
    f.writelines(lz_lines)

with open("src/actool_linux/imagestack.py", "r") as f:
    im_lines = f.readlines()
for i in range(len(im_lines)):
    if "h * (scale or 1)" in im_lines[i] and "scale" in im_lines[i] and "int" not in im_lines[i]:
        im_lines[i] = im_lines[i].replace("scale or 1", "scale if scale is not None else 1")
    if "w * (scale or 1)" in im_lines[i] and "scale" in im_lines[i] and "int" not in im_lines[i]:
        im_lines[i] = im_lines[i].replace("scale or 1", "scale if scale is not None else 1")
    if "scale: int | None = None" in im_lines[i] or "scale: int = 1" in im_lines[i]:
        im_lines[i] = im_lines[i].replace("scale: int | None = None", "scale: int = 1")
    if "child_width = width // (scale or 1)" in im_lines[i]:
        im_lines[i] = "    child_width = width // scale\n"
    if "child_height = height // (scale or 1)" in im_lines[i]:
        im_lines[i] = "    child_height = height // scale\n"
    if "asset_scale = scale or 1" in im_lines[i] and "asset_scale = scale\n" not in im_lines[i]:
        im_lines[i] = "    asset_scale = scale\n"
with open("src/actool_linux/imagestack.py", "w") as f:
    f.writelines(im_lines)

