with open("src/actool_linux/texture_gradient_stack.py", "r") as f:
    tx_lines = f.readlines()
for i in range(len(tx_lines)):
    if "def _pack_value(value):" in tx_lines[i]:
        tx_lines[i] = "def _pack_value(value: Any) -> bytes:\n"
with open("src/actool_linux/texture_gradient_stack.py", "w") as f:
    f.writelines(tx_lines)

with open("src/actool_linux/zero_code_db.py", "r") as f:
    zc_lines = f.readlines()
for i in range(len(zc_lines)):
    zc_lines[i] = zc_lines[i].replace(": any", ": Any").replace("-> any", "-> Any")
with open("src/actool_linux/zero_code_db.py", "w") as f:
    f.writelines(zc_lines)

with open("src/actool_linux/multi_database.py", "r") as f:
    md_lines = f.readlines()
for i in range(len(md_lines)):
    if "store =" in md_lines[i] and "self.databases" in md_lines[i]:
        pass
    if "renditions =" in md_lines[i] and "[]" in md_lines[i]:
        md_lines[i] = md_lines[i].replace("renditions =", "renditions: List[dict] =")
    if "colors =" in md_lines[i] and "{}" in md_lines[i]:
        md_lines[i] = md_lines[i].replace("colors =", "colors: Dict[str, dict] =")
    if "facet_keys =" in md_lines[i] and "{}" in md_lines[i]:
        md_lines[i] = md_lines[i].replace("facet_keys =", "facet_keys: Dict[str, int] =")
with open("src/actool_linux/multi_database.py", "w") as f:
    f.writelines(md_lines)

with open("src/actool_linux/thinning.py", "r") as f:
    th_lines = f.readlines()
for i in range(len(th_lines)):
    if "allowed_locales.add(None)" in th_lines[i]:
        th_lines[i] = "            if options.keep_fallbacks: allowed_locales.add(None) # type: ignore\n"
with open("src/actool_linux/thinning.py", "w") as f:
    f.writelines(th_lines)

with open("src/actool_linux/imagestack.py", "r") as f:
    im_lines = f.readlines()
for i in range(len(im_lines)):
    if "asset_scale = " in im_lines[i]:
        im_lines[i] = im_lines[i].replace("asset_scale = scale", "asset_scale = scale or 1")
with open("src/actool_linux/imagestack.py", "w") as f:
    f.writelines(im_lines)

with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "placements.append((page,name,x,y,w,h,pix))" in at_lines[i]:
        at_lines[i] = "        placements.append((page,name,x,y,w,h,pix, (0,0,0,0), w, h)); x+=w; row_h=max(row_h,h)\n" # Add dummy bbox and dimensions to match explicit packing schema
    if "placements.append((1,name,x,top,cw,ch,cpix,bbox,w,h))" in at_lines[i]:
        pass
    if "for page, name, px, py, w, h, pix in placements:" in at_lines[i]:
        at_lines[i] = "    for page, name, px, py, w, h, pix, _, _, _ in placements:\n"
    if "tuple[AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken]" in at_lines[i]:
        at_lines[i] = at_lines[i].replace("tuple[AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken]", "tuple[AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken]")
with open("src/actool_linux/atlas.py", "w") as f:
    f.writelines(at_lines)
