#!/usr/bin/env python3
import sys, time, re, base64, paramiko, os

def run_command(session, command, wait=15.0):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    key_path = os.path.expanduser('/home/user/.ssh/id_ed25519')
    if not os.path.exists(key_path):
        key_path = os.path.expanduser('/home/user/.ssh/arena_upterm_ed25519')
    key = paramiko.Ed25519Key.from_private_key_file(key_path)
    client.connect('uptermd.upterm.dev', port=22, username=session, pkey=key, timeout=15)
    
    chan = client.invoke_shell(term='xterm', width=200, height=50)
    time.sleep(1.5)
    while chan.recv_ready():
        chan.recv(65536)
        
    token = f"TK{int(time.time()*1000)}"
    payload = base64.b64encode(command.encode()).decode()
    
    cmd_str = (
        f"echo {payload} | base64 -D > /tmp/remote_cmd_{token}.sh && bash /tmp/remote_cmd_{token}.sh > /tmp/remote_out_{token}.txt 2>&1; "
        f"rc=$?; printf '\\n===BASE' && printf '64_START_{token}===\\n'; base64 -i /tmp/remote_out_{token}.txt; "
        f"printf '===BASE' && printf \"64_END_RC_{token}:${{rc}}===\\n\"; rm -f /tmp/remote_cmd_{token}.sh /tmp/remote_out_{token}.txt\n"
    )
    chan.send(cmd_str)
    
    start_time = time.time()
    raw_output = ""
    while time.time() - start_time < wait:
        if chan.recv_ready():
            chunk = chan.recv(65536).decode('utf-8', errors='ignore')
            raw_output += chunk
            if f"===BASE64_END_RC_{token}:" in raw_output:
                time.sleep(0.3)
                while chan.recv_ready():
                    raw_output += chan.recv(65536).decode('utf-8', errors='ignore')
                break
        else:
            time.sleep(0.1)
    
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    clean = ansi_escape.sub('', raw_output)
    
    match = re.search(r'===BASE64_START_' + token + r'===\s+([A-Za-z0-9+/=\r\n\s]+?)\s+===BASE64_END_RC_' + token + r':(-?\d+)===', clean)
    if match:
        b64_data = match.group(1).replace('\r', '').replace('\n', '').replace(' ', '')
        rc = int(match.group(2))
        try:
            out = base64.b64decode(b64_data).decode('utf-8', errors='replace')
            return rc, out
        except Exception as e:
            return -1, f"Base64 decode error: {e}\nRaw clean: {clean}"
    return -1, clean

if __name__ == '__main__':
    session = sys.argv[1] if len(sys.argv) > 1 else 'vyUvDyfVq5tQ5Ll20bR0'
    cmd = sys.argv[2] if len(sys.argv) > 2 else 'pwd'
    wait = float(sys.argv[3]) if len(sys.argv) > 3 else 15.0
    rc, out = run_command(session, cmd, wait)
    print(out, end='')
    sys.exit(rc)
