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
with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

with open("src/actool_linux/zero_code_db.py", "r") as f:
    zc_lines = f.readlines()
for i in range(len(zc_lines)):
    if "builtins.any" in zc_lines[i]:
        pass
    zc_lines[i] = zc_lines[i].replace(": any", ": Any").replace("-> any", "-> Any")
has_any_zc = any("from typing import Any" in line for line in zc_lines)
if not has_any_zc:
    for i in range(len(zc_lines)):
        if "from typing import " in zc_lines[i] and "Any" not in zc_lines[i]:
            zc_lines[i] = zc_lines[i].replace("from typing import ", "from typing import Any, ")
            has_any_zc = True
            break
if not has_any_zc:
    zc_lines.insert(6, "from typing import Any\n")
with open("src/actool_linux/zero_code_db.py", "w") as f:
    f.writelines(zc_lines)

with open("src/actool_linux/texture_gradient_stack.py", "r") as f:
    tx_lines = f.readlines()
has_any_tx = any("from typing import Any" in line for line in tx_lines)
if not has_any_tx:
    tx_lines.insert(6, "from typing import Any\n")
with open("src/actool_linux/texture_gradient_stack.py", "w") as f:
    f.writelines(tx_lines)

with open("src/actool_linux/imagestack.py", "r") as f:
    im_lines = f.readlines()
for i in range(len(im_lines)):
    if "scale=" in im_lines[i] and "scale=scale" in im_lines[i]:
        pass
    if "child_width = width // (scale if scale is not None else 1)" in im_lines[i]:
        pass
with open("src/actool_linux/imagestack.py", "w") as f:
    f.writelines(im_lines)

with open("src/actool_linux/lzfse_optimized.py", "r") as f:
    lz_lines = f.readlines()
for i in range(len(lz_lines)):
    if "self._encode_literals(chunk)" in lz_lines[i]:
        lz_lines[i] = lz_lines[i].replace("self._encode_literals(chunk)", "self._encode_literals(bytes(chunk))")
    if "self._encode_literals(chunk[match_len:])" in lz_lines[i]:
        lz_lines[i] = lz_lines[i].replace("self._encode_literals(chunk[match_len:])", "self._encode_literals(bytes(chunk[match_len:]))")
with open("src/actool_linux/lzfse_optimized.py", "w") as f:
    f.writelines(lz_lines)

with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "tuple[AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken]" in at_lines[i] and "tokens: tuple" in at_lines[i]:
        at_lines[i] = at_lines[i].replace("tuple[AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken]", "tuple[AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken]")
with open("src/actool_linux/atlas.py", "w") as f:
    f.writelines(at_lines)
