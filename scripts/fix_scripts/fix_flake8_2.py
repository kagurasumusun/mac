import re

with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "tokens_page: tuple" in at_lines[i]:
        at_lines[i] = ""

with open("src/actool_linux/atlas.py", "w") as f:
    f.writelines(at_lines)

with open("src/actool_linux/atlas_geometry.py", "r") as f:
    ag_lines = f.readlines()
for i in range(len(ag_lines)):
    if "best_skyline_idx =" in ag_lines[i]:
        ag_lines[i] = ""

with open("src/actool_linux/atlas_geometry.py", "w") as f:
    f.writelines(ag_lines)

with open("src/actool_linux/bom.py", "r") as f:
    bom_lines = f.readlines()
for i in range(len(bom_lines)):
    if "typing.BinaryIO" in bom_lines[i] or "from typing import BinaryIO" in bom_lines[i]:
        bom_lines[i] = bom_lines[i].replace("BinaryIO, ", "").replace("BinaryIO", "")
        if "from typing import \n" in bom_lines[i] or "from typing import\n" in bom_lines[i]:
            bom_lines[i] = ""

with open("src/actool_linux/bom.py", "w") as f:
    f.writelines(bom_lines)

with open("src/actool_linux/cbck_complete.py", "r") as f:
    cb_lines = f.readlines()
for i in range(len(cb_lines)):
    if "from typing import Optional" in cb_lines[i]:
        cb_lines[i] = cb_lines[i].replace("Optional, ", "").replace("Optional", "")
        if "from typing import \n" in cb_lines[i]:
            cb_lines[i] = ""
    if "from pathlib import Path" in cb_lines[i]:
        cb_lines[i] = ""

with open("src/actool_linux/cbck_complete.py", "w") as f:
    f.writelines(cb_lines)

with open("src/actool_linux/legacy_coreui_features.py", "r") as f:
    lc_lines = f.readlines()
for i in range(len(lc_lines)):
    if "from typing import Dict, Optional" in lc_lines[i]:
        lc_lines[i] = ""
    if "from pathlib import Path" in lc_lines[i]:
        lc_lines[i] = ""
    if "import struct" in lc_lines[i]:
        lc_lines[i] = ""

with open("src/actool_linux/legacy_coreui_features.py", "w") as f:
    f.writelines(lc_lines)

with open("src/actool_linux/lzfse_optimized.py", "r") as f:
    lz_lines = f.readlines()
for i in range(len(lz_lines)):
    if "from typing import List, Tuple, Optional" in lz_lines[i]:
        lz_lines[i] = "from typing import List\n"

with open("src/actool_linux/lzfse_optimized.py", "w") as f:
    f.writelines(lz_lines)

with open("src/actool_linux/multi_database.py", "r") as f:
    md_lines = f.readlines()
for i in range(len(md_lines)):
    if "import struct" in md_lines[i]:
        md_lines[i] = ""
    if "renditions_data = store.named_block('RENDITIONS')" in md_lines[i]:
        md_lines[i] = "                store.named_block('RENDITIONS')\n"
    if "color_data = store.named_block('COLORDEFINITIONS')" in md_lines[i]:
        md_lines[i] = "                store.named_block('COLORDEFINITIONS')\n"
    if "facet_data = store.named_block('FACETKEYS')" in md_lines[i]:
        md_lines[i] = "                store.named_block('FACETKEYS')\n"
    if "db_path = output_path.parent" in md_lines[i]:
        md_lines[i] = ""

with open("src/actool_linux/multi_database.py", "w") as f:
    f.writelines(md_lines)

with open("src/actool_linux/texture_gradient_stack.py", "r") as f:
    tx_lines = f.readlines()
for i in range(len(tx_lines)):
    if "from pathlib import Path" in tx_lines[i]:
        tx_lines[i] = ""
    if "undefined name 'Any'" in tx_lines[i] or "Any" in tx_lines[i]:
        pass # fixed earlier, let's make sure typing is imported
has_any = any("from typing import Any" in line for line in tx_lines)
if not has_any:
    tx_lines.insert(6, "from typing import Any\n")

with open("src/actool_linux/texture_gradient_stack.py", "w") as f:
    f.writelines(tx_lines)

with open("src/actool_linux/zero_code_db.py", "r") as f:
    zc_lines = f.readlines()
for i in range(len(zc_lines)):
    if "from pathlib import Path" in zc_lines[i]:
        zc_lines[i] = ""

with open("src/actool_linux/zero_code_db.py", "w") as f:
    f.writelines(zc_lines)

with open("src/actool_linux/carwriter.py", "r") as f:
    cw_lines = f.readlines()
for i in range(len(cw_lines)):
    if "import hashlib" in cw_lines[i]:
        cw_lines[i] = ""

with open("src/actool_linux/carwriter.py", "w") as f:
    f.writelines(cw_lines)

