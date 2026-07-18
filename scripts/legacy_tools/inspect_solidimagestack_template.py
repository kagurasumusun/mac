from pathlib import Path
import json
root = Path('/Applications/Xcode_26.5.app/Contents/Developer/Library/Xcode/Templates/Project Templates/MultiPlatform/Application/visionOS Foveated Streaming App.xctemplate/Assets.xcassets')
for p in sorted(root.rglob('*')):
    print(p)
    if p.is_file() and p.name == 'Contents.json':
        print(p.read_text())
        print('---')
