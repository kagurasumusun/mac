with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()
for i in range(len(cp_lines)):
    if "primary = shelf = shelf_wide = None" in cp_lines[i] or "primary: Any = None; shelf: Any = None; shelf_wide: Any = None" in cp_lines[i]:
        cp_lines[i] = "                primary: Any = None; shelf: Any = None; shelf_wide: Any = None\n"
with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

