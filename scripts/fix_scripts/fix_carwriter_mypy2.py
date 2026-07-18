import re

with open("src/actool_linux/carwriter.py", "r") as f:
    lines = f.readlines()

for i in range(len(lines)):
    line = lines[i]
    if "_packed_sample(" in line and "decoded" in line:
        lines[i] = line.replace("_packed_sample(decoded", "_packed_sample(bytes(decoded)")
    if "out =" in line and "bytearray(" in line:
        pass
    if "band_dmp2(" in line and "out)" in line:
        lines[i] = line.replace("band_dmp2(out)", "band_dmp2(bytes(out))")
        lines[i] = line.replace("band_dmp2(out,", "band_dmp2(bytes(out),")
    if "_palette_plane(" in line and "out)" in line:
        lines[i] = line.replace("_palette_plane(out)", "_palette_plane(bytes(out))")
    if "v1_raw(None, len(out), out)" in line:
        lines[i] = line.replace("out)", "bytes(out))")
    if "v3_mini_color(None, len(out), out)" in line:
        lines[i] = line.replace("out)", "bytes(out))")
    if "v4_mini(None, len(out), out)" in line:
        lines[i] = line.replace("out)", "bytes(out))")
    if "_dmp2_lzfse_stream(None, len(out), out)" in line:
        lines[i] = line.replace("out)", "bytes(out))")
    if "out = lzfse.compress(out)" in line:
        lines[i] = "                out = bytearray(lzfse.compress(bytes(out)))\n"

with open("src/actool_linux/carwriter.py", "w") as f:
    f.writelines(lines)
