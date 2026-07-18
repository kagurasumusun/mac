with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()
for i in range(len(cp_lines)):
    if "primary: Any =" in cp_lines[i]:
        cp_lines[i] = "                primary: Any = None\n                shelf: Any = None\n                shelf_wide: Any = None\n"
    if "result[\"CFBundleIcons\"] = {\"CFBundlePrimaryIcon\": primary} # type: ignore" in cp_lines[i] or "result[\"TVTopShelfImage\"] = tv # type: ignore" in cp_lines[i] or "StackLayerImage(str(layer.get(\"layer_name\", \"\")), str(layer.get(\"filename\", \"\")), (Path(str(layer.get(\"base\", \"\"))) / str(layer.get(\"filename\", \"\"))).read_bytes()) for layer in reversed(resolved)] # type: ignore" in cp_lines[i]:
        pass
with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

with open("src/actool_linux/lzfse_optimized.py", "r") as f:
    lz_lines = f.readlines()
for i in range(len(lz_lines)):
    if "def _encode_literals(self, data: bytes | bytearray) -> None:" in lz_lines[i]:
        lz_lines[i] = "    def _encode_literals(self, data: bytes | bytearray) -> None:\n        data = bytes(data)\n"
with open("src/actool_linux/lzfse_optimized.py", "w") as f:
    f.writelines(lz_lines)

with open("src/actool_linux/imagestack.py", "r") as f:
    im_lines = f.readlines()
for i in range(len(im_lines)):
    if "asset_scale = scale" in im_lines[i]:
        im_lines[i] = im_lines[i].replace("asset_scale = scale", "asset_scale = scale or 1")
    if "child_width = width // scale" in im_lines[i]:
        im_lines[i] = im_lines[i].replace("width // scale", "width // (scale or 1)")
    if "child_height = height // scale" in im_lines[i]:
        im_lines[i] = im_lines[i].replace("height // scale", "height // (scale or 1)")
with open("src/actool_linux/imagestack.py", "w") as f:
    f.writelines(im_lines)

