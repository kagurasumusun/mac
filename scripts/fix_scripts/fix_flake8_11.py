with open("src/actool_linux/atlas.py", "r") as f:
    at_lines = f.readlines()
for i in range(len(at_lines)):
    if "link=AtlasLink(px,py,w,h,tokens_page)" in at_lines[i]:
        at_lines[i] = "        link = AtlasLink(px, py, w, h, tokens_page)\n"
with open("src/actool_linux/atlas.py", "w") as f:
    f.writelines(at_lines)

with open("src/actool_linux/cli.py", "r") as f:
    cl_lines = f.readlines()
for i in range(len(cl_lines)):
    cl_lines[i] = cl_lines[i].replace("(\"iphone\",\"ipad\",\"tv\",\"watch\",\"mac\",\"vision\")", "(\"iphone\", \"ipad\", \"tv\", \"watch\", \"mac\", \"vision\")")
    cl_lines[i] = cl_lines[i].replace("(\"yes\",\"no\")", "(\"yes\", \"no\")")
    cl_lines[i] = cl_lines[i].replace("(\"human-readable-text\",\"xml1\")", "(\"human-readable-text\", \"xml1\")")
    cl_lines[i] = cl_lines[i].replace("(\"16.0\",\"16.1\",\"16.2\",\"16.3\",\"16.4\",\"26.0.1\",\"26.1.1\",\"26.2\",\"26.3\",\"26.4.1\",\"26.5\",\"26.6\")", "(\"16.0\", \"16.1\", \"16.2\", \"16.3\", \"16.4\", \"26.0.1\", \"26.1.1\", \"26.2\", \"26.3\", \"26.4.1\", \"26.5\", \"26.6\")")
    if "import datetime, os, threading" in cl_lines[i]:
        cl_lines[i] = "        import datetime\n        import os\n        import threading\n"
    if "if out_text: print(out_text)" in cl_lines[i]:
        cl_lines[i] = "        if out_text:\n            print(out_text)\n"
    if "for output in result.outputs: print(output)" in cl_lines[i]:
        cl_lines[i] = "            for output in result.outputs:\n                print(output)\n"
with open("src/actool_linux/cli.py", "w") as f:
    f.writelines(cl_lines)

