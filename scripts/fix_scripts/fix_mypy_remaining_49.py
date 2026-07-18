with open("src/actool_linux/imagestack.py", "r") as f:
    im_lines = f.readlines()
for i in range(len(im_lines)):
    if "def imagestack_renditions(" in im_lines[i]:
        im_lines[i] = im_lines[i].replace("scale: int | None = None", "scale: int = 1")
    if "child_width = width // (scale or 1)" in im_lines[i]:
        im_lines[i] = "    child_width = width // scale\n"
    elif "child_height = height // (scale or 1)" in im_lines[i]:
        im_lines[i] = "    child_height = height // scale\n"
    elif "asset_scale = scale or 1" in im_lines[i]:
        im_lines[i] = "    asset_scale = scale\n"
with open("src/actool_linux/imagestack.py", "w") as f:
    f.writelines(im_lines)

with open("src/actool_linux/lzfse_optimized.py", "r") as f:
    lz_lines = f.readlines()
for i in range(len(lz_lines)):
    if "def _encode_literals(self, data: bytes)" in lz_lines[i]:
        lz_lines[i] = "    def _encode_literals(self, data: bytes | bytearray) -> None:\n        data = bytes(data)\n"
    if "self._encode_literals(chunk)" in lz_lines[i] and "bytearray" not in lz_lines[i]:
        lz_lines[i] = lz_lines[i].replace("chunk", "bytes(chunk)")
    elif "self._encode_literals(chunk[match_len:])" in lz_lines[i] and "bytearray" not in lz_lines[i]:
        lz_lines[i] = lz_lines[i].replace("chunk[match_len:]", "bytes(chunk[match_len:])")
with open("src/actool_linux/lzfse_optimized.py", "w") as f:
    f.writelines(lz_lines)

with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()
for i in range(len(cp_lines)):
    if "StackLayerImage(str(layer.get(\"layer_name\", \"\")), str(layer.get(\"filename\", \"\")), (Path(str(layer.get(\"base\", \"\"))) / str(layer.get(\"filename\", \"\"))).read_bytes()) for layer in reversed(resolved)" in cp_lines[i]:
        cp_lines[i] = "        layers = [StackLayerImage(str(layer.get(\"layer_name\", \"\")), str(layer.get(\"filename\", \"\")), (Path(str(layer.get(\"base\", \"\"))) / str(layer.get(\"filename\", \"\"))).read_bytes()) for layer in reversed(resolved)] # type: ignore\n"
        
with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)
