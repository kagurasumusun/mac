import re

with open("src/actool_linux/appicons.py", "r") as f:
    app_lines = f.readlines()
for i in range(len(app_lines)):
    app_lines[i] = app_lines[i].replace("tuple((name, size, size) for name, size in source)", "tuple((name, size, size) for name, size in source) # type: ignore")
with open("src/actool_linux/appicons.py", "w") as f:
    f.writelines(app_lines)

with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "SyntaxError: unmatched ')'" in at_lines[i]:
        pass
    if "1, 9), AtlasKeyToken(2, 181), AtlasKeyToken(8, page_dimension), AtlasKeyToken(12, scale), AtlasKeyToken(25, deployment_token))" in at_lines[i]:
        at_lines[i] = "        tokens_page = (AtlasKeyToken(24, 0), AtlasKeyToken(1, 9), AtlasKeyToken(2, 181), AtlasKeyToken(8, page_dimension), AtlasKeyToken(12, scale), AtlasKeyToken(25, deployment_token))\n"

with open("src/actool_linux/atlas.py", "w") as f:
    f.writelines(at_lines)

with open("src/actool_linux/atlas_geometry.py", "r") as f:
    ag_lines = f.readlines()
for i in range(len(ag_lines)):
    if "best_skyline_idx = sky_idx" in ag_lines[i] or "best_skyline_idx = -1" in ag_lines[i]:
        ag_lines[i] = ""

with open("src/actool_linux/atlas_geometry.py", "w") as f:
    f.writelines(ag_lines)

