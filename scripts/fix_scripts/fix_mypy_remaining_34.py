with open("src/actool_linux/lzfse_optimized.py", "r") as f:
    lz_lines = f.readlines()
for i in range(len(lz_lines)):
    if "def _encode_literals(self, data: bytes | bytearray) -> None:\n" in lz_lines[i] and "data = bytes(data)" in lz_lines[i+1]:
        lz_lines[i] = "    def _encode_literals(self, data: bytes) -> None:\n"
        lz_lines[i+1] = ""
    elif "self._encode_literals(chunk)" in lz_lines[i]:
        lz_lines[i] = lz_lines[i].replace("chunk", "bytes(chunk)")
    elif "self._encode_literals(chunk[match_len:])" in lz_lines[i]:
        lz_lines[i] = lz_lines[i].replace("chunk[match_len:]", "bytes(chunk[match_len:])")
with open("src/actool_linux/lzfse_optimized.py", "w") as f:
    f.writelines(lz_lines)

with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()
for i in range(len(cp_lines)):
    if "primary: Any =" in cp_lines[i]:
        cp_lines[i] = "                primary: Any = None; shelf: Any = None; shelf_wide: Any = None\n"
    if "shelf: Any =" in cp_lines[i]:
        cp_lines[i] = ""
    if "shelf_wide: Any =" in cp_lines[i]:
        cp_lines[i] = ""
with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

