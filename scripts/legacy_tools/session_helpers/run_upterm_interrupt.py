#!/usr/bin/env python3
"""Execute a command in the shared Upterm tmux pane without terminating its shell.

The client sends tmux detach (Ctrl-B d) after the command has had time to finish.
It never sends exit/logout/Ctrl-D.
"""
import base64
import os
import subprocess
import sys
import time

if len(sys.argv) < 3:
    raise SystemExit("usage: run_upterm_command.py SESSION COMMAND [wait-seconds]")
session, command = sys.argv[1], sys.argv[2]
wait = float(sys.argv[3]) if len(sys.argv) > 3 else 8.0
payload = base64.b64encode(command.encode()).decode()
marker = f"__ARENA_DONE_{int(time.time() * 1000)}__"
line = f"echo {payload} | base64 -D | bash; printf '\\n{marker}:%s\\n' $?\n"
encoded_line = base64.b64encode(line.encode()).decode()
ssh = (
    f"ssh -i /home/user/.ssh/arena_upterm_ed25519 -o IdentitiesOnly=yes "
    f"-o StrictHostKeyChecking=accept-new -o ConnectTimeout=12 -tt "
    f"{session}@uptermd.upterm.dev"
)
# `script` allocates the PTY required by Upterm. Ctrl-B d only detaches the
# client from tmux; it does not terminate the shell or server-side session.
producer = subprocess.Popen(
    ["bash", "-c", f"sleep 2; printf '\\003'; sleep 2; printf %s {encoded_line} | base64 -d; sleep {wait}; printf '\\002d'"],
    stdout=subprocess.PIPE,
)
env = os.environ.copy()
env["TERM"] = "xterm-256color"
proc = subprocess.run(
    ["script", "-qefc", ssh, "/dev/null"],
    stdin=producer.stdout,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    timeout=wait + 15,
    env=env,
)
if producer.poll() is None:
    producer.terminate()
    try:
        producer.wait(timeout=1)
    except subprocess.TimeoutExpired:
        producer.kill()
out = proc.stdout.replace(b"\x00", b"").decode("utf-8", "replace")
print(out)
if marker not in out:
    raise SystemExit(124)
