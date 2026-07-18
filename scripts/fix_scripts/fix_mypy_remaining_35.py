with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()
for i in range(len(cp_lines)):
    if "layers = [StackLayerImage(layer[\"layer_name\"], layer[\"filename\"], (layer[\"base\"] / layer[\"filename\"]).read_bytes())" in cp_lines[i] or "[StackLayerImage(layer[\"layer_name\"], layer[\"filename\"], (layer[\"base\"] / layer[\"filename\"]).read_bytes())" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace("[StackLayerImage(layer[\"layer_name\"], layer[\"filename\"], (layer[\"base\"] / layer[\"filename\"]).read_bytes())", "[StackLayerImage(str(layer.get(\"layer_name\", \"\")), str(layer.get(\"filename\", \"\")), (Path(str(layer.get(\"base\", \"\"))) / str(layer.get(\"filename\", \"\"))).read_bytes())")
    if "tv: dict[str, Sequence[str]] = {}" in cp_lines[i] or "tv: dict[str, Any] = {}" in cp_lines[i] or "tv: dict[str, str] = {}" in cp_lines[i]:
        cp_lines[i] = "                tv: dict[str, Any] = {}\n"
with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

with open("src/actool_linux/imagestack.py", "r") as f:
    im_lines = f.readlines()
for i in range(len(im_lines)):
    if "scale: int | None = None" in im_lines[i] or "scale: int = 1" in im_lines[i]:
        im_lines[i] = im_lines[i].replace("scale: int | None = None", "scale: int = 1")
    if "child_width = width // scale" in im_lines[i]:
        im_lines[i] = im_lines[i].replace("width // scale", "width // (scale or 1)")
    if "child_height = height // scale" in im_lines[i]:
        im_lines[i] = im_lines[i].replace("height // scale", "height // (scale or 1)")
with open("src/actool_linux/imagestack.py", "w") as f:
    f.writelines(im_lines)

with open("src/actool_linux/lzfse_optimized.py", "r") as f:
    lz_lines = f.readlines()
for i in range(len(lz_lines)):
    if "self._encode_literals(" in lz_lines[i] and "bytearray" in lz_lines[i]:
        lz_lines[i] = lz_lines[i].replace("chunk", "bytes(chunk)")

with open("src/actool_linux/lzfse_optimized.py", "w") as f:
    f.writelines(lz_lines)

