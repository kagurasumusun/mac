from pathlib import Path
import json
from actool_linux.model import load_catalog

def setup_catalog():
    root = Path("test_ns.xcassets")
    root.mkdir(exist_ok=True)
    
    group = root / "MyGroup"
    group.mkdir(exist_ok=True)
    (group / "Contents.json").write_text(json.dumps({
        "properties": {"provides-namespace": True},
        "info": {"version": 1, "author": "xcode"}
    }))
    
    image = group / "MyImage.imageset"
    image.mkdir(exist_ok=True)
    (image / "Contents.json").write_text(json.dumps({
        "images": [{"idiom": "universal", "filename": "test.png"}],
        "info": {"version": 1, "author": "xcode"}
    }))
    (image / "test.png").write_bytes(b"")

    catalog = load_catalog(root)
    for asset in catalog.assets:
        print(f"Found asset: {asset.name} (kind: {asset.kind})")

setup_catalog()
