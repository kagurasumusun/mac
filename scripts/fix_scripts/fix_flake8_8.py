with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "tokens_page = (AtlasKeyToken(24, 0)" in at_lines[i]:
        at_lines[i] = ""
with open("src/actool_linux/atlas.py", "w") as f:
    f.writelines(at_lines)

with open("src/actool_linux/cbck_complete.py", "r") as f:
    cb_lines = f.readlines()
for i in range(len(cb_lines)):
    if "from typing import List, Tuple, Optional" in cb_lines[i]:
        cb_lines[i] = "from typing import List, Tuple\n"
with open("src/actool_linux/cbck_complete.py", "w") as f:
    f.writelines(cb_lines)

with open("src/actool_linux/legacy_coreui_features.py", "r") as f:
    lc_lines = f.readlines()
for i in range(len(lc_lines)):
    if "from typing import Dict, List, Optional, Tuple, Any" in lc_lines[i]:
        lc_lines[i] = "from typing import List, Tuple, Any\n"
with open("src/actool_linux/legacy_coreui_features.py", "w") as f:
    f.writelines(lc_lines)

with open("src/actool_linux/lzfse_optimized.py", "r") as f:
    lz_lines = f.readlines()
for i in range(len(lz_lines)):
    if "from typing import List, Tuple, Optional" in lz_lines[i] or "from typing import List, Optional, Tuple" in lz_lines[i]:
        lz_lines[i] = "from typing import List\n"
with open("src/actool_linux/lzfse_optimized.py", "w") as f:
    f.writelines(lz_lines)

with open("src/actool_linux/texture_gradient_stack.py", "r") as f:
    tx_lines = f.readlines()
for i in range(len(tx_lines)):
    if "undefined name 'Any'" in tx_lines[i] or "Any" in tx_lines[i]:
        pass

has_any = any("from typing import Any" in line or "from typing import" in line and "Any" in line for line in tx_lines)
if not has_any:
    for i in range(len(tx_lines)):
        if "from typing import " in tx_lines[i]:
            tx_lines[i] = tx_lines[i].replace("from typing import ", "from typing import Any, ")
            has_any = True
            break
if not has_any:
    tx_lines.insert(6, "from typing import Any\n")

with open("src/actool_linux/texture_gradient_stack.py", "w") as f:
    f.writelines(tx_lines)
