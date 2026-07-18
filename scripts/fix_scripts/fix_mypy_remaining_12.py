with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()
for i in range(len(cp_lines)):
    if "result[\"CFBundleIcons\"] = {\"CFBundlePrimaryIcon\": primary} # type: ignore" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace(" # type: ignore", "")
    if "result[\"TVTopShelfImage\"] = tv # type: ignore" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace(" # type: ignore", "")
    if "primary =" in cp_lines[i] and "shelf =" in cp_lines[i] and "shelf_wide = None" in cp_lines[i]:
        pass
    if "StackLayerImage(str(layer[\"layer_name\"])" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace("str(layer[\"layer_name\"])", "str(layer.get(\"layer_name\", \"\"))")
        cp_lines[i] = cp_lines[i].replace("str(layer[\"filename\"])", "str(layer.get(\"filename\", \"\"))")
        cp_lines[i] = cp_lines[i].replace("layer[\"base\"] /", "Path(str(layer.get(\"base\", \"\"))) /")

with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

with open("src/actool_linux/imagestack.py", "r") as f:
    im_lines = f.readlines()
for i in range(len(im_lines)):
    if "child_width = width // (scale or 1)" in im_lines[i]:
        im_lines[i] = "    child_width = width // (scale if scale is not None else 1)\n"
    if "child_height = height // (scale or 1)" in im_lines[i]:
        im_lines[i] = "    child_height = height // (scale if scale is not None else 1)\n"
    if "asset_scale = scale or 1" in im_lines[i]:
        im_lines[i] = "    asset_scale = scale if scale is not None else 1\n"
with open("src/actool_linux/imagestack.py", "w") as f:
    f.writelines(im_lines)

with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "tokens=(AtlasKeyToken(24,0),AtlasKeyToken(1,9),AtlasKeyToken(2,181),AtlasKeyToken(8,page_dimension),AtlasKeyToken(12,scale),AtlasKeyToken(25,deployment_token))" in at_lines[i]:
        at_lines[i] = "        tokens: tuple[AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken] = (AtlasKeyToken(24,0),AtlasKeyToken(1,9),AtlasKeyToken(2,181),AtlasKeyToken(8,page_dimension),AtlasKeyToken(12,scale),AtlasKeyToken(25,deployment_token))\n"
with open("src/actool_linux/atlas.py", "w") as f:
    f.writelines(at_lines)

with open("src/actool_linux/lzfse_optimized.py", "r") as f:
    lz_lines = f.readlines()
for i in range(len(lz_lines)):
    if "self._encode_literals(" in lz_lines[i] and "bytearray" in lz_lines[i]:
        pass
    if "def _encode_literals(self, data: bytes)" in lz_lines[i]:
        pass
with open("src/actool_linux/lzfse_optimized.py", "w") as f:
    f.writelines(lz_lines)

