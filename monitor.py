import os,sys,time,signal,subprocess,argparse
from datetime import datetime
try:
    import psutil
except:
    subprocess.run([sys.executable,"-m","pip","install","psutil"],check=True)
    import psutil

ROBLOX_PKG="com.roblox.client"
CHECK_INTERVAL=5
REJOIN_COOLDOWN=25
FLAG_FILENAME="disconnect.flag"
EXECUTOR_PATHS=["/sdcard/Fluxus/workspace/","/sdcard/Delta/workspace/","/sdcard/AceusX/workspace/","/sdcard/ArceusX/workspace/","/sdcard/Hydrogen/workspace/","/sdcard/Codex/workspace/","/sdcard/Trigon/workspace/","/sdcard/Xeno/workspace/",os.path.expanduser("~/"),"/sdcard/"]

def log(msg,level="INFO"):
    icons={"INFO":"ℹ️","OK":"✅","WARN":"⚠️","ERROR":"❌","ACTION":"🚀","FLAG":"🚩","KILL":"💀","RAM":"🧠"}
    ts=datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {icons.get(level,'  ')} {msg}",flush=True)

def check_flag():
    for folder in EXECUTOR_PATHS:
        p=os.path.join(folder,FLAG_FILENAME)
        try:
            if os.path.exists(p):
                content=open(p).read().strip()
                if content:
                    reason=content.split("|")[1] if "|" in content else "unknown"
                    return True,reason,p
        except:pass
    return False,None,None

def clear_flags():
    for folder in EXECUTOR_PATHS:
        p=os.path.join(folder,FLAG_FILENAME)
        try:
            if os.path.exists(p):open(p,"w").write("")
        except:pass

def is_running():
    for proc in psutil.process_iter(["name","cmdline"]):
        try:
            n=(proc.info["name"]or"").lower()
            c=" ".join(proc.info["cmdline"]or[]).lower()
            if "roblox" in n or ROBLOX_PKG in c:return True
        except:pass
    try:
        r=subprocess.run(["am","stack","list"],capture_output=True,text=True,timeout=5)
        if ROBLOX_PKG in r.stdout:return True
    except:pass
    return False

def kill_roblox():
    log("Killing Roblox...","KILL")
    for proc in psutil.process_iter(["name","cmdline","pid"]):
        try:
            n=(proc.info["name"]or"").lower()
            c=" ".join(proc.info["cmdline"]or[]).lower()
            if "roblox" in n or ROBLOX_PKG in c:
                os.kill(proc.pid,signal.SIGKILL)
        except:pass
    try:subprocess.run(["am","force-stop",ROBLOX_PKG],timeout=5,capture_output=True)
    except:pass
    time.sleep(2)

def launch(place_id):
    log(f"Launching place {place_id}","ACTION")
    try:
        r=subprocess.run([
            "am","start","-n",
            f"{ROBLOX_PKG}/com.roblox.client.ActivityProtocolLaunch",
            "-a","android.intent.action.VIEW",
            "-d",f"roblox://placeId={place_id}&launchData=rejoin"
        ],capture_output=True,text=True,timeout=10)
        if r.returncode==0:
            log("Launched via ActivityProtocolLaunch ✓","OK")
            return True
    except:pass
    try:
        r=subprocess.run([
            "am","start",
            "-a","android.intent.action.VIEW",
            "-d",f"roblox://placeId={place_id}",
            "-p",ROBLOX_PKG
        ],capture_output=True,text=True,timeout=10)
        if r.returncode==0:
            log("Launched via deep link ✓","OK")
            return True
    except:pass
    try:
        subprocess.run(["termux-open-url",f"roblox://placeId={place_id}"],capture_output=True,timeout=10)
        log("Launched via termux-open-url ✓","OK")
        return True
    except:pass
    log("All launch methods failed!","ERROR")
    return False

def rejoin(place_id,reason,fresh=False):
    log(f"REJOIN — {reason}","ACTION")
    if fresh:
        kill_roblox()
        time.sleep(3)
    clear_flags()
    launch(place_id)
    log(f"Waiting {REJOIN_COOLDOWN}s for game to load...","ACTION")
    time.sleep(REJOIN_COOLDOWN)

def get_ram():
    try:return psutil.virtual_memory().percent
    except:return 0

def monitor(place_id,ram_limit):
    print("\n╔══════════════════════════════════╗")
    print("║  Roblox Auto-Rejoin Monitor 🎮   ║")
    print("╚══════════════════════════════════╝\n")
    log(f"Place ID: {place_id}")
    log(f"RAM limit: {ram_limit}%","RAM")
    clear_flags()
    log("Initial launch...","ACTION")
    launch(place_id)
    time.sleep(REJOIN_COOLDOWN)
    crashes=0
    while True:
        try:
            ram=get_ram()
            log(f"RAM: {ram:.1f}%")
            if ram>=ram_limit:
                log(f"RAM overload! {ram:.1f}%","RAM")
                rejoin(place_id,f"ram({ram:.0f}%)",fresh=True)
                crashes=0
                continue
            found,reason,path=check_flag()
            if found:
                log(f"Disconnect flag! {reason}","FLAG")
                rejoin(place_id,f"flag:{reason}",fresh=False)
                crashes=0
                continue
            if not is_running():
                crashes+=1
                log(f"Roblox not running ({crashes}/2)","WARN")
                if crashes>=2:
                    rejoin(place_id,"crash",fresh=True)
                    crashes=0
            else:
                if crashes>0:log("Roblox running ✓","OK")
                crashes=0
            time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:log("Stopped.","WARN");break
        except Exception as e:log(f"Error: {e}","ERROR");time.sleep(CHECK_INTERVAL)

parser=argparse.ArgumentParser()
parser.add_argument("--place-id","-p",required=True)
parser.add_argument("--ram-limit","-r",type=float,default=90)
args=parser.parse_args()
monitor(args.place_id,args.ram_limit)
