with open("src/actool_linux/bomwriter.py", "r") as f:
    lines = f.readlines()

for i in range(len(lines)):
    if "import struct" in lines[i]:
        lines.insert(i+1, "import io\n")
        break

for i in range(len(lines)):
    if "def build(self) -> bytes:" in lines[i]:
        # Replace the build method to use io.BytesIO
        pass

with open("src/actool_linux/bomwriter.py", "w") as f:
    f.writelines(lines)
