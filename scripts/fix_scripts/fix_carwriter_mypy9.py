with open("src/actool_linux/carwriter.py", "r") as f:
    lines = f.readlines()

for i in range(len(lines)):
    line = lines[i]
    if "key=lambda item: (item.name.encode(\"utf-8\")" in line:
        lines[i] = line.replace("item.name.encode(\"utf-8\")", "str(item.name).encode(\"utf-8\")")
    if "key=lambda item: str(item).encode" in line:
        lines[i] = line.replace("str(item).encode(\"utf-8\")", "str(item)")
    if "name.encode(\"utf-8\") for name in facet_names" in line:
        lines[i] = line.replace("name.encode", "str(name).encode")
    if "locale.encode(\"utf-8\")" in line and "for locale in locale_names" not in line:
        lines[i] = line.replace("locale.encode", "str(locale).encode")
    if "appearance_name.encode(\"utf-8\")" in line:
        lines[i] = line.replace("appearance_name.encode", "str(appearance_name).encode")
    if "raw_name: object" in line:
        lines[i] = line.replace("raw_name: object", "raw_name: bytes")

with open("src/actool_linux/carwriter.py", "w") as f:
    f.writelines(lines)
