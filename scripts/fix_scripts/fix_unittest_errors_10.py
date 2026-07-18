with open("src/actool_linux/cli.py", "r") as f:
    cl_lines = f.readlines()
for i in range(len(cl_lines)):
    if "sys.stdout.write(data.decode(\"utf-8\", errors=\"replace\") if isinstance(data, (bytes, bytearray)) else data if isinstance(data, str) else str(data))" in cl_lines[i]:
        cl_lines[i] = "    if isinstance(data, (bytes, bytearray)):\n        sys.stdout.buffer.write(data)\n    else:\n        sys.stdout.write(data if isinstance(data, str) else str(data))\n"
    if "sys.stdout.write(data if isinstance(data, str) else data.decode(\"utf-8\", errors=\"replace\"))" in cl_lines[i] and i < 24:
        cl_lines[i] = ""
    if "return" in cl_lines[i] and "except TypeError:" in cl_lines[i+1]:
        cl_lines[i] = ""
        cl_lines[i+1] = ""
        cl_lines[i+2] = ""
with open("src/actool_linux/cli.py", "w") as f:
    f.writelines(cl_lines)
