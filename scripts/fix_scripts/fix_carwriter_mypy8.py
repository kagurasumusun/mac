with open("src/actool_linux/carwriter.py", "r") as f:
    lines = f.readlines()

for i in range(len(lines)):
    line = lines[i]
    if "key=lambda x: x.encode" in line:
        lines[i] = line.replace("x.encode(\"utf-8\")", "str(x)")
    elif "locale.encode" in line and "for locale in locale_names" not in line:
        lines[i] = line.replace("locale.encode", "str(locale).encode")
    elif "locale_ids.get" in line:
        lines[i] = line.replace("locale_ids.get(asset.localization, 0)", "locale_ids.get(str(asset.localization or \"\"), 0)")
    elif "appearance_name.encode" in line:
        lines[i] = line.replace("appearance_name.encode", "str(appearance_name).encode")
    elif "def _facet_value(attribute: int, value: object) -> bytes:" in line:
        lines[i] = line.replace("value: object", "value: Any")

with open("src/actool_linux/carwriter.py", "w") as f:
    f.writelines(lines)
