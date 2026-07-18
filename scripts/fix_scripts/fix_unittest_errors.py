with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "for page_dimension,name,px,py,w,h,_,_,_,_ in placements:" in at_lines[i]:
        at_lines.insert(i+1, "        link=AtlasLink(px,py,w,h,tokens_page)\n")
        break
with open("src/actool_linux/atlas.py", "w") as f:
    f.writelines(at_lines)

with open("src/actool_linux/cli.py", "r") as f:
    cl_lines = f.readlines()
for i in range(len(cl_lines)):
    if "sys.stdout.buffer.write(data)" in cl_lines[i] and "sys.stdout.write(data" not in cl_lines[i]:
        cl_lines[i] = "        sys.stdout.write(data if isinstance(data, str) else data.decode(\"utf-8\"))\n"

with open("src/actool_linux/cli.py", "w") as f:
    f.writelines(cl_lines)

