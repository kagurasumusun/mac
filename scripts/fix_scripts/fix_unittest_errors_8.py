with open("src/actool_linux/cli.py", "r") as f:
    cl_lines = f.readlines()
for i in range(len(cl_lines)):
    if "sys.stdout.buffer.write(data if isinstance(data, (bytes, bytearray)) else str(data).encode(\"utf-8\"))" in cl_lines[i] and "sys.stdout.buffer.write" in cl_lines[i]:
        cl_lines[i] = "            sys.stdout.buffer.write(data if isinstance(data, (bytes, bytearray)) else str(data).encode(\"utf-8\"))\n"
with open("src/actool_linux/cli.py", "w") as f:
    f.writelines(cl_lines)
