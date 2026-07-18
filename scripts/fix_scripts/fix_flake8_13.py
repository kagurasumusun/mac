with open("src/actool_linux/cli.py", "r") as f:
    cl_lines = f.readlines()
for i in range(len(cl_lines)):
    if " # type: ignore" in cl_lines[i] and "  # type: ignore" not in cl_lines[i]:
        cl_lines[i] = cl_lines[i].replace(" # type: ignore", "  # type: ignore")
    if " # this happens" in cl_lines[i]:
        cl_lines[i] = cl_lines[i].replace(" # this happens", "  # this happens")

with open("src/actool_linux/cli.py", "w") as f:
    f.writelines(cl_lines)
