#!/usr/bin/env python3
"""Batch diff classification across all Apple-oracle corpora vs our outputs.

Counts cases by worst diff class:
  exact    - zero diffs
  hash16   - only facet-hash16 (cosmetic, documented) diffs
  payload  - payload-byte diffs inside dmp2 streams
  struct   - size/structural/TLV diffs (real divergence)
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = "/home/user/mac-repo"

PAIRS = [
    ("probe5", "/home/user/work/probe5-out", "/home/user/work/ours-fresh5"),
    ("probe6", "/home/user/work/probe6-out", "/home/user/work/ours-probe6-v2"),
    ("probe3", "/home/user/work/probe3-out", "/home/user/work/ours-probe3-v2"),
    ("basic", "/home/user/work/apple-out/basic", "/home/user/work/ours-cars/basic"),
    ("brand", "/home/user/work/apple-out/brand", "/home/user/work/ours-cars/brand"),
    ("colordata", "/home/user/work/apple-out/colordata", "/home/user/work/ours-cars/colordata"),
    ("scales", "/home/user/work/apple-out/scales", "/home/user/work/ours-cars/scales"),
    ("tvstack", "/home/user/work/apple-out/tvstack", "/home/user/work/ours-cars/tvstack"),
]


def cars(root):
    root = Path(root)
    if not root.is_dir():
        return {}
    return {p.parent.name + "/" + p.name: p for p in root.rglob("*.car")}


def classify(diff):
    kinds = set()
    for d in diff:
        s = str(d)
        if "kCRThemeIdentifierName" in s:
            kinds.add("hash16")
        elif "payload" in s:
            kinds.add("payload")
        else:
            kinds.add("struct:" + s.split(":")[0])
    return kinds


def main():
    grand = {}
    detail = {}
    for suite, aroot, oroot in PAIRS:
        acars, ocars = cars(aroot), cars(oroot)
        names = sorted(set(acars) & set(ocars))
        if not names:
            # try flat naming: files directly under root
            acars = {p.name: p for p in Path(aroot).glob("*.car")} if Path(aroot).is_dir() else {}
            ocars = {p.name: p for p in Path(oroot).glob("*.car")} if Path(oroot).is_dir() else {}
            names = sorted(set(acars) & set(ocars))
        counts = dict(exact=0, hash16=0, payload=0, struct=0, missing=0)
        for n in names:
            outp = subprocess.run(
                [sys.executable, f"{REPO}/tools/diff_cars.py", "--json", "-",
                 str(acars[n]), str(ocars[n])],
                capture_output=True, text=True)
            try:
                blob = json.loads(outp.stdout or "{}")
                diff = blob.get("mismatches", [])
            except Exception:
                counts["struct"] += 1
                detail.setdefault(suite, []).append((n, "unparseable"))
                continue
            kinds = classify(diff)
            if not kinds:
                counts["exact"] += 1
            elif kinds <= {"hash16", "identifier", "hash"}:
                counts["hash16"] += 1
            elif any("payload" in k or "stream" in k for k in kinds):
                counts["payload"] += 1
            else:
                counts["struct"] += 1
                detail.setdefault(suite, []).append((n, sorted(kinds)))
        grand[suite] = (len(names), counts)
    total = dict(exact=0, hash16=0, payload=0, struct=0, missing=0)
    tn = 0
    for suite, (n, counts) in grand.items():
        print(f"{suite:10s} n={n:3d}  " + "  ".join(f"{k}={v}" for k, v in counts.items() if v))
        for k, v in counts.items():
            total[k] += v
        tn += n
    print("-" * 70)
    print(f"TOTAL n={tn}  " + "  ".join(f"{k}={v}" for k, v in total.items() if v))
    for suite, items in detail.items():
        print(f"## struct details {suite}:")
        for n, k in items[:20]:
            print("   ", n, k)


if __name__ == "__main__":
    main()
