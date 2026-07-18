with open("src/actool_linux/carwriter.py", "r") as f:
    cw_lines = f.readlines()
for i in range(len(cw_lines)):
    if "import cairosvg" in cw_lines[i]:
        cw_lines[i] = "        import cairosvg # type: ignore\n"
with open("src/actool_linux/carwriter.py", "w") as f:
    f.writelines(cw_lines)
