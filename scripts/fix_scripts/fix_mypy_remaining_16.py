with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "placements: list[tuple[int, str, int, int, int, int, bytes]] = []" in at_lines[i]:
        at_lines[i] = "    placements: list[tuple[int, str, int, int, int, int, bytes, tuple[int, int, int, int], int, int]] = []\n"
    if "placements.append((page,name,x,y,w,h,pix))" in at_lines[i]:
        at_lines[i] = "        placements.append((page,name,x,y,w,h,pix,(0,0,0,0),w,h)); x+=w; row_h=max(row_h,h)\n"
    if "tuple[AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken]" in at_lines[i]:
        at_lines[i] = at_lines[i].replace("tuple[AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken]", "tuple[AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken]")
    if "for page, name, x, y, cw, ch, cpix in placements:" in at_lines[i] or "for page, name, px, py, w, h, pix in placements:" in at_lines[i] or "for page, name, px, py, w, h, pix in sorted(" in at_lines[i]:
        at_lines[i] = at_lines[i].replace("cpix in", "cpix, _, _, _ in").replace("pix in", "pix, _, _, _ in")
    if "aw=max(px+w for _,_,px,_,w,_,_ in page_items); ah=max(py+h for _,_,_,py,_,h,_ in page_items)" in at_lines[i]:
        at_lines[i] = "        aw=max(px+w for _,_,px,_,w,_,_,_,_,_ in page_items); ah=max(py+h for _,_,_,py,_,h,_,_,_,_ in page_items)\n"
    if "for _,_,px,py,w,h,pix in page_items:" in at_lines[i]:
        at_lines[i] = "        for _,_,px,py,w,h,pix,_,_,_ in page_items:\n"
    if "for page_dimension,name,px,py,w,h,_ in placements:" in at_lines[i]:
        at_lines[i] = "    for page_dimension,name,px,py,w,h,_,_,_,_ in placements:\n"

with open("src/actool_linux/atlas.py", "w") as f:
    f.writelines(at_lines)

with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()
for i in range(len(cp_lines)):
    if "tv: dict[str, Any] = {}" in cp_lines[i]:
        pass
    if "def _partial_info(" in cp_lines[i]:
        pass
    if "StackLayerImage(str(layer.get(\"layer_name\"," in cp_lines[i] or "StackLayerImage(str(layer[\"layer_name\"])" in cp_lines[i]:
        cp_lines[i] = "        layers = [StackLayerImage(str(layer[\"layer_name\"]), str(layer[\"filename\"]), (layer[\"base\"] / str(layer[\"filename\"])).read_bytes()) for layer in reversed(resolved)] # type: ignore\n"
    if "result[\"CFBundleIcons\"] = {\"CFBundlePrimaryIcon\": primary}" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace("result[\"CFBundleIcons\"]", "result[\"CFBundleIcons\"] # type: ignore")
    if "result[\"TVTopShelfImage\"] = tv" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace("result[\"TVTopShelfImage\"] = tv", "result[\"TVTopShelfImage\"] = tv # type: ignore")

with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

