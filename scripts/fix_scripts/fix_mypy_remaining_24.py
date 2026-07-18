with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()
for i in range(len(cp_lines)):
    if "result[\"CFBundleIcons\"] = {\"CFBundlePrimaryIcon\": primary}" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace("result[\"CFBundleIcons\"] = {\"CFBundlePrimaryIcon\": primary}", "result[\"CFBundleIcons\"] = {\"CFBundlePrimaryIcon\": primary} # type: ignore")
    if "result[\"TVTopShelfImage\"] = tv" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace("result[\"TVTopShelfImage\"] = tv", "result[\"TVTopShelfImage\"] = tv # type: ignore")

with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "tokens=(AtlasKeyToken(24,0),AtlasKeyToken(1,9),AtlasKeyToken(2,181),AtlasKeyToken(8,page_dimension),AtlasKeyToken(12,scale),AtlasKeyToken(25,deployment_token))" in at_lines[i] and i > 295:
        at_lines[i] = "        tokens_2: tuple[AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken] = (AtlasKeyToken(24,0),AtlasKeyToken(1,9),AtlasKeyToken(2,181),AtlasKeyToken(8,page_dimension),AtlasKeyToken(12,scale),AtlasKeyToken(25,deployment_token))\n"
    elif "link=AtlasLink(px,py,w,h,tokens)" in at_lines[i] and i > 295:
        at_lines[i] = "        link=AtlasLink(px,py,w,h,tokens_2)\n"

with open("src/actool_linux/atlas.py", "w") as f:
    f.writelines(at_lines)

with open("src/actool_linux/texture_gradient_stack.py", "r") as f:
    tx_lines = f.readlines()
for i in range(len(tx_lines)):
    if "def _pack_value(value: Any) -> bytes:" in tx_lines[i]:
        pass
    if "value.encode(\"utf-8\")" in tx_lines[i]:
        tx_lines[i] = tx_lines[i].replace("value.encode(\"utf-8\")", "str(value).encode(\"utf-8\")")

with open("src/actool_linux/texture_gradient_stack.py", "w") as f:
    f.writelines(tx_lines)

with open("src/actool_linux/lzfse_optimized.py", "r") as f:
    lz_lines = f.readlines()
for i in range(len(lz_lines)):
    if "self._encode_literals(chunk)" in lz_lines[i]:
        lz_lines[i] = lz_lines[i].replace("chunk", "bytes(chunk)")
    if "self._encode_literals(chunk[match_len:])" in lz_lines[i]:
        lz_lines[i] = lz_lines[i].replace("chunk[match_len:]", "bytes(chunk[match_len:])")

with open("src/actool_linux/lzfse_optimized.py", "w") as f:
    f.writelines(lz_lines)

with open("src/actool_linux/zero_code_db.py", "r") as f:
    zc_lines = f.readlines()
for i in range(len(zc_lines)):
    if "def test(" in zc_lines[i]:
        pass
    if "builtins.any" in zc_lines[i]:
        pass
    zc_lines[i] = zc_lines[i].replace(": any", ": Any").replace("-> any", "-> Any")

with open("src/actool_linux/zero_code_db.py", "w") as f:
    f.writelines(zc_lines)

