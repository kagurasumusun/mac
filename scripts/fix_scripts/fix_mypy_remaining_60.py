with open("src/actool_linux/texture_gradient_stack.py", "r") as f:
    tx_lines = f.readlines()
for i in range(len(tx_lines)):
    if "name_bytes = entry['inferred_kind_name'].encode('utf-8')" in tx_lines[i]:
        tx_lines[i] = "            name_bytes = str(entry['inferred_kind_name']).encode('utf-8')\n"
with open("src/actool_linux/texture_gradient_stack.py", "w") as f:
    f.writelines(tx_lines)

