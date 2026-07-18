with open("src/actool_linux/cli.py", "r") as f:
    cl_lines = f.readlines()
for i in range(len(cl_lines)):
    if "sys.stdout.write(data)" in cl_lines[i] and "type: ignore" not in cl_lines[i] and i > 25:
        cl_lines[i] = cl_lines[i].replace("sys.stdout.write(data)", "sys.stdout.write(data)  # type: ignore")
    if "sys.stdout.write(str(data))" in cl_lines[i] and "type: ignore" not in cl_lines[i]:
        cl_lines[i] = cl_lines[i].replace("sys.stdout.write(str(data))", "sys.stdout.write(str(data))  # type: ignore")
with open("src/actool_linux/cli.py", "w") as f:
    f.writelines(cl_lines)
