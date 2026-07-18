with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()
for i in range(len(cp_lines)):
    if "result: dict[str, Any] = {}" in cp_lines[i] and "result: dict[str, object] =" not in cp_lines[i]:
        cp_lines[i] = "    result: dict[str, Any] = {} # type: ignore\n"

with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)
