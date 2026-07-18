with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "for page_dimension,name,px,py,w,h,_,_,_,_ in placements:" in at_lines[i]:
        at_lines.insert(i-1, "    tokens_page = (AtlasKeyToken(24,0),AtlasKeyToken(1,9),AtlasKeyToken(2,181),AtlasKeyToken(8,page_dimension),AtlasKeyToken(12,scale),AtlasKeyToken(25,deployment_token))\n")
        break

with open("src/actool_linux/atlas.py", "w") as f:
    f.writelines(at_lines)

with open("src/actool_linux/cli.py", "r") as f:
    cl_lines = f.readlines()
for i in range(len(cl_lines)):
    if "sys.stdout.write(data if isinstance(data, str) else data.decode(\"utf-8\"))" in cl_lines[i]:
        cl_lines[i] = "        sys.stdout.write(data if isinstance(data, str) else data.decode(\"utf-8\", errors=\"replace\"))\n"
    if "sys.stdout.write(data.decode(\"utf-8\", errors=\"replace\") if isinstance(data, bytes) else str(data))" in cl_lines[i]:
        cl_lines[i] = "    sys.stdout.write(data.decode(\"utf-8\", errors=\"replace\") if isinstance(data, bytes) else data if isinstance(data, str) else str(data))\n"
with open("src/actool_linux/cli.py", "w") as f:
    f.writelines(cl_lines)

