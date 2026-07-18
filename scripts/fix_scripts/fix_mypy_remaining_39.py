with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()
for i in range(len(cp_lines)):
    if "tv: dict[str, str] = {}" in cp_lines[i] or "tv: dict[str, object] = {}" in cp_lines[i] or "tv: dict[str, Sequence[str]] = {}" in cp_lines[i]:
        cp_lines[i] = "                tv: dict[str, Any] = {}\n"
    if "layers = [StackLayerImage(str(layer.get(\"layer_name\", \"\")), str(layer.get(\"filename\", \"\")), (Path(str(layer.get(\"base\", \"\"))) / str(layer.get(\"filename\", \"\"))).read_bytes()) for layer in reversed(resolved)] # type: ignore" in cp_lines[i]:
        pass
    elif "StackLayerImage(layer[\"layer_name\"], layer[\"filename\"], (layer[\"base\"] / layer[\"filename\"]).read_bytes())" in cp_lines[i]:
        cp_lines[i] = "                                [StackLayerImage(str(layer.get(\"layer_name\", \"\")), str(layer.get(\"filename\", \"\")), (Path(str(layer.get(\"base\", \"\"))) / str(layer.get(\"filename\", \"\"))).read_bytes()) # type: ignore\n"
with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

with open("src/actool_linux/imagestack.py", "r") as f:
    im_lines = f.readlines()
for i in range(len(im_lines)):
    if "scale: int | None = None" in im_lines[i] or "scale: int = 1" in im_lines[i]:
        im_lines[i] = im_lines[i].replace("scale: int | None = None", "scale: int = 1")
    if "child_width = width // scale" in im_lines[i]:
        im_lines[i] = "    child_width = width // scale\n"
    if "child_height = height // scale" in im_lines[i]:
        im_lines[i] = "    child_height = height // scale\n"
    if "asset_scale = scale" in im_lines[i]:
        im_lines[i] = "    asset_scale = scale\n"
with open("src/actool_linux/imagestack.py", "w") as f:
    f.writelines(im_lines)

with open("src/actool_linux/lzfse_optimized.py", "r") as f:
    lz_lines = f.readlines()
for i in range(len(lz_lines)):
    if "def _encode_literals(self, data: bytes | bytearray) -> None:" in lz_lines[i]:
        lz_lines[i] = "    def _encode_literals(self, data: bytes | bytearray) -> None:\n        data = bytes(data)\n"
    if "self._encode_literals(" in lz_lines[i] and "bytearray" not in lz_lines[i] and "bytes" not in lz_lines[i]:
        lz_lines[i] = lz_lines[i].replace("chunk", "bytes(chunk)")

with open("src/actool_linux/lzfse_optimized.py", "w") as f:
    f.writelines(lz_lines)

