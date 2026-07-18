import subprocess
import glob

subprocess.run(["flake8", "--max-line-length=150", "src/actool_linux/"])
