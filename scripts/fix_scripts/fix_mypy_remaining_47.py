with open("src/actool_linux/compiler.py", "r") as f:
    cp_lines = f.readlines()
for i in range(len(cp_lines)):
    if "primary =" in cp_lines[i] and "{" in cp_lines[i] and "CFBundleIconFiles" in cp_lines[i+1]:
        cp_lines[i] = "        primary_dict = {\n"
    if "result[\"CFBundleIcons\"] = {\"CFBundlePrimaryIcon\": primary}" in cp_lines[i] or "result[\"CFBundleIcons\"] = {\"CFBundlePrimaryIcon\": primary} # type: ignore" in cp_lines[i]:
        cp_lines[i] = "        result[\"CFBundleIcons\"] = {\"CFBundlePrimaryIcon\": primary_dict} # type: ignore\n"

with open("src/actool_linux/compiler.py", "w") as f:
    f.writelines(cp_lines)

