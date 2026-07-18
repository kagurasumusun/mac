with open("src/actool_linux/cli.py", "r") as f:
    cl_lines = f.readlines()
for i in range(len(cl_lines)):
    if "sys.stdout.write(data.decode(\"utf-8\", errors=\"replace\") if isinstance(data, (bytes, bytearray)) else str(data))" in cl_lines[i]:
        cl_lines[i] = "    sys.stdout.write(data.decode(\"utf-8\", errors=\"replace\") if isinstance(data, (bytes, bytearray)) else data if isinstance(data, str) else str(data))\n"

with open("src/actool_linux/cli.py", "w") as f:
    f.writelines(cl_lines)

