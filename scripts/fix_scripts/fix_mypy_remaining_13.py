with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "tokens: tuple[AtlasKeyToken," in at_lines[i] and i > 290:
        at_lines[i] = at_lines[i].replace("tokens: tuple[AtlasKeyToken", "tokens")

with open("src/actool_linux/atlas.py", "w") as f:
    f.writelines(at_lines)

with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()
for i in range(len(cp_lines)):
    if "result[\"CFBundleIcons\"]" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace(" # type: ignore", "")
    if "result[\"TVTopShelfImage\"]" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace(" # type: ignore", "")
    if "StackLayerImage(str(layer.get(\"layer_name\"" in cp_lines[i]:
        cp_lines[i] = "        layers = [StackLayerImage(str(layer[\"layer_name\"]), str(layer[\"filename\"]), (layer[\"base\"] / str(layer[\"filename\"])).read_bytes()) for layer in reversed(resolved)] # type: ignore\n"

with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

with open("src/actool_linux/lzfse_optimized.py", "r") as f:
    lz_lines = f.readlines()
for i in range(len(lz_lines)):
    if "def _encode_literals(self, data: bytes)" in lz_lines[i]:
        lz_lines[i] = "    def _encode_literals(self, data: bytes | bytearray) -> None:\n"
with open("src/actool_linux/lzfse_optimized.py", "w") as f:
    f.writelines(lz_lines)

with open("src/actool_linux/zero_code_db.py", "r") as f:
    zc_lines = f.readlines()
for i in range(len(zc_lines)):
    if ": Any" in zc_lines[i] and "any" not in zc_lines[i]:
        pass
    if ": any" in zc_lines[i]:
        zc_lines[i] = zc_lines[i].replace(": any", ": Any")
    if "-> any" in zc_lines[i]:
        zc_lines[i] = zc_lines[i].replace("-> any", "-> Any")
    if "def test(" in zc_lines[i]:
        pass
with open("src/actool_linux/zero_code_db.py", "w") as f:
    f.writelines(zc_lines)

with open("src/actool_linux/texture_gradient_stack.py", "r") as f:
    tx_lines = f.readlines()
for i in range(len(tx_lines)):
    if "def test(" in tx_lines[i]:
        pass
    if "any?" in tx_lines[i]:
        tx_lines[i] = tx_lines[i].replace("any?", "Any")
with open("src/actool_linux/texture_gradient_stack.py", "w") as f:
    f.writelines(tx_lines)

