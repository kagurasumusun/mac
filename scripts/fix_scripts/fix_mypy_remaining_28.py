with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()
for i in range(len(cp_lines)):
    if "primary = shelf = shelf_wide = None" in cp_lines[i]:
        cp_lines[i] = "                primary: Any = None; shelf: Any = None; shelf_wide: Any = None\n"
    if "layers = [StackLayerImage(str(layer[\"layer_name\"]), str(layer[\"filename\"]), (layer[\"base\"] / str(layer[\"filename\"])).read_bytes())" in cp_lines[i]:
        cp_lines[i] = "        layers = [StackLayerImage(str(layer.get(\"layer_name\", \"\")), str(layer.get(\"filename\", \"\")), (Path(str(layer.get(\"base\", \"\"))) / str(layer.get(\"filename\", \"\"))).read_bytes()) for layer in reversed(resolved)] # type: ignore\n"
with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "tokens: tuple[AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken] = (AtlasKeyToken(24,0),AtlasKeyToken(1,9),AtlasKeyToken(2,181),AtlasKeyToken(8,page_dimension),AtlasKeyToken(12,scale),AtlasKeyToken(25,deployment_token))" in at_lines[i] and i > 295:
        at_lines[i] = "        tokens_page: tuple[AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken] = (AtlasKeyToken(24,0),AtlasKeyToken(1,9),AtlasKeyToken(2,181),AtlasKeyToken(8,page_dimension),AtlasKeyToken(12,scale),AtlasKeyToken(25,deployment_token))\n"
    if "link=AtlasLink(px,py,w,h,tokens)" in at_lines[i] and i > 295:
        at_lines[i] = "        link=AtlasLink(px,py,w,h,tokens_page)\n"
with open("src/actool_linux/atlas.py", "w") as f:
    f.writelines(at_lines)

