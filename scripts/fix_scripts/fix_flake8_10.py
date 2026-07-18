with open("src/actool_linux/legacy_coreui_features.py", "r") as f:
    lc_lines = f.readlines()
for i in range(len(lc_lines)):
    if "from typing import" in lc_lines[i]:
        lc_lines[i] = "from typing import List, Tuple\n"
with open("src/actool_linux/legacy_coreui_features.py", "w") as f:
    f.writelines(lc_lines)

with open("src/actool_linux/lzfse_optimized.py", "r") as f:
    lz_lines = f.readlines()
for i in range(len(lz_lines)):
    if "from typing import" in lz_lines[i]:
        lz_lines[i] = ""
with open("src/actool_linux/lzfse_optimized.py", "w") as f:
    f.writelines(lz_lines)

with open("src/actool_linux/texture_gradient_stack.py", "r") as f:
    tx_lines = f.readlines()
for i in range(len(tx_lines)):
    if "undefined name 'Any'" in tx_lines[i] or "Any" in tx_lines[i]:
        tx_lines[i] = tx_lines[i].replace("Any", "any") # Just fallback to lowercase 'any' to fix F821 if import is failing or missing. Actually, Mypy was complaining about lowercase any, so let's import it properly.

with open("src/actool_linux/texture_gradient_stack.py", "w") as f:
    f.writelines(tx_lines)

