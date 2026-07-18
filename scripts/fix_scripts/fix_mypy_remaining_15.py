with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()

for i in range(len(cp_lines)):
    if "def _partial_info(" in cp_lines[i]:
        cp_lines[i] = "def _partial_info(catalogs: Iterable[Catalog], options: CompileOptions) -> dict[str, Any]:\n"
    if "result: dict[str, object] = {}" in cp_lines[i]:
        cp_lines[i] = "    result: dict[str, Any] = {}\n"
    if "tv: dict[str, object] = {}" in cp_lines[i]:
        cp_lines[i] = "                tv: dict[str, Any] = {}\n"

# Only insert if not already there
has_any = any("from typing import Any" in line for line in cp_lines)
if not has_any:
    for i in range(len(cp_lines)):
        if "from typing import" in cp_lines[i]:
            cp_lines[i] = cp_lines[i].replace("from typing import ", "from typing import Any, ")
            has_any = True
            break
if not has_any:
    cp_lines.insert(6, "from typing import Any\n")

with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

