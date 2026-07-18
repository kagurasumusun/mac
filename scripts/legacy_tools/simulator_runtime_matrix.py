#!/usr/bin/env python3
"""Inventory and optionally boot one compatible device for every Simulator runtime."""
from __future__ import annotations
import argparse, json, subprocess, time
from pathlib import Path

DEVICE_HINTS={"iOS":"iPhone 17 Pro","tvOS":"Apple TV 4K (3rd generation)","watchOS":"Apple Watch Series 11 (46mm)","xrOS":"Apple Vision Pro"}

def run(*args, timeout=120):
 p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
 return p.returncode,p.stdout,p.stderr

def inventory():
 _,raw,_=run("xcrun","simctl","list","-j")
 data=json.loads(raw); types=data["devicetypes"]
 out=[]
 for r in data["runtimes"]:
  platform=r.get("platform") or ("xrOS" if r["name"].startswith("visionOS") else r["name"].split()[0])
  hint=DEVICE_HINTS.get(platform); matches=[d for d in types if d["name"]==hint]
  out.append({"name":r["name"],"version":r.get("version"),"identifier":r["identifier"],"platform":platform,"available":r.get("isAvailable",False),"device_type":matches[0]["identifier"] if matches else None,"status":"inventory"})
 return out

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--boot",action="store_true");ap.add_argument("--output",type=Path);ns=ap.parse_args(); rows=inventory()
 def save():
  report={"generated_by":"actool-linux","count":len(rows),"runtimes":rows}
  text=json.dumps(report,indent=2)
  if ns.output: ns.output.write_text(text+"\n")
  return text
 save()
 if ns.boot:
  for row in rows:
   if not row["available"] or not row["device_type"]: row["status"]="unsupported-device-type";save();continue
   name="actool-linux-"+row["name"].replace(" ","-").replace(".","-")
   rc,udid,err=run("xcrun","simctl","create",name,row["device_type"],row["identifier"])
   if rc: row.update(status="create-failed",error=err.strip());save();continue
   row["udid"]=udid.strip(); start=time.time()
   try:
    run("xcrun","simctl","boot",row["udid"],timeout=30)
    rc,_,err=run("xcrun","simctl","bootstatus",row["udid"],"-b",timeout=240)
    row.update(status="booted" if rc==0 else "boot-failed",seconds=round(time.time()-start,2),error=err.strip())
   except subprocess.TimeoutExpired: row.update(status="boot-timeout",seconds=round(time.time()-start,2))
   finally:
    for action in ("shutdown","delete"):
     try: run("xcrun","simctl",action,row["udid"],timeout=30)
     except subprocess.TimeoutExpired: row.setdefault("cleanup_errors",[]).append(action+"-timeout")
    save()
 print(save())
if __name__=="__main__": main()
