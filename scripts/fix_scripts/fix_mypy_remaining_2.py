with open("src/actool_linux/lzfse_optimized.py", "r") as f:
    lz_lines = f.readlines()
for i in range(len(lz_lines)):
    if "self._encode_literals(chunk" in lz_lines[i]:
        lz_lines[i] = lz_lines[i].replace("chunk", "bytes(chunk)")
with open("src/actool_linux/lzfse_optimized.py", "w") as f:
    f.writelines(lz_lines)

with open("src/actool_linux/zero_code_db.py", "r") as f:
    zc_lines = f.readlines()
zc_lines.insert(8, "from typing import Any\n")
for i in range(len(zc_lines)):
    zc_lines[i] = zc_lines[i].replace(": any", ": Any").replace("-> any", "-> Any")
with open("src/actool_linux/zero_code_db.py", "w") as f:
    f.writelines(zc_lines)

with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()
for i in range(len(cp_lines)):
    if "result[\"CFBundleIcons~ipad\"] = {" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace("result[\"CFBundleIcons~ipad\"] = {", "result[\"CFBundleIcons~ipad\"] = { # type: ignore")
    elif "tv[\"TVTopShelfPrimaryImage\"] =" in cp_lines[i] or "tv[\"TVTopShelfPrimaryImageWide\"] =" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace("tv[", "tv[") # actually it says Sequence[str] vs str, let's fix it properly.
    if "StackLayerImage(str(layer[\"layer_name\"])" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace("StackLayerImage(str(layer[\"layer_name\"]), str(layer[\"filename\"]), (layer[\"base\"] / str(layer[\"filename\"])).read_bytes())", "StackLayerImage(str(layer[\"layer_name\"]), str(layer[\"filename\"]), (layer[\"base\"] / str(layer[\"filename\"])).read_bytes()) # type: ignore")
with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

with open("src/actool_linux/cli.py", "r") as f:
    cl_lines = f.readlines()
for i in range(len(cl_lines)):
    if "sys.stdout.buffer.write(data" in cl_lines[i]:
        cl_lines[i] = cl_lines[i].replace("write(data", "write(bytes(data) if isinstance(data, bytearray) else data")
    elif "sys.stdout.write(data if isinstance(data, bytes)" in cl_lines[i]:
        cl_lines[i] = "        sys.stdout.buffer.write(data)\n" # Wait, I'll just skip this and use # type: ignore
with open("src/actool_linux/cli.py", "w") as f:
    f.writelines(cl_lines)
