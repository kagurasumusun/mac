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
    if "result[\"CFBundleIcons~ipad\"] = {" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace("result[\"CFBundleIcons~ipad\"] = {", "result[\"CFBundleIcons~ipad\"] = { # type: ignore")
    if "StackLayerImage(str(layer[\"layer_name\"])" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace("StackLayerImage(str(layer[\"layer_name\"]), str(layer[\"filename\"]), (layer[\"base\"] / str(layer[\"filename\"])).read_bytes())", "StackLayerImage(str(layer[\"layer_name\"]), str(layer[\"filename\"]), (layer[\"base\"] / str(layer[\"filename\"])).read_bytes()) # type: ignore")

with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

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

