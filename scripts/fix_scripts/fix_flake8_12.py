import subprocess
import glob

files = glob.glob("src/actool_linux/*.py")
subprocess.run(["autopep8", "--in-place", "--max-line-length", "999999"] + files)

