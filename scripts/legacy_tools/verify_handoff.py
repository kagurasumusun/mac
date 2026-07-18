#!/usr/bin/env python3
"""Verify the persisted cross-session handoff and evidence file hashes."""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
manifest_path=ROOT/'EVIDENCE_MANIFEST.json'
required=['docs/SESSION_HANDOFF_COMPLETE.md','HANDOFF.md','ENGINEERING_LOG.md','PROJECT_STATE.json','VERIFICATION.md','EVIDENCE_MANIFEST.json']
errors=[]
for name in required:
 if not (ROOT/name).is_file():errors.append(f'missing required file: {name}')
if manifest_path.is_file():
 try:manifest=json.loads(manifest_path.read_text())
 except Exception as exc:errors.append(f'invalid manifest JSON: {exc}');manifest={'files':[]}
 for row in manifest.get('files',[]):
  path=ROOT/row['path']
  if not path.is_file():errors.append(f'missing manifested file: {row["path"]}');continue
  raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
  if len(raw)!=row['size']:errors.append(f'size mismatch: {row["path"]}')
  if digest!=row['sha256']:errors.append(f'hash mismatch: {row["path"]}')
for name in ('PROJECT_STATE.json','research/diagnostic-schema3.json','research/runtime-consumer-matrix-verified.json'):
 path=ROOT/name
 if path.is_file():
  try:json.loads(path.read_text())
  except Exception as exc:errors.append(f'invalid JSON {name}: {exc}')
if errors:
 print('\n'.join(errors),file=sys.stderr);raise SystemExit(1)
print(f'HANDOFF_OK {len(manifest.get("files",[]))} manifested files')
