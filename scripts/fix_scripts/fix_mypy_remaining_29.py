with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()
for i in range(len(cp_lines)):
    if "layers = [StackLayerImage(str(layer[\"layer_name\"]), str(layer[\"filename\"]), (layer[\"base\"] / str(layer[\"filename\"])).read_bytes())" in cp_lines[i]:
        cp_lines[i] = "        layers = [StackLayerImage(str(layer.get(\"layer_name\", \"\")), str(layer.get(\"filename\", \"\")), (layer[\"base\"] / str(layer.get(\"filename\", \"\"))).read_bytes()) # type: ignore\n"
        cp_lines[i+1] = "                  for layer in reversed(resolved)]\n"
with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

