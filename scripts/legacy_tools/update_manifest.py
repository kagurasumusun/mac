#!/usr/bin/env python3
import hashlib, json
from pathlib import Path

root = Path(".")
manifest_path = root / "EVIDENCE_MANIFEST.json"
manifest = json.loads(manifest_path.read_text())

for row in manifest.get("files", []):
    path = root / row["path"]
    if path.is_file():
        raw = path.read_bytes()
        row["size"] = len(raw)
        row["sha256"] = hashlib.sha256(raw).hexdigest()

# Drop entries whose files were removed from the tree.
manifest["files"] = [row for row in manifest.get("files", []) if (root / row["path"]).is_file()]

manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
print("Updated EVIDENCE_MANIFEST.json")
