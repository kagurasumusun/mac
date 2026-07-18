with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "tokens_2" in at_lines[i] and i > 295:
        at_lines[i] = "        tokens_page: tuple[AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken] = (AtlasKeyToken(24,0),AtlasKeyToken(1,9),AtlasKeyToken(2,181),AtlasKeyToken(8,page_dimension),AtlasKeyToken(12,scale),AtlasKeyToken(25,deployment_token))\n"
    if "link=AtlasLink(px,py,w,h,tokens" in at_lines[i] and i > 295:
        at_lines[i] = "        link=AtlasLink(px,py,w,h,tokens_page)\n"

with open("src/actool_linux/atlas.py", "w") as f:
    f.writelines(at_lines)

with open("src/actool_linux/lzfse_optimized.py", "r") as f:
    lz_lines = f.readlines()
for i in range(len(lz_lines)):
    if "self._encode_literals(" in lz_lines[i] and "bytearray" in lz_lines[i]:
        pass
    if "def _encode_literals(self, data: bytes)" in lz_lines[i]:
        lz_lines[i] = "    def _encode_literals(self, data: bytes | bytearray) -> None:\n"
with open("src/actool_linux/lzfse_optimized.py", "w") as f:
    f.writelines(lz_lines)
