import re
with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()
for i in range(len(cp_lines)):
    if "def _partial_info(" in cp_lines[i]:
        cp_lines[i] = "def _partial_info(catalogs: Iterable[Catalog], options: CompileOptions) -> dict[str, Any]:\n"
    if "result: dict[str, object] = {}" in cp_lines[i]:
        cp_lines[i] = "    result: dict[str, Any] = {}\n"
    if "tv: dict[str, object] = {}" in cp_lines[i]:
        cp_lines[i] = "                tv: dict[str, Any] = {}\n"

with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

with open("src/actool_linux/texture_gradient_stack.py", "r") as f:
    tx_lines = f.readlines()
for i in range(len(tx_lines)):
    if "value.encode" in tx_lines[i]:
        tx_lines[i] = tx_lines[i].replace("value.encode", "str(value).encode")
with open("src/actool_linux/texture_gradient_stack.py", "w") as f:
    f.writelines(tx_lines)

with open("src/actool_linux/zero_code_db.py", "r") as f:
    zc_lines = f.readlines()
for i in range(len(zc_lines)):
    if "def test(" in zc_lines[i]:
        pass
    if ": Any" in zc_lines[i] and "typing" not in zc_lines[i]:
        pass
with open("src/actool_linux/zero_code_db.py", "w") as f:
    f.writelines(zc_lines)

with open("src/actool_linux/imagestack.py", "r") as f:
    im_lines = f.readlines()
for i in range(len(im_lines)):
    if "h * (scale or 1)" in im_lines[i]:
        im_lines[i] = im_lines[i].replace("h * (scale or 1)", "h * (scale if scale is not None else 1)")
    if "w * (scale or 1)" in im_lines[i]:
        im_lines[i] = im_lines[i].replace("w * (scale or 1)", "w * (scale if scale is not None else 1)")
with open("src/actool_linux/imagestack.py", "w") as f:
    f.writelines(im_lines)

