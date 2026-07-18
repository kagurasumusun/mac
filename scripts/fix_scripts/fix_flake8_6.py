import re

with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "SyntaxError: unmatched ')'" in at_lines[i]:
        pass
    if "tuple((name, size, size) for name, size in source)" in at_lines[i]:
        pass
    if "tokens_page: tuple[AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken] =" in at_lines[i] and "AtlasKeyToken(24, 0)" in at_lines[i]:
        pass # this line was manually fixed to not have the type annotation

with open("src/actool_linux/atlas.py", "w") as f:
    f.writelines(at_lines)

