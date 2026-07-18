with open("src/actool_linux/cli.py", "r") as f:
    cl_lines = f.readlines()
for i in range(len(cl_lines)):
    if "sys.stdout.write(data.decode(\"utf-8\", errors=\"replace\") if hasattr(data, \"decode\") else data if isinstance(data, str) else str(data))" in cl_lines[i]:
        cl_lines[i] = "    sys.stdout.write(data.decode(\"utf-8\", errors=\"replace\") if isinstance(data, (bytes, bytearray)) else str(data))\n"
    if "sys.stdout.buffer.write(bytes(data) if isinstance(data, bytearray) else data if isinstance(data, bytes) else data.encode(\"utf-8\"))" in cl_lines[i]:
        cl_lines[i] = "        sys.stdout.buffer.write(data if isinstance(data, (bytes, bytearray)) else str(data).encode(\"utf-8\"))\n"
with open("src/actool_linux/cli.py", "w") as f:
    f.writelines(cl_lines)
