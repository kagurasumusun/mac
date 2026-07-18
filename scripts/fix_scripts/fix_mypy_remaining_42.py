with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()
has_any = any("from typing import Any" in line for line in cp_lines)
if not has_any:
    for i in range(len(cp_lines)):
        if "from typing import " in cp_lines[i] and "Any" not in cp_lines[i]:
            cp_lines[i] = cp_lines[i].replace("from typing import ", "from typing import Any, ")
            has_any = True
            break
if not has_any:
    cp_lines.insert(6, "from typing import Any\n")
for i in range(len(cp_lines)):
    if "result[\"CFBundleIcons\"] = {\"CFBundlePrimaryIcon\": primary}" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace("result[\"CFBundleIcons\"] = {\"CFBundlePrimaryIcon\": primary}", "result[\"CFBundleIcons\"] = {\"CFBundlePrimaryIcon\": primary} # type: ignore")
    if "result[\"TVTopShelfImage\"] = tv" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace("result[\"TVTopShelfImage\"] = tv", "result[\"TVTopShelfImage\"] = tv # type: ignore")

with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

with open("src/actool_linux/lzfse_optimized.py", "r") as f:
    lz_lines = f.readlines()
for i in range(len(lz_lines)):
    if "self._encode_literals(chunk)" in lz_lines[i]:
        lz_lines[i] = lz_lines[i].replace("self._encode_literals(chunk)", "self._encode_literals(bytes(chunk))")
    if "self._encode_literals(chunk[match_len:])" in lz_lines[i]:
        lz_lines[i] = lz_lines[i].replace("self._encode_literals(chunk[match_len:])", "self._encode_literals(bytes(chunk[match_len:]))")

with open("src/actool_linux/lzfse_optimized.py", "w") as f:
    f.writelines(lz_lines)

with open("src/actool_linux/imagestack.py", "r") as f:
    im_lines = f.readlines()
for i in range(len(im_lines)):
    if "child_width = width // (scale if scale is not None else 1)" in im_lines[i]:
        im_lines[i] = "    child_width = width // (scale or 1)\n"
    if "child_height = height // (scale if scale is not None else 1)" in im_lines[i]:
        im_lines[i] = "    child_height = height // (scale or 1)\n"
    if "asset_scale = scale if scale is not None else 1" in im_lines[i]:
        im_lines[i] = "    asset_scale = scale or 1\n"
with open("src/actool_linux/imagestack.py", "w") as f:
    f.writelines(im_lines)

