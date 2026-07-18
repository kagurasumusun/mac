with open("src/actool_linux/cli.py", "r") as f:
    cl_lines = f.readlines()
for i in range(len(cl_lines)):
    if "if isinstance(data, (bytes, bytearray)):" in cl_lines[i] and "sys.stdout.write(data)" in cl_lines[i+2]:
        cl_lines[i+2] = "                sys.stdout.write(data.decode(\"utf-8\", errors=\"replace\"))  # type: ignore\n"
with open("src/actool_linux/cli.py", "w") as f:
    f.writelines(cl_lines)
