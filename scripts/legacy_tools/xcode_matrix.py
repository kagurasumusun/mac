#!/usr/bin/env python3
"""Build one catalog with every installed Xcode/Apple platform and record evidence."""
from __future__ import annotations
import argparse, concurrent.futures, json, os, signal
from pathlib import Path
import subprocess, tempfile

PLATFORMS = {
    "macosx": ("macosx", "13.0"), "iphoneos": ("iphoneos", "15.0"),
    "appletvos": ("appletvos", "15.0"), "watchos": ("watchos", "8.0"),
    "xros": ("xros", "1.0"),
}

def run(command: list[str], env: dict[str, str], timeout: int = 20) -> dict[str, object]:
    p = subprocess.Popen(command, env=env, text=True, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, start_new_session=True)
    try:
        stdout, stderr = p.communicate(timeout=timeout)
        return {"command": command, "exit_code": p.returncode, "stdout": stdout, "stderr": stderr}
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        stdout, stderr = p.communicate()
        return {"command": command, "exit_code": 124, "stdout": stdout, "stderr": stderr + "\ntimeout"}

def process(app: Path, sdk: str, platform: str, target: str, catalog: Path, root: Path) -> dict[str, object]:
    env = os.environ.copy(); env["DEVELOPER_DIR"] = str(app / "Contents/Developer")
    version = run(["xcodebuild", "-version"], env, 10)
    sdk_check = run(["xcrun", "--sdk", sdk, "--show-sdk-path"], env, 10)
    row: dict[str, object] = {"xcode_app": str(app), "xcode": version, "sdk": sdk,
                              "platform": platform, "target": target, "sdk_check": sdk_check}
    if sdk_check["exit_code"] != 0:
        row["status"] = "sdk-unavailable"; return row
    out = root / f"{app.stem}-{sdk}"; out.mkdir()
    build = run(["xcrun", "--sdk", sdk, "actool", "--compile", str(out), "--platform",
                 platform, "--minimum-deployment-target", target, str(catalog)], env, 25)
    row["build"] = build; car = out / "Assets.car"
    if build["exit_code"] != 0 or not car.is_file():
        row["status"] = "build-timeout" if build["exit_code"] == 124 else "build-failed"; return row
    info = run(["xcrun", "--sdk", sdk, "assetutil", "--info", str(car)], env, 20)
    row["assetutil"] = info
    if info["exit_code"] != 0:
        row["status"] = "assetutil-failed"; return row
    try:
        parsed = json.loads(str(info["stdout"])); row["summary"] = parsed[0]; row["assets"] = parsed[1:]
        row["status"] = "pass"
    except json.JSONDecodeError:
        row["status"] = "assetutil-invalid-json"
    return row

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("catalog", type=Path)
    ap.add_argument("--output", type=Path, default=Path("xcode-matrix.json")); ap.add_argument("--workers", type=int, default=6)
    ns = ap.parse_args(); apps = sorted(Path("/Applications").glob("Xcode*.app")); catalog = ns.catalog.resolve()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); jobs = [(app, sdk, *values, catalog, root) for app in apps for sdk, values in PLATFORMS.items()]
        with concurrent.futures.ThreadPoolExecutor(max_workers=ns.workers) as pool:
            rows = list(pool.map(lambda args: process(*args), jobs))
    rows.sort(key=lambda r: (str(r["xcode_app"]), str(r["sdk"])))
    ns.output.write_text(json.dumps({"schema": 1, "catalog": str(catalog), "rows": rows}, indent=2, sort_keys=True))
    counts: dict[str, int] = {}
    for row in rows: counts[str(row["status"])] = counts.get(str(row["status"]), 0) + 1
    print(json.dumps(counts, sort_keys=True)); print(ns.output)
    return 0 if counts.get("pass", 0) else 1

if __name__ == "__main__": raise SystemExit(main())
