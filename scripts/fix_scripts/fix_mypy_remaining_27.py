with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()
for i in range(len(cp_lines)):
    if "result[\"CFBundleIcons\"] = {\"CFBundlePrimaryIcon\": primary} # type: ignore" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace(" # type: ignore", "")
    if "result[\"TVTopShelfImage\"] = tv # type: ignore" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace(" # type: ignore", "")
    if "primary = shelf = shelf_wide = None" in cp_lines[i]:
        cp_lines[i] = "                primary: Any = None; shelf: Any = None; shelf_wide: Any = None\n"
    if "layers = [StackLayerImage(str(layer[\"layer_name\"]), str(layer[\"filename\"]), (layer[\"base\"] / str(layer[\"filename\"])).read_bytes())" in cp_lines[i]:
        cp_lines[i] = "        layers = [StackLayerImage(str(layer.get(\"layer_name\", \"\")), str(layer.get(\"filename\", \"\")), (Path(str(layer.get(\"base\", \"\"))) / str(layer.get(\"filename\", \"\"))).read_bytes()) for layer in reversed(resolved)] # type: ignore\n"

with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "tokens: tuple[AtlasKeyToken," in at_lines[i] and i > 295 and "tokens_page" not in at_lines[i]:
        pass # this line was causing redef, need to rename
    if "tokens=(AtlasKeyToken(24,0)" in at_lines[i] and i > 295:
        at_lines[i] = "        tokens_page: tuple[AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken] = (AtlasKeyToken(24,0),AtlasKeyToken(1,9),AtlasKeyToken(2,181),AtlasKeyToken(8,page_dimension),AtlasKeyToken(12,scale),AtlasKeyToken(25,deployment_token))\n"
    elif "link=AtlasLink(px,py,w,h,tokens)" in at_lines[i] and i > 295:
        at_lines[i] = "        link=AtlasLink(px,py,w,h,tokens_page)\n"

with open("src/actool_linux/atlas.py", "w") as f:
    f.writelines(at_lines)

with open("src/actool_linux/texture_gradient_stack.py", "r") as f:
    tx_lines = f.readlines()
for i in range(len(tx_lines)):
    if "any" in tx_lines[i] and "typing.Any" not in tx_lines[i] and "def " in tx_lines[i]:
        tx_lines[i] = tx_lines[i].replace("any", "Any")
with open("src/actool_linux/texture_gradient_stack.py", "w") as f:
    f.writelines(tx_lines)

with open("src/actool_linux/zero_code_db.py", "r") as f:
    zc_lines = f.readlines()
for i in range(len(zc_lines)):
    if "builtins.any" in zc_lines[i] or "typing.Any" in zc_lines[i]:
        pass
    zc_lines[i] = zc_lines[i].replace("builtins.any", "Any")
with open("src/actool_linux/zero_code_db.py", "w") as f:
    f.writelines(zc_lines)

