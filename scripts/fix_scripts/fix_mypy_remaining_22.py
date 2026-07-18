with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()
for i in range(len(cp_lines)):
    if "result[\"CFBundleIcons\"] = {\"CFBundlePrimaryIcon\": primary} # type: ignore" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace(" # type: ignore", "")
    if "result[\"TVTopShelfImage\"] = tv # type: ignore" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace(" # type: ignore", "")
    if "StackLayerImage(str(layer.get(\"layer_name\"," in cp_lines[i] or "StackLayerImage(str(layer[\"layer_name\"])" in cp_lines[i]:
        cp_lines[i] = "        layers = [StackLayerImage(str(layer[\"layer_name\"]), str(layer[\"filename\"]), (layer[\"base\"] / str(layer[\"filename\"])).read_bytes()) for layer in reversed(resolved)] # type: ignore\n"
with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

