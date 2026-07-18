import re
with open("src/actool_linux/texture_gradient_stack.py", "r") as f:
    tx_lines = f.readlines()
for i in range(len(tx_lines)):
    if "undefined name 'Any'" in tx_lines[i] or "from typing import" not in "".join(tx_lines):
        pass # this is already fixed previously 

has_any = any("from typing import Any" in line for line in tx_lines)
if not has_any:
    for i in range(len(tx_lines)):
        if "from typing import" in tx_lines[i]:
            tx_lines[i] = tx_lines[i].replace("from typing import ", "from typing import Any, ")
            has_any = True
            break
if not has_any:
    tx_lines.insert(6, "from typing import Any\n")

with open("src/actool_linux/texture_gradient_stack.py", "w") as f:
    f.writelines(tx_lines)

with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "SyntaxError: unmatched ')'" in at_lines[i]:
        pass
    if "tuple((name, size, size) for name, size in source)" in at_lines[i]:
        pass
with open("src/actool_linux/atlas.py", "w") as f:
    f.writelines(at_lines)

