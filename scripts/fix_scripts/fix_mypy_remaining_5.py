import re

with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "for page, name, x, y, cw, ch, cpix in " in at_lines[i] or "for page, name, px, py, w, h, pix in " in at_lines[i]:
        at_lines[i] = at_lines[i].replace("cpix in", "cpix, _, _, _ in").replace("pix in", "pix, _, _, _ in")
with open("src/actool_linux/atlas.py", "w") as f:
    f.writelines(at_lines)

with open("src/actool_linux/imagestack.py", "r") as f:
    im_lines = f.readlines()
for i in range(len(im_lines)):
    if "h * scale" in im_lines[i]:
        im_lines[i] = im_lines[i].replace("h * scale", "h * (scale or 1)")
    if "w * scale" in im_lines[i]:
        im_lines[i] = im_lines[i].replace("w * scale", "w * (scale or 1)")
with open("src/actool_linux/imagestack.py", "w") as f:
    f.writelines(im_lines)

with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()
for i in range(len(cp_lines)):
    if "result: dict[str, object] = {}" in cp_lines[i]:
        pass
    if "def _partial_info(catalogs" in cp_lines[i]:
        pass # dict[str, object] should be fine
    if "StackLayerImage(str(layer[\"layer_name\"])" in cp_lines[i]:
        pass

with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

with open("src/actool_linux/lzfse_optimized.py", "r") as f:
    lz_lines = f.readlines()
for i in range(len(lz_lines)):
    if "self._encode_literals(chunk)" in lz_lines[i]:
        lz_lines[i] = lz_lines[i].replace("self._encode_literals(chunk)", "self._encode_literals(bytes(chunk))")
    if "self._encode_literals(chunk[match_len:])" in lz_lines[i]:
        lz_lines[i] = lz_lines[i].replace("self._encode_literals(chunk[match_len:])", "self._encode_literals(bytes(chunk[match_len:]))")
with open("src/actool_linux/lzfse_optimized.py", "w") as f:
    f.writelines(lz_lines)
