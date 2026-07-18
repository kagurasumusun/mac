with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()
for i in range(len(cp_lines)):
    if "        primary = {" in cp_lines[i] and "CFBundleIconFiles" in cp_lines[i+1]:
        cp_lines[i] = "        primary_dict = {\n"
    if "result[\"CFBundleIcons\"] = {\"CFBundlePrimaryIcon\": primary}" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace("primary}", "primary_dict}")

with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

with open("src/actool_linux/lzfse_optimized.py", "r") as f:
    lz_lines = f.readlines()
for i in range(len(lz_lines)):
    if "self._encode_literals(chunk)" in lz_lines[i]:
        lz_lines[i] = lz_lines[i].replace("chunk", "bytes(chunk)")
    elif "self._encode_literals(chunk[match_len:])" in lz_lines[i]:
        lz_lines[i] = lz_lines[i].replace("chunk[match_len:]", "bytes(chunk[match_len:])")
with open("src/actool_linux/lzfse_optimized.py", "w") as f:
    f.writelines(lz_lines)

with open("src/actool_linux/imagestack.py", "r") as f:
    im_lines = f.readlines()
for i in range(len(im_lines)):
    if "child_width = width // scale" in im_lines[i] and "or" not in im_lines[i]:
        im_lines[i] = "    child_width = width // (scale or 1)\n"
    elif "child_height = height // scale" in im_lines[i] and "or" not in im_lines[i]:
        im_lines[i] = "    child_height = height // (scale or 1)\n"
    elif "asset_scale = scale\n" == im_lines[i]:
        im_lines[i] = "    asset_scale = scale or 1\n"
with open("src/actool_linux/imagestack.py", "w") as f:
    f.writelines(im_lines)

