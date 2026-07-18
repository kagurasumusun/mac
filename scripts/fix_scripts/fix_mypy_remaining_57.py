with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "1, 9), AtlasKeyToken(2, 181), AtlasKeyToken(8, page_dimension), AtlasKeyToken(12, scale), AtlasKeyToken(25, deployment_token))" in at_lines[i]:
        at_lines[i] = "        tokens_page: tuple[AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken] = (AtlasKeyToken(24, 0), AtlasKeyToken(1, 9), AtlasKeyToken(2, 181), AtlasKeyToken(8, page_dimension), AtlasKeyToken(12, scale), AtlasKeyToken(25, deployment_token))\n"

with open("src/actool_linux/atlas.py", "w") as f:
    f.writelines(at_lines)
