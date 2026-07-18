with open("src/actool_linux/texture_gradient_stack.py", "r") as f:
    tx_lines = f.readlines()
for i in range(len(tx_lines)):
    if "value.encode" in tx_lines[i] and "str(value)" not in tx_lines[i]:
        tx_lines[i] = tx_lines[i].replace("value.encode", "str(value).encode")
with open("src/actool_linux/texture_gradient_stack.py", "w") as f:
    f.writelines(tx_lines)

