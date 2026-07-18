#!/usr/bin/env python3
"""Capture byte-exact actool version plists from every installed Xcode app."""
from __future__ import annotations
import base64,hashlib,json,os,plistlib,subprocess
from pathlib import Path
rows=[]
for app in sorted(Path('/Applications').glob('Xcode*.app')):
 env=os.environ.copy();env['DEVELOPER_DIR']=str(app/'Contents/Developer')
 v=subprocess.run(['xcodebuild','-version'],env=env,capture_output=True,text=True,timeout=20)
 p=subprocess.run(['xcrun','actool','--version','--output-format','xml1'],env=env,capture_output=True,timeout=20)
 try:parsed=plistlib.loads(p.stdout)
 except Exception:parsed=None
 rows.append({'app':str(app),'xcodebuild':v.stdout,'exit_code':p.returncode,'stdout_b64':base64.b64encode(p.stdout).decode(),'stdout_sha256':hashlib.sha256(p.stdout).hexdigest(),'stderr_b64':base64.b64encode(p.stderr).decode(),'parsed':parsed})
print(json.dumps({'schema':1,'rows':rows},indent=2))
