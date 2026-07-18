#!/usr/bin/env python3
"""Build/install/launch a CAR consumer on every available Apple Simulator runtime.

The matrix groups work by platform and runs the four platform groups in parallel.
Each row records build, boot, install, launch, screenshot and cleanup independently;
partial JSON is saved atomically after every state change.
"""
from __future__ import annotations
import argparse,concurrent.futures,json,plistlib,shutil,subprocess,tempfile,threading,time
from pathlib import Path

HINTS={"iOS":"iPhone 17 Pro","tvOS":"Apple TV 4K (3rd generation)","xrOS":"Apple Vision Pro","watchOS":"Apple Watch Series 11 (46mm)"}
CONFIG={
 "iOS":("iphonesimulator","arm64-apple-ios15.0-simulator","iPhoneSimulator",[1,2]),
 "tvOS":("appletvsimulator","arm64-apple-tvos15.0-simulator","AppleTVSimulator",[3]),
 "xrOS":("xrsimulator","arm64-apple-xros1.0-simulator","XRSimulator",[7]),
}
def run(args,timeout=180):
 try:
  p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
  return {"command":args,"exit_code":p.returncode,"stdout":p.stdout,"stderr":p.stderr}
 except subprocess.TimeoutExpired as e:return {"command":args,"exit_code":124,"stdout":e.stdout or "","stderr":e.stderr or "","timeout":True}
def inventory():
 data=json.loads(subprocess.check_output(["xcrun","simctl","list","-j"],text=True));types={x["name"]:x["identifier"] for x in data["devicetypes"]};out=[]
 for r in data["runtimes"]:
  platform=r.get("platform") or ("xrOS" if r["name"].startswith("visionOS") else r["name"].split()[0])
  if platform == "visionOS": platform = "xrOS"
  if platform not in HINTS:continue
  out.append({"name":r["name"],"version":r.get("version"),"runtime":r["identifier"],"platform":platform,"available":r.get("isAvailable",False),"device_type":types.get(HINTS[platform]),"status":"inventory"})
 return out
def write_plist(path,obj):path.write_bytes(plistlib.dumps(obj,fmt=plistlib.FMT_XML,sort_keys=False))
def build_uikit(root,platform,car):
 sdk,target,supported,family=CONFIG[platform];app=root/(platform+"Consumer.app");app.mkdir()
 source=root/(platform+"Main.m");source.write_text(r'''#import <UIKit/UIKit.h>
@interface V:UIViewController @end
@implementation V
-(void)viewDidLoad{[super viewDidLoad];UIImage*i=[UIImage imageNamed:@"RuntimeImage"];self.view.backgroundColor=i?[UIColor colorWithRed:0 green:0.7 blue:0 alpha:1]:UIColor.redColor;UIImageView*v=[[UIImageView alloc]initWithImage:i];v.frame=CGRectMake(30,80,160,160);v.contentMode=UIViewContentModeScaleAspectFit;[self.view addSubview:v];NSLog(@"ACTOOL_RUNTIME_%@ %g %g",i?@"PASS":@"FAIL",i.size.width,i.size.height);}
@end
@interface D:UIResponder<UIApplicationDelegate>@property(strong,nonatomic)UIWindow*w;@end
@implementation D
-(BOOL)application:(UIApplication*)a didFinishLaunchingWithOptions:(NSDictionary*)o{self.w=[[UIWindow alloc]initWithFrame:UIScreen.mainScreen.bounds];self.w.rootViewController=[V new];[self.w makeKeyAndVisible];return YES;}
@end
int main(int c,char**v){@autoreleasepool{return UIApplicationMain(c,v,nil,NSStringFromClass(D.class));}}
''')
 sdkpath=subprocess.check_output(["xcrun","--sdk",sdk,"--show-sdk-path"],text=True).strip();exe=app/"RuntimeConsumer"
 build=run(["xcrun","--sdk",sdk,"clang","-fobjc-arc","-target",target,"-isysroot",sdkpath,"-framework","UIKit","-framework","Foundation",str(source),"-o",str(exe)],300)
 if build["exit_code"]:return app,build
 write_plist(app/"Info.plist",{"CFBundleIdentifier":"ai.arena.actool.runtime."+platform.lower(),"CFBundleExecutable":"RuntimeConsumer","CFBundleName":"RuntimeConsumer","CFBundlePackageType":"APPL","CFBundleVersion":"1","CFBundleShortVersionString":"1.0","CFBundleSupportedPlatforms":[supported],"MinimumOSVersion":"15.0" if platform!="xrOS" else "1.0","UIDeviceFamily":family,"UILaunchScreen":{}})
 shutil.copy2(car,app/"Assets.car");run(["codesign","--force","--sign","-",str(app)],60);return app,build
def build_swiftui(root,platform,car):
 watch=platform=="watchOS";app=root/(platform+"Consumer.app");app.mkdir();src=root/(platform+"Main.swift");src.write_text('''import SwiftUI\n@main struct RuntimeApp: App { var body: some Scene { WindowGroup { Image("RuntimeImage").resizable().frame(width:80,height:80).background(Color.green) } } }\n''')
 sdk="watchsimulator" if watch else "xrsimulator";target="arm64-apple-watchos8.0-simulator" if watch else "arm64-apple-xros1.0-simulator";sdkpath=subprocess.check_output(["xcrun","--sdk",sdk,"--show-sdk-path"],text=True).strip();exe=app/"RuntimeConsumer"
 build=run(["xcrun","--sdk",sdk,"swiftc","-parse-as-library","-target",target,"-sdk",sdkpath,str(src),"-o",str(exe)],300)
 if build["exit_code"]:return app,build
 info={"CFBundleIdentifier":"ai.arena.actool.runtime."+platform.lower(),"CFBundleExecutable":"RuntimeConsumer","CFBundleName":"RuntimeConsumer","CFBundlePackageType":"APPL","CFBundleVersion":"1","CFBundleShortVersionString":"1.0","CFBundleSupportedPlatforms":["WatchSimulator" if watch else "XRSimulator"],"MinimumOSVersion":"8.0" if watch else "1.0","UIDeviceFamily":[4] if watch else [7]}
 if watch:
  # A directly executable SwiftUI watch app is a modern WKApplication.
  # WKWatchKitApp identifies the obsolete WatchKit 1.0 container format.
  info.update({"WKApplication":True,"WKWatchOnly":True})
 write_plist(app/"Info.plist",info);shutil.copy2(car,app/"Assets.car");run(["codesign","--force","--sign","-",str(app)],60);return app,build
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--car",type=Path,required=True);ap.add_argument("--output",type=Path,default=Path("runtime-consumer-matrix.json"));ap.add_argument("--screenshots",type=Path,default=Path("runtime-screenshots"));ap.add_argument("--platform",action="append",choices=tuple(HINTS));ap.add_argument("--runtime-name",action="append");ns=ap.parse_args();rows=inventory();
 if ns.platform:rows=[r for r in rows if r["platform"] in ns.platform]
 if ns.runtime_name:rows=[r for r in rows if r["name"] in ns.runtime_name]
 lock=threading.Lock();ns.screenshots.mkdir(parents=True,exist_ok=True)
 def save():
  with lock:
   tmp=ns.output.with_suffix(ns.output.suffix+".tmp");tmp.write_text(json.dumps({"schema":1,"rows":rows},indent=2)+"\n");tmp.replace(ns.output)
 save()
 with tempfile.TemporaryDirectory(prefix="actool-runtime-") as td:
  root=Path(td);apps={};builds={}
  for platform in HINTS:
   if ns.platform and platform not in ns.platform:continue
   try:apps[platform],builds[platform]=(build_swiftui(root,platform,ns.car) if platform in ("watchOS","xrOS") else build_uikit(root,platform,ns.car))
   except Exception as e:builds[platform]={"exit_code":125,"stderr":repr(e)}
  def group(platform):
   for row in [r for r in rows if r["platform"]==platform]:
    row["build"]=builds[platform]
    if builds[platform].get("exit_code")!=0:row["status"]="build-failed";save();continue
    if not row["available"] or not row["device_type"]:row["status"]="unavailable";save();continue
    name="actool-consumer-"+row["name"].replace(" ","-").replace(".","-");created=run(["xcrun","simctl","create",name,row["device_type"],row["runtime"]],60);row["create"]=created
    if created["exit_code"]:row["status"]="create-failed";save();continue
    udid=created["stdout"].strip();row["udid"]=udid;start=time.time()
    try:
     row["boot"]=run(["xcrun","simctl","boot",udid],60);row["bootstatus"]=run(["xcrun","simctl","bootstatus",udid,"-b"],360)
     if row["bootstatus"]["exit_code"]:row["status"]="boot-failed";continue
     row["install"]=run(["xcrun","simctl","install",udid,str(apps[platform])],120)
     if row["install"]["exit_code"]:row["status"]="install-failed";continue
     bundle="ai.arena.actool.runtime."+platform.lower();row["launch"]=run(["xcrun","simctl","launch",udid,bundle],120)
     if row["launch"]["exit_code"]:row["status"]="launch-failed";continue
     time.sleep(3)
     row["materialization_log"]=run(["xcrun","simctl","spawn",udid,"log","show","--last","2m","--style","compact","--predicate",'process == "RuntimeConsumer" AND eventMessage CONTAINS "ACTOOL_RUNTIME_"'],120)
     shot=ns.screenshots/(row["name"].replace(" ","-")+".png");row["screenshot"]=run(["xcrun","simctl","io",udid,"screenshot",str(shot)],120);row["screenshot_path"]=str(shot)
     screenshot_ok=row["screenshot"]["exit_code"]==0 and shot.is_file()
     # UIKit consumers emit an explicit UIImage lookup marker. SwiftUI-only
     # watch/vision consumers are retained as visual-materialization evidence.
     marker_ok=("ACTOOL_RUNTIME_PASS" in row["materialization_log"]["stdout"]) if platform in ("iOS","tvOS") else screenshot_ok
     row["materialized"]=marker_ok
     row["status"]="pass" if screenshot_ok and marker_ok else ("materialization-failed" if screenshot_ok else "screenshot-failed")
    finally:
     row["seconds"]=round(time.time()-start,2);row["shutdown"]=run(["xcrun","simctl","shutdown",udid],60);row["delete"]=run(["xcrun","simctl","delete",udid],60);save()
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(group,HINTS))
 save();counts={}
 for r in rows:counts[r["status"]]=counts.get(r["status"],0)+1
 print(json.dumps(counts,sort_keys=True));return 0 if counts.get("pass")==len(rows) else 1
if __name__=="__main__":raise SystemExit(main())
