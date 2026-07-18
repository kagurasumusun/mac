#!/usr/bin/env python3
"""Classify Apple-vs-cleanroom CAR pairs across corpora.

Usage: oracle_census.py APPLE_ROOT OURS_ROOT [--json OUT]

For every CAR present under both roots (matched by path relative to each
root's immediate case directory), classify the pair:
  exact    - zero diffs
  hash16   - only facet-hash16 (cosmetic, documented) diffs
  payload  - payload-byte diffs inside dmp2/deepmap streams
  struct   - size/structural/TLV diffs (real divergence)
  missing  - CAR present on exactly one side

Exit code: 1 when any struct or missing case exists, else 0 (payload/hash16
are tracked but non-fatal; they are documented residual divergence).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def cars(root: Path) -> dict[str, Path]:
    out = {}
    for p in root.rglob("*.car"):
        try:
            rel = p.relative_to(root)
        except ValueError:
            rel = p.name
        out[str(rel)] = p
    return out


def classify(mismatches: list) -> set[str]:
    kinds = set()
    for d in mismatches:
        s = str(d)
        if "kCRThemeIdentifierName" in s:
            kinds.add("hash16")
        elif "payload" in s or "stream" in s:
            kinds.add("payload")
        else:
            kinds.add("struct:" + s.split(":")[0])
    return kinds


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("apple", type=Path)
    ap.add_argument("ours", type=Path)
    ap.add_argument("--json", type=Path)
    ns = ap.parse_args()

    acars, ocars = cars(ns.apple), cars(ns.ours)
    names = sorted(set(acars) | set(ocars))
    total = Counter()
    struct_detail = []
    pair_detail = {}
    for n in names:
        if n not in acars or n not in ocars:
            total["missing"] += 1
            struct_detail.append((n, "missing-one-side"))
            pair_detail[n] = {"class": "missing"}
            continue
        outp = subprocess.run(
            [sys.executable, str(REPO / "tools/diff_cars.py"), "--json", "-",
             str(acars[n]), str(ocars[n])],
            capture_output=True, text=True, cwd=REPO)
        try:
            blob = json.loads(outp.stdout or "{}")
            mismatches = blob.get("mismatches", [])
        except Exception:
            total["struct"] += 1
            struct_detail.append((n, "unparseable"))
            pair_detail[n] = {"class": "struct", "kinds": ["unparseable"]}
            continue
        kinds = classify(mismatches)
        if not kinds:
            total["exact"] += 1
            pair_detail[n] = {"class": "exact"}
        elif kinds <= {"hash16"}:
            total["hash16"] += 1
            pair_detail[n] = {"class": "hash16",
                              "diffs": [str(d) for d in mismatches]}
        elif any(k.startswith("struct") for k in kinds):
            total["struct"] += 1
            struct_detail.append((n, sorted(kinds)))
            pair_detail[n] = {"class": "struct", "kinds": sorted(kinds),
                              "diffs": [str(d) for d in mismatches][:40]}
        else:
            total["payload"] += 1
            pair_detail[n] = {"class": "payload",
                              "diffs": [str(d) for d in mismatches][:40]}

    summary = {
        "apple_root": str(ns.apple),
        "ours_root": str(ns.ours),
        "pairs": len(names),
        "counts": dict(total),
        "struct_detail": struct_detail,
        "pair_detail": pair_detail,
    }
    text = json.dumps(summary, indent=2, ensure_ascii=False)
    if ns.json:
        ns.json.parent.mkdir(parents=True, exist_ok=True)
        ns.json.write_text(text + "\n")
    print(f"pairs={len(names)}  " + "  ".join(f"{k}={v}" for k, v in sorted(total.items())))
    for n, k in struct_detail[:30]:
        print("  STRUCT", n, k)
    return 1 if (total["struct"] or total["missing"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
