import re

with open("src/actool_linux/carwriter.py", "r") as f:
    lines = f.readlines()

for i in range(len(lines)):
    line = lines[i]
    if "premultiplied = bytes(premultiplied)" in line:
        lines[i] = "    premultiplied_bytes = bytes(premultiplied)\n"
    elif "bytes(premultiplied)" in line:
        lines[i] = line.replace("bytes(premultiplied)", "premultiplied_bytes")
    elif "bytes(premultiplied[:4])" in line:
        lines[i] = line.replace("bytes(premultiplied[:4])", "premultiplied_bytes[:4]")

with open("src/actool_linux/carwriter.py", "w") as f:
    f.writelines(lines)
