with open("src/actool_linux/lzfse_optimized.py", "r") as f:
    lines = f.readlines()

for i in range(len(lines)):
    if "def _find_match_length(self, data: bytes, pos1: int, pos2: int) -> int:" in lines[i]:
        lines[i] = "    def _find_match_length(self, data: memoryview, pos1: int, pos2: int) -> int:\n"
    elif "match_len = self._find_match_length(data, match_pos, i)" in lines[i]:
        lines[i] = "                    match_len = self._find_match_length(memoryview(data), match_pos, i)\n"
    elif "def _encode_literals(self, data: bytes | bytearray) -> bytes:" in lines[i]:
        lines[i] = "    def _encode_literals(self, data: bytes | bytearray | memoryview) -> bytes:\n"

with open("src/actool_linux/lzfse_optimized.py", "w") as f:
    f.writelines(lines)
