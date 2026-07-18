with open("src/actool_linux/legacy_coreui_features.py", "r") as f:
    lc_lines = f.readlines()
for i in range(len(lc_lines)):
    if "from typing import" in lc_lines[i]:
        lc_lines[i] = "from typing import List, Tuple, Any\n"
with open("src/actool_linux/legacy_coreui_features.py", "w") as f:
    f.writelines(lc_lines)

with open("src/actool_linux/lzfse_optimized.py", "r") as f:
    lz_lines = f.readlines()
for i in range(len(lz_lines)):
    if "from typing import" in lz_lines[i]:
        lz_lines[i] = "from typing import List\n"
with open("src/actool_linux/lzfse_optimized.py", "w") as f:
    f.writelines(lz_lines)

with open("src/actool_linux/texture_gradient_stack.py", "r") as f:
    tx_lines = f.readlines()
has_any = any("Any" in line and "typing" in line for line in tx_lines)
if not has_any:
    tx_lines.insert(0, "from typing import Any\n")
with open("src/actool_linux/texture_gradient_stack.py", "w") as f:
    f.writelines(tx_lines)

