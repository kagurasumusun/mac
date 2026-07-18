with open("src/actool_linux/lzfse_optimized.py", "r") as f:
    lz_lines = f.readlines()
for i in range(len(lz_lines)):
    if "self._encode_bytes(literals)(bytes(literals))" in lz_lines[i]:
        lz_lines[i] = lz_lines[i].replace("self._encode_bytes(literals)(bytes(literals))", "self._encode_literals(bytes(literals))")

with open("src/actool_linux/lzfse_optimized.py", "w") as f:
    f.writelines(lz_lines)

