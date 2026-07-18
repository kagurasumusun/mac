with open("src/actool_linux/carwriter.py", "r") as f:
    lines = f.readlines()

for i in range(len(lines)):
    line = lines[i]
    if "index = decoded[y * width + x] if interlace else _packed_sample(decoded[y * packed_stride:(y + 1) * packed_stride], x, depth)" in line:
        lines[i] = line.replace("decoded[y * packed_stride:(y + 1) * packed_stride]", "bytes(decoded[y * packed_stride:(y + 1) * packed_stride])")
    if "ga = _gray_ga_bytes(premultiplied)" in line:
        lines[i] = "    ga = _gray_ga_bytes(bytes(premultiplied))\n"
    elif "band_dmp2(" in line and "premultiplied" in line:
        lines[i] = line.replace("premultiplied", "bytes(premultiplied)")
    elif "v1_raw(width, height, premultiplied" in line:
        lines[i] = line.replace("premultiplied", "bytes(premultiplied)")
    elif "v3_mini_color(width, height, premultiplied" in line:
        lines[i] = line.replace("premultiplied[:4]", "bytes(premultiplied[:4])")
    elif "v4_mini(width, height, premultiplied" in line:
        lines[i] = line.replace("premultiplied[:4]", "bytes(premultiplied[:4])")
    elif "_palette_plane(premultiplied)" in line:
        lines[i] = line.replace("premultiplied", "bytes(premultiplied)")
    elif "_dmp2_lzfse_stream(width, height, premultiplied" in line:
        lines[i] = line.replace("premultiplied", "bytes(premultiplied)")
    if "_gray_ga_bytes(out)" in line:
        lines[i] = line.replace("_gray_ga_bytes(out)", "_gray_ga_bytes(bytes(out))")
    elif "_packed_sample(out" in line:
        lines[i] = line.replace("_packed_sample(out", "_packed_sample(bytes(out)")
    elif "band_dmp2(out" in line:
        lines[i] = line.replace("band_dmp2(out", "band_dmp2(bytes(out)")
    elif "v1_raw(None, len(out), out" in line:
        lines[i] = line.replace("v1_raw(None, len(out), out", "v1_raw(None, len(out), bytes(out)")
    elif "v3_mini_color(None, len(out), out" in line:
        lines[i] = line.replace("v3_mini_color(None, len(out), out", "v3_mini_color(None, len(out), bytes(out)")
    elif "v4_mini(None, len(out), out" in line:
        lines[i] = line.replace("v4_mini(None, len(out), out", "v4_mini(None, len(out), bytes(out)")
    elif "_palette_plane(out" in line:
        lines[i] = line.replace("_palette_plane(out", "_palette_plane(bytes(out)")
    elif "_dmp2_lzfse_stream(None, len(out), out" in line:
        lines[i] = line.replace("_dmp2_lzfse_stream(None, len(out), out", "_dmp2_lzfse_stream(None, len(out), bytes(out)")
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
    if "locale_ids.get(asset.localization, 0)" in line:
        lines[i] = line.replace("locale_ids.get(asset.localization, 0)", "locale_ids.get(str(asset.localization or \"\"), 0)")
    if "def _facet_value(attribute: int, value: object)" in line:
        lines[i] = line.replace("value: object", "value: Any")

with open("src/actool_linux/carwriter.py", "w") as f:
    f.writelines(lines)
