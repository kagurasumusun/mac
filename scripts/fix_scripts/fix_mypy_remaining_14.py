with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "for page, name, x, top, cw, ch, cpix in placements:" in at_lines[i] or "for page, name, px, py, w, h, pix in placements:" in at_lines[i] or "for page, name, px, py, w, h, pix in sorted(" in at_lines[i]:
        at_lines[i] = at_lines[i].replace("cpix in", "cpix, _, _, _ in").replace("pix in", "pix, _, _, _ in")
    if "aw=max(px+w for _,_,px,_,w,_,_ in page_items); ah=max(py+h for _,_,_,py,_,h,_ in page_items)" in at_lines[i]:
        at_lines[i] = "        aw=max(px+w for _,_,px,_,w,_,_,_,_,_ in page_items); ah=max(py+h for _,_,_,py,_,h,_,_,_,_ in page_items)\n"
    if "for _,_,px,py,w,h,pix in page_items:" in at_lines[i]:
        at_lines[i] = "        for _,_,px,py,w,h,pix,_,_,_ in page_items:\n"
    if "for page_dimension,name,px,py,w,h,_ in placements:" in at_lines[i]:
        at_lines[i] = "    for page_dimension,name,px,py,w,h,_,_,_,_ in placements:\n"
with open("src/actool_linux/atlas.py", "w") as f:
    f.writelines(at_lines)

with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()
for i in range(len(cp_lines)):
    if "def _partial_info(" in cp_lines[i]:
        cp_lines[i] = "def _partial_info(catalogs: Iterable[Catalog], options: CompileOptions) -> dict[str, Any]:\n"
    if "result: dict[str, object] = {}" in cp_lines[i]:
        cp_lines[i] = "    result: dict[str, Any] = {}\n"
    if "tv: dict[str, object] = {}" in cp_lines[i]:
        cp_lines[i] = "                tv: dict[str, Any] = {}\n"
cp_lines.insert(6, "from typing import Any\n")
with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

