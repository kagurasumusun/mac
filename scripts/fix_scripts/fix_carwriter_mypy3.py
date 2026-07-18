import re

with open("src/actool_linux/carwriter.py", "r") as f:
    lines = f.readlines()

for i in range(len(lines)):
    line = lines[i]
    if "ga = _gray_ga_bytes(premultiplied)" in line:
        lines[i] = line.replace("premultiplied", "bytes(premultiplied)")
    elif "band_dmp2(" in line and "rows_pixels:" in line:
        # def band_dmp2(rows_pixels: bytes, band_height: int) -> bytes:
        pass
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

with open("src/actool_linux/carwriter.py", "w") as f:
    f.writelines(lines)
