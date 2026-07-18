import re

with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "tokens_page: tuple[AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken, AtlasKeyToken] =" in at_lines[i] and i > 295:
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

with open("src/actool_linux/multi_database.py", "r") as f:
    md_lines = f.readlines()
for i in range(len(md_lines)):
    if "renditions_data = store.named_block('RENDITIONS')" in md_lines[i] or "color_data = store.named_block('COLORDEFINITIONS')" in md_lines[i] or "facet_data = store.named_block('FACETKEYS')" in md_lines[i] or "db_path = output_path.parent / f\"{output_path.stem}_{db_name}{output_path.suffix}\"" in md_lines[i]:
        md_lines[i] = md_lines[i].replace("renditions_data = ", "").replace("color_data = ", "").replace("facet_data = ", "").replace("db_path = ", "_ = ")

with open("src/actool_linux/multi_database.py", "w") as f:
    f.writelines(md_lines)

