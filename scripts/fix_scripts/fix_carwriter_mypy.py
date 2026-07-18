import re

with open("src/actool_linux/carwriter.py", "r") as f:
    lines = f.readlines()

for i in range(len(lines)):
    line = lines[i]
    if "_packed_sample(" in line and "bytearray" in line:
        pass  # We can just change bytearray to bytes inside the calls
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

with open("src/actool_linux/carwriter.py", "w") as f:
    f.writelines(lines)
