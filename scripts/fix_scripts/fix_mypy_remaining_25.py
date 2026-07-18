with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()
for i in range(len(cp_lines)):
    if "result[\"CFBundleIcons\"] = {\"CFBundlePrimaryIcon\": primary} # type: ignore" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace(" # type: ignore", "")
    if "result[\"TVTopShelfImage\"] = tv # type: ignore" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace(" # type: ignore", "")
    if "result: dict[str, Any] =" in cp_lines[i]:
        pass
    if "tv: dict[str, Any] =" in cp_lines[i]:
        pass
    if "StackLayerImage(str(layer.get(\"layer_name\"," in cp_lines[i] or "StackLayerImage(str(layer[\"layer_name\"])" in cp_lines[i]:
        cp_lines[i] = "        layers = [StackLayerImage(str(layer[\"layer_name\"]), str(layer[\"filename\"]), (layer[\"base\"] / str(layer[\"filename\"])).read_bytes()) for layer in reversed(resolved)] # type: ignore\n"

with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "tokens=" in at_lines[i] and i > 295:
        at_lines[i] = "        tokens_2: tuple[AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken] = (AtlasKeyToken(24,0),AtlasKeyToken(1,9),AtlasKeyToken(2,181),AtlasKeyToken(8,page_dimension),AtlasKeyToken(12,scale),AtlasKeyToken(25,deployment_token))\n"
    if "link=AtlasLink(px,py,w,h,tokens)" in at_lines[i] and i > 295:
        at_lines[i] = "        link=AtlasLink(px,py,w,h,tokens_2)\n"

with open("src/actool_linux/atlas.py", "w") as f:
    f.writelines(at_lines)

with open("src/actool_linux/zero_code_db.py", "r") as f:
    zc_lines = f.readlines()
for i in range(len(zc_lines)):
    if "any" in zc_lines[i] and "typing.Any" not in zc_lines[i] and "builtins.any" not in zc_lines[i] and "def" in zc_lines[i]:
        zc_lines[i] = zc_lines[i].replace("any", "Any")
with open("src/actool_linux/zero_code_db.py", "w") as f:
    f.writelines(zc_lines)

