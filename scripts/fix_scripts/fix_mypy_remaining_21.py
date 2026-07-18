with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "tokens=(AtlasKeyToken(24,0),AtlasKeyToken(1,9),AtlasKeyToken(2,181),AtlasKeyToken(8,page_dimension),AtlasKeyToken(12,scale),AtlasKeyToken(25,deployment_token))" in at_lines[i] or "tokens: tuple[AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken]=" in at_lines[i] or "tokens=" in at_lines[i] and "tuple[AtlasKeyToken" in at_lines[i]:
        at_lines[i] = "        tokens: tuple[AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken] = (AtlasKeyToken(24,0),AtlasKeyToken(1,9),AtlasKeyToken(2,181),AtlasKeyToken(8,page_dimension),AtlasKeyToken(12,scale),AtlasKeyToken(25,deployment_token))\n"

with open("src/actool_linux/atlas.py", "w") as f:
    f.writelines(at_lines)

with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()
for i in range(len(cp_lines)):
    if "result[\"CFBundleIcons\"] = {\"CFBundlePrimaryIcon\": primary} # type: ignore" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace(" # type: ignore", "")
    if "result[\"TVTopShelfImage\"] = tv # type: ignore" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace(" # type: ignore", "")
    if "StackLayerImage(str(layer.get(\"layer_name\"," in cp_lines[i] or "StackLayerImage(str(layer[\"layer_name\"])" in cp_lines[i]:
        cp_lines[i] = "        layers = [StackLayerImage(str(layer[\"layer_name\"]), str(layer[\"filename\"]), (layer[\"base\"] / str(layer[\"filename\"])).read_bytes()) for layer in reversed(resolved)] # type: ignore\n"
    if "result: dict[str, Any] =" in cp_lines[i] or "result: dict[str, object] =" in cp_lines[i]:
        pass
    if "tv: dict[str, Any] =" in cp_lines[i] or "tv: dict[str, object] =" in cp_lines[i]:
        pass
with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

with open("src/actool_linux/imagestack.py", "r") as f:
    im_lines = f.readlines()
for i in range(len(im_lines)):
    if "def imagestack_renditions(" in im_lines[i]:
        im_lines[i] = im_lines[i].replace("scale: int | None = None", "scale: int = 1")
    if "child_width = width // (scale if scale is not None else 1)" in im_lines[i]:
        im_lines[i] = im_lines[i].replace("child_width = width // (scale if scale is not None else 1)", "child_width = width // scale")
    if "child_height = height // (scale if scale is not None else 1)" in im_lines[i]:
        im_lines[i] = im_lines[i].replace("child_height = height // (scale if scale is not None else 1)", "child_height = height // scale")
    if "asset_scale = scale if scale is not None else 1" in im_lines[i]:
        im_lines[i] = im_lines[i].replace("asset_scale = scale if scale is not None else 1", "asset_scale = scale")
with open("src/actool_linux/imagestack.py", "w") as f:
    f.writelines(im_lines)

with open("src/actool_linux/lzfse_optimized.py", "r") as f:
    lz_lines = f.readlines()
for i in range(len(lz_lines)):
    if "def _encode_literals(self, data: bytes)" in lz_lines[i]:
        lz_lines[i] = "    def _encode_literals(self, data: bytes | bytearray) -> None:\n"
    if "self._encode_literals(" in lz_lines[i] and "bytearray" in lz_lines[i]:
        pass
with open("src/actool_linux/lzfse_optimized.py", "w") as f:
    f.writelines(lz_lines)
