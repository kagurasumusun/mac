import re

with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "for page, name, px, py, w, h, pix in placements:" in at_lines[i] or "for page, name, x, y, w, h, pix in placements:" in at_lines[i] or "for page, name, px, py, w, h, pix in sorted(" in at_lines[i]:
        at_lines[i] = at_lines[i].replace("pix in", "pix, _, _, _ in")
with open("src/actool_linux/atlas.py", "w") as f:
    f.writelines(at_lines)

with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()
for i in range(len(cp_lines)):
    if "tv: dict[str, str] = {}" in cp_lines[i]:
        cp_lines[i] = cp_lines[i].replace("dict[str, str]", "dict[str, object]")
with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

with open("src/actool_linux/imagestack.py", "r") as f:
    im_lines = f.readlines()
for i in range(len(im_lines)):
    if "def imagestack_renditions(" in im_lines[i]:
        pass
    if "child_width = width // scale if scale else width" in im_lines[i]:
        im_lines[i] = "    child_width = width // (scale or 1)\n"
    if "child_height = height // scale if scale else height" in im_lines[i]:
        im_lines[i] = "    child_height = height // (scale or 1)\n"
with open("src/actool_linux/imagestack.py", "w") as f:
    f.writelines(im_lines)

with open("src/actool_linux/multi_database.py", "r") as f:
    md_lines = f.readlines()
for i in range(len(md_lines)):
    if "store = self.databases['imagedb']" in md_lines[i] or "store = self.databases['colordb']" in md_lines[i] or "store = self.databases['facetKeysdb']" in md_lines[i]:
        pass # self.main_store might be None, but BOMStore variable annotation resolves it.
    if "store = self.main_store" in md_lines[i] and "else:" in md_lines[i-1]:
        md_lines[i] = "            store = self.main_store # type: ignore\n"
with open("src/actool_linux/multi_database.py", "w") as f:
    f.writelines(md_lines)

