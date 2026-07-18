with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "tokens_page: tuple[AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken] = (AtlasKeyToken(24,0),AtlasKeyToken(1,9),AtlasKeyToken(2,181),AtlasKeyToken(8,page_dimension),AtlasKeyToken(12,scale),AtlasKeyToken(25,deployment_token))" in at_lines[i] and "for page_dimension,name,px,py,w,h,_,_,_,_ in placements:" not in at_lines[i-1]:
        at_lines[i] = ""
    elif "link=AtlasLink(px,py,w,h,tokens_page)" in at_lines[i] and "tokens_page: tuple" not in at_lines[i-1]:
        at_lines[i] = ""

with open("src/actool_linux/atlas.py", "w") as f:
    f.writelines(at_lines)

with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()
for i in range(len(cp_lines)):
    if "result[\"CFBundleIcons\"] = {\"CFBundlePrimaryIcon\": primary}" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace("result[\"CFBundleIcons\"] = {\"CFBundlePrimaryIcon\": primary}", "result[\"CFBundleIcons\"] = {\"CFBundlePrimaryIcon\": primary} # type: ignore")
    if "result[\"TVTopShelfImage\"] = tv" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace("result[\"TVTopShelfImage\"] = tv", "result[\"TVTopShelfImage\"] = tv # type: ignore")
    if "StackLayerImage(str(layer.get(\"layer_name\", \"\")), str(layer.get(\"filename\", \"\")), (layer[\"base\"] / str(layer.get(\"filename\", \"\"))).read_bytes())" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace("(layer[\"base\"] / str(layer.get(\"filename\", \"\"))).read_bytes()", "(Path(str(layer.get(\"base\", \"\"))) / str(layer.get(\"filename\", \"\"))).read_bytes()")
with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

