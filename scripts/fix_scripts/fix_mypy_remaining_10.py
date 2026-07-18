with open("src/actool_linux/imagestack.py", "r") as f:
    im_lines = f.readlines()
for i in range(len(im_lines)):
    if "child_width =" in im_lines[i] and "width // scale if scale else width" in im_lines[i]:
        im_lines[i] = im_lines[i].replace("width // scale if scale else width", "width // (scale or 1)")
    elif "child_height =" in im_lines[i] and "height // scale if scale else height" in im_lines[i]:
        im_lines[i] = im_lines[i].replace("height // scale if scale else height", "height // (scale or 1)")
    if "scale=" in im_lines[i] and "asset_scale" in im_lines[i]:
        pass
with open("src/actool_linux/imagestack.py", "w") as f:
    f.writelines(im_lines)

with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "placements.append((1,name,x,top,cw,ch,cpix))" in at_lines[i]:
        at_lines[i] = "            placements.append((1,name,x,top,cw,ch,cpix, (0,0,0,0), cw, ch))\n"
    elif "tuple[AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken]" in at_lines[i]:
        at_lines[i] = at_lines[i].replace("tuple[AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken]", "tuple[AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken]")

with open("src/actool_linux/atlas.py", "w") as f:
    f.writelines(at_lines)

