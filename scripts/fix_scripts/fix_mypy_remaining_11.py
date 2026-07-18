with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "aw=max(px+w for _,_,px,_,w,_,_ in page_items); ah=max(py+h for _,_,_,py,_,h,_ in page_items)" in at_lines[i]:
        at_lines[i] = "        aw=max(px+w for _,_,px,_,w,_,_,_,_,_ in page_items); ah=max(py+h for _,_,_,py,_,h,_,_,_,_ in page_items)\n"
    if "for _,_,px,py,w,h,pix in page_items:" in at_lines[i]:
        at_lines[i] = "        for _,_,px,py,w,h,pix,_,_,_ in page_items:\n"
    if "for page_dimension,name,px,py,w,h,_ in placements:" in at_lines[i]:
        at_lines[i] = "    for page_dimension,name,px,py,w,h,_,_,_,_ in placements:\n"

with open("src/actool_linux/atlas.py", "w") as f:
    f.writelines(at_lines)

with open("src/actool_linux/zero_code_db.py", "r") as f:
    zc_lines = f.readlines()
for i in range(len(zc_lines)):
    zc_lines[i] = zc_lines[i].replace("any?", "Any")

with open("src/actool_linux/zero_code_db.py", "w") as f:
    f.writelines(zc_lines)

with open("src/actool_linux/texture_gradient_stack.py", "r") as f:
    tx_lines = f.readlines()
for i in range(len(tx_lines)):
    if "any?" in tx_lines[i]:
        tx_lines[i] = tx_lines[i].replace("any?", "Any")
with open("src/actool_linux/texture_gradient_stack.py", "w") as f:
    f.writelines(tx_lines)

with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()
for i in range(len(cp_lines)):
    if "result[\"CFBundleIcons\"] = {\"CFBundlePrimaryIcon\": primary}" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace("result[\"CFBundleIcons\"]", "result[\"CFBundleIcons\"] # type: ignore")
    if "result[\"TVTopShelfImage\"] = tv" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace("result[\"TVTopShelfImage\"] = tv", "result[\"TVTopShelfImage\"] = tv # type: ignore")
    if "def compile_brand_assets(" in cp_lines[i]:
        pass

with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

