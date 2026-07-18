import re

# zero_code_db.py
with open("src/actool_linux/zero_code_db.py", "r") as f:
    zc_lines = f.readlines()
for i in range(len(zc_lines)):
    zc_lines[i] = zc_lines[i].replace(": any", ": Any").replace("-> any", "-> Any")
with open("src/actool_linux/zero_code_db.py", "w") as f:
    f.writelines(zc_lines)
    
# texture_gradient_stack.py
with open("src/actool_linux/texture_gradient_stack.py", "r") as f:
    tx_lines = f.readlines()
for i in range(len(tx_lines)):
    if "value.encode" in tx_lines[i]:
        tx_lines[i] = tx_lines[i].replace("value.encode", "str(value).encode")
with open("src/actool_linux/texture_gradient_stack.py", "w") as f:
    f.writelines(tx_lines)

# lzfse_optimized.py
with open("src/actool_linux/lzfse_optimized.py", "r") as f:
    lz_lines = f.readlines()
for i in range(len(lz_lines)):
    if "hash_table =" in lz_lines[i] and "{}" in lz_lines[i]:
        lz_lines[i] = lz_lines[i].replace("hash_table =", "hash_table: dict[int, int] =")
    if "_encode_literals" in lz_lines[i] and "bytearray" in lz_lines[i]:
        pass
with open("src/actool_linux/lzfse_optimized.py", "w") as f:
    f.writelines(lz_lines)

# thinning.py
with open("src/actool_linux/thinning.py", "r") as f:
    th_lines = f.readlines()
for i in range(len(th_lines)):
    if "allowed.add(None)" in th_lines[i]:
        th_lines[i] = "            if options.keep_fallbacks: allowed_locales.add(None) # type: ignore\n"
with open("src/actool_linux/thinning.py", "w") as f:
    f.writelines(th_lines)

# imagestack.py
with open("src/actool_linux/imagestack.py", "r") as f:
    im_lines = f.readlines()
for i in range(len(im_lines)):
    if "h * scale" in im_lines[i]:
        im_lines[i] = im_lines[i].replace("h * scale", "h * (scale or 1)")
    if "w * scale" in im_lines[i]:
        im_lines[i] = im_lines[i].replace("w * scale", "w * (scale or 1)")
with open("src/actool_linux/imagestack.py", "w") as f:
    f.writelines(im_lines)

