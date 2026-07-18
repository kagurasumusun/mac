with open("src/actool_linux/lzfse_optimized.py", "r") as f:
    lz_lines = f.readlines()
for i in range(len(lz_lines)):
    if "self._encode_literals(literals)" in lz_lines[i] and "bytes" not in lz_lines[i]:
        lz_lines[i] = lz_lines[i].replace("literals", "bytes(literals)")
    if "def _encode_literals(self, data: bytes)" in lz_lines[i]:
        lz_lines[i] = "    def _encode_literals(self, data: bytes | bytearray) -> bytes:\n        data = bytes(data)\n"
    elif "def _encode_literals(self, data: bytes | bytearray) -> None:" in lz_lines[i] or "def _encode_literals(self, data: bytes | bytearray) -> bytes:" in lz_lines[i]:
        lz_lines[i] = "    def _encode_literals(self, data: bytes | bytearray) -> bytes:\n        data = bytes(data)\n"
with open("src/actool_linux/lzfse_optimized.py", "w") as f:
    f.writelines(lz_lines)

