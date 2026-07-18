with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "for page, name, x, top, cw, ch, cpix in placements:" in at_lines[i] or "for page, name, px, py, w, h, pix in placements:" in at_lines[i] or "for page, name, px, py, w, h, pix in sorted(" in at_lines[i]:
        at_lines[i] = at_lines[i].replace("cpix in", "cpix, _, _, _ in").replace("pix in", "pix, _, _, _ in")
with open("src/actool_linux/atlas.py", "w") as f:
    f.writelines(at_lines)

with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()
for i in range(len(cp_lines)):
    if "tv: dict[str, str] = {}" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace("dict[str, str]", "dict[str, object]")
    if "StackLayerImage(str(layer[\"layer_name\"])" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace("StackLayerImage(str(layer[\"layer_name\"]), str(layer[\"filename\"]), (layer[\"base\"] / str(layer[\"filename\"])).read_bytes())", "StackLayerImage(str(layer[\"layer_name\"]), str(layer[\"filename\"]), (layer[\"base\"] / str(layer[\"filename\"])).read_bytes()) # type: ignore")

with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

