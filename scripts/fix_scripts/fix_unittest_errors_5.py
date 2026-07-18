with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "link=AtlasLink(px,py,w,h,tokens_page)" in at_lines[i] and i > 295:
        at_lines.insert(i, "        tokens_page = (AtlasKeyToken(24, 0), AtlasKeyToken(1, 9), AtlasKeyToken(2, 181), AtlasKeyToken(8, page_dimension), AtlasKeyToken(12, scale), AtlasKeyToken(25, deployment_token))\n")
        break

with open("src/actool_linux/atlas.py", "w") as f:
    f.writelines(at_lines)

with open("src/actool_linux/cli.py", "r") as f:
    cl_lines = f.readlines()
for i in range(len(cl_lines)):
    if "sys.stdout.write(data.decode(\"utf-8\", errors=\"replace\") if isinstance(data, bytes) else data if isinstance(data, str) else str(data))" in cl_lines[i]:
        cl_lines[i] = "    sys.stdout.write(data.decode(\"utf-8\", errors=\"replace\") if isinstance(data, (bytes, bytearray)) else data if isinstance(data, str) else str(data))\n"

with open("src/actool_linux/cli.py", "w") as f:
    f.writelines(cl_lines)

