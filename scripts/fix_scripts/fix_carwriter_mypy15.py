with open("src/actool_linux/carwriter.py", "r") as f:
    lines = f.readlines()

for i in range(len(lines)):
    line = lines[i]
    if "value_id = writer.add_block(_facet_value(ident, int(part)))" in line:
        lines[i] = line.replace("int(part)", "part")
    if "key_id = writer.add_block(raw_name); value_id = writer.add_block(_facet_value(ident, part))" in line:
        lines[i] = "        key_id = writer.add_block(raw_name); value_id = writer.add_block(_facet_value(int(ident), int(str(part))))\n"
    if "facet_blocks.append((writer.add_block(_facet_value(*facet_by_name[name]))," in line:
        lines[i] = line.replace("_facet_value(*facet_by_name[name])", "_facet_value(int(facet_by_name[name][0]), int(str(facet_by_name[name][1])))")

with open("src/actool_linux/carwriter.py", "w") as f:
    f.writelines(lines)
