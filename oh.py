import os,sys,time,signal,subprocess,json,threading
from datetime import datetime

try:
    import psutil
except:
    subprocess.run([sys.executable,"-m","pip","install","psutil"],check=True)
    import psutil

try:
    import urllib.request,urllib.parse
except:pass

ROBLOX_PKG="com.roblox.client"
FLAG_FILENAME="disconnect.flag"
GAMES_FILE=os.path.expanduser("~/roblox_games.json")
CONFIG_FILE=os.path.expanduser("~/roblox_config.json")
EXECUTOR_PATHS=[
    "/sdcard/Fluxus/workspace/","/sdcard/Delta/workspace/",
    "/sdcard/AceusX/workspace/","/sdcard/ArceusX/workspace/",
    "/sdcard/Hydrogen/workspace/","/sdcard/Codex/workspace/",
    "/sdcard/Trigon/workspace/","/sdcard/Xeno/workspace/",
    os.path.expanduser("~/"),"/sdcard/"
]

def cl(t,c):return f"\033[{c}m{t}\033[0m"
def log(msg,level="INFO"):
    icons={"INFO":cl("ℹ","96"),"OK":cl("✓","92"),"WARN":cl("!","93"),
           "ERROR":cl("✗","91"),"ACTION":cl("»","95"),"FLAG":cl("⚑","93"),
           "KILL":cl("☠","91"),"RAM":cl("▣","94"),"TIMER":cl("◷","96"),
           "WEBHOOK":cl("⬆","95")}
    ts=cl(datetime.now().strftime("%H:%M:%S"),"2")
    print(f"[{ts}] {icons.get(level,'·')} {msg}",flush=True)

def inp(prompt,default=None):
    suffix=f" [{cl(str(default),'93')}]" if default is not None else ""
    try:
        v=input(f"  {cl('→','96')} {prompt}{suffix}: ").strip()
        return v if v else (str(default) if default is not None else "")
    except(EOFError,KeyboardInterrupt):
        print();sys.exit(0)

def seconds_to_str(s):
    s=int(s)
    if s<60:return f"{s}s"
    elif s<3600:return f"{s//60}m {s%60}s"
    else:return f"{s//3600}h {(s%3600)//60}m"

def divider(w=50):print(cl("─"*w,"96"))

def banner():
    os.system("clear")
    print(f"""
{cl('╔══════════════════════════════════════════════════╗','96')}
{cl('║','96')}  {cl('Roblox Auto-Rejoin','1;97')} {cl('🎮','0')}  {cl('v5.0','2')}                      {cl('║','96')}
{cl('║','96')}  {cl('Game Manager · Config Save · Discord Webhook','2')}   {cl('║','96')}
{cl('╚══════════════════════════════════════════════════╝','96')}
""")

# ══════════════════════════════════════════════════
# SAVE / LOAD CONFIG
# ══════════════════════════════════════════════════
DEFAULT_CFG={
    "place_id":"",
    "check_interval":5,
    "rejoin_cooldown":25,
    "crash_delay":30,
    "crash_confirm":1,
    "ram_limit":90.0,
    "auto_restart":True,
    "restart_seconds":7200,
    "watch_flag":True,
    "webhook_url":"",
    "webhook_interval":60,
    "webhook_enabled":False,
}

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE) as f:
                saved=json.load(f)
                cfg={**DEFAULT_CFG,**saved}
                return cfg
    except:pass
    return dict(DEFAULT_CFG)

def save_config(cfg):
    try:
        with open(CONFIG_FILE,"w") as f:
            json.dump(cfg,f,indent=2)
    except Exception as e:
        log(f"Could not save config: {e}","WARN")

# ══════════════════════════════════════════════════
# GAME LIST
# ══════════════════════════════════════════════════
def load_games():
    try:
        if os.path.exists(GAMES_FILE):
            with open(GAMES_FILE) as f:return json.load(f)
    except:pass
    return []

def save_games(games):
    try:
        with open(GAMES_FILE,"w") as f:json.dump(games,f,indent=2)
    except:pass

def print_games(games):
    if not games:print(cl("  No saved games.","2"));return
    divider()
    for i,g in enumerate(games,1):
        print(f"  {cl(str(i),'95;1')}. {cl(g['name'],'93;1')}  {cl('—','2')} {cl(g['place_id'],'96')}")
    divider()

def game_manager(games):
    while True:
        banner()
        print(cl("  ── Game Manager ──────────────────────────────","96"))
        print_games(games)
        print(f"\n  {cl('1','92')}. Add game")
        if games:
            print(f"  {cl('2','91')}. Delete game")
            print(f"  {cl('3','93')}. Rename game")
        print(f"  {cl('0','96')}. Back")
        print()
        c=inp("Option").strip()
        if c=="1":
            name=inp("Game name")
            if not name:continue
            pid=inp("Place ID")
            if not pid or not pid.isdigit():
                print(cl("  Invalid Place ID","91"));time.sleep(1);continue
            games.append({"name":name,"place_id":pid})
            save_games(games)
            print(cl(f"  ✓ '{name}' saved!","92"));time.sleep(1)
        elif c=="2" and games:
            print_games(games)
            r=inp("Number to delete (0=cancel)","0")
            try:
                idx=int(r)-1
                if 0<=idx<len(games):
                    rem=games.pop(idx);save_games(games)
                    print(cl(f"  ✓ '{rem['name']}' deleted","92"));time.sleep(1)
            except:pass
        elif c=="3" and games:
            print_games(games)
            r=inp("Number to rename (0=cancel)","0")
            try:
                idx=int(r)-1
                if 0<=idx<len(games):
                    nn=inp(f"New name for '{games[idx]['name']}'")
                    if nn:games[idx]["name"]=nn;save_games(games)
                    print(cl(f"  ✓ Renamed","92"));time.sleep(1)
            except:pass
        elif c=="0":break
    return games

def pick_game(games,cfg):
    while True:
        banner()
        print(cl("  ── Select Game ───────────────────────────────","96"))
        print()
        if cfg.get("place_id"):
            print(f"  {cl('↺','92')} Last used: {cl(cfg['place_id'],'93')}")
            print()
        if games:
            for i,g in enumerate(games,1):
                print(f"  {cl(str(i),'95;1')}. {cl(g['name'],'93;1')}  {cl('—','2')} {cl(g['place_id'],'96')}")
            print()
            print(f"  {cl('M','92')}. Enter Place ID manually")
            print(f"  {cl('E','96')}. Manage games")
            if cfg.get("place_id"):
                print(f"  {cl('L','93')}. Use last used ({cfg['place_id']})")
            print()
            c=inp("Choose")
            if c.upper()=="E":games=game_manager(games);continue
            elif c.upper()=="L" and cfg.get("place_id"):return cfg["place_id"],games
            elif c.upper()=="M":
                pid=inp("Place ID")
                if pid and pid.isdigit():return pid,games
            else:
                try:
                    idx=int(c)-1
                    if 0<=idx<len(games):
                        ch=games[idx]
                        print(cl(f"\n  ✓ {ch['name']}","92"));time.sleep(0.5)
                        return ch["place_id"],games
                except:pass
            print(cl("  Invalid choice","91"))
        else:
            print(cl("  No saved games — add one or enter manually","93"))
            print(f"\n  {cl('1','92')}. Add a game")
            print(f"  {cl('2','92')}. Enter Place ID manually")
            print()
            c=inp("Option")
            if c=="1":games=game_manager(games)
            elif c=="2":
                pid=inp("Place ID")
                if pid and pid.isdigit():return pid,games

# ══════════════════════════════════════════════════
# SETTINGS MENU — numbered, all on one screen
# ══════════════════════════════════════════════════
def settings_menu(cfg):
    while True:
        banner()
        print(cl("  ── Settings ──────────────────────────────────","96"))
        print()

        ri=cfg["restart_seconds"]
        rstr=seconds_to_str(ri) if cfg["auto_restart"] else cl("Off","91")
        wi=cfg["webhook_interval"]
        wstr=f"every {seconds_to_str(wi)}" if cfg["webhook_enabled"] else cl("Off","91")
        wurl=cfg["webhook_url"]
        wshow=(wurl[:30]+"...") if len(wurl)>30 else wurl if wurl else cl("Not set","91")

        print(f"  {cl('1','95')}. Check interval       {cl(seconds_to_str(cfg['check_interval']),'93')}")
        print(f"  {cl('2','95')}. Rejoin cooldown       {cl(seconds_to_str(cfg['rejoin_cooldown']),'93')}")
        print(f"  {cl('3','95')}. Crash delay           {cl(seconds_to_str(cfg['crash_delay']),'93')}")
        print(f"  {cl('4','95')}. Crash confirm checks  {cl(str(cfg['crash_confirm']),'93')} checks")
        print(f"  {cl('5','95')}. RAM limit             {cl(str(cfg['ram_limit'])+'%','93')}")
        print(f"  {cl('6','95')}. Auto restart          {cl(rstr,'93')}")
        print(f"  {cl('7','95')}. Watch disconnect flag {cl('On','92') if cfg['watch_flag'] else cl('Off','91')}")
        print()
        print(cl("  ── Discord Webhook ───────────────────────────","96"))
        print()
        print(f"  {cl('8','95')}. Webhook enabled       {cl('On','92') if cfg['webhook_enabled'] else cl('Off','91')}")
        print(f"  {cl('9','95')}. Webhook URL           {cl(wshow,'96')}")
        print(f"  {cl('10','95')}. Webhook interval     {wstr}")
        print()
        divider()
        print(f"  {cl('S','92')}. Save & Start")
        print(f"  {cl('R','93')}. Reset to defaults")
        print()

        c=inp("Edit setting number or S to start").strip().upper()

        if c=="S":
            save_config(cfg)
            print(cl("\n  ✓ Config saved!","92"));time.sleep(0.5)
            break
        elif c=="R":
            cfg={**DEFAULT_CFG,"place_id":cfg["place_id"]}
            print(cl("  ✓ Reset to defaults","92"));time.sleep(0.5)
        elif c=="1":
            v=inp("Check interval (seconds)",cfg["check_interval"])
            try:cfg["check_interval"]=max(1,int(v))
            except:pass
        elif c=="2":
            v=inp("Rejoin cooldown (seconds)",cfg["rejoin_cooldown"])
            try:cfg["rejoin_cooldown"]=max(5,int(v))
            except:pass
        elif c=="3":
            v=inp("Crash rejoin delay (seconds)",cfg["crash_delay"])
            try:cfg["crash_delay"]=max(0,int(v))
            except:pass
        elif c=="4":
            v=inp("Crash confirm checks",cfg["crash_confirm"])
            try:cfg["crash_confirm"]=max(1,int(v))
            except:pass
        elif c=="5":
            v=inp("RAM % limit",cfg["ram_limit"])
            try:cfg["ram_limit"]=float(v)
            except:pass
        elif c=="6":
            print(f"\n  Current: {cl(rstr,'93')}")
            en=inp("Enable auto restart? (y/n)","y" if cfg["auto_restart"] else "n").lower()
            cfg["auto_restart"]=en in("y","yes")
            if cfg["auto_restart"]:
                unit=inp("Unit — hours (h) or minutes (m)","h").lower()
                if unit in("h","hours"):
                    v=inp("Every X hours",cfg["restart_seconds"]//3600)
                    try:cfg["restart_seconds"]=max(1,int(float(v)*3600))
                    except:pass
                else:
                    v=inp("Every X minutes",cfg["restart_seconds"]//60)
                    try:cfg["restart_seconds"]=max(1,int(float(v)*60))
                    except:pass
        elif c=="7":
            v=inp("Watch disconnect flag? (y/n)","y" if cfg["watch_flag"] else "n").lower()
            cfg["watch_flag"]=v in("y","yes")
        elif c=="8":
            v=inp("Enable webhook? (y/n)","y" if cfg["webhook_enabled"] else "n").lower()
            cfg["webhook_enabled"]=v in("y","yes")
        elif c=="9":
            v=inp("Discord Webhook URL",cfg["webhook_url"] or "")
            if v:cfg["webhook_url"]=v
        elif c=="10":
            print(f"\n  Current: {wstr}")
            unit=inp("Unit — minutes (m) or hours (h)","m").lower()
            if unit in("h","hours"):
                v=inp("Every X hours",cfg["webhook_interval"]//3600)
                try:cfg["webhook_interval"]=max(10,int(float(v)*3600))
                except:pass
            else:
                v=inp("Every X minutes",max(1,cfg["webhook_interval"]//60))
                try:cfg["webhook_interval"]=max(10,int(float(v)*60))
                except:pass

    return cfg

# ══════════════════════════════════════════════════
# SCREENSHOT
# ══════════════════════════════════════════════════
SCREENSHOT_PATH="/sdcard/roblox_status.png"

def take_screenshot():
    try:
        subprocess.run(["screencap","-p",SCREENSHOT_PATH],timeout=10,capture_output=True)
        if os.path.exists(SCREENSHOT_PATH):return SCREENSHOT_PATH
    except:pass
    return None

# ══════════════════════════════════════════════════
# DISCORD WEBHOOK
# ══════════════════════════════════════════════════
def get_ram():
    try:return psutil.virtual_memory().percent
    except:return 0

def get_cpu():
    try:
        r=subprocess.run(["top","-bn1"],capture_output=True,text=True,timeout=5)
        for line in r.stdout.splitlines():
            if "cpu" in line.lower() or "Cpu" in line:
                import re
                m=re.search(r'(\d+\.?\d*)%?\s*(?:us|user)',line,re.IGNORECASE)
                if m:return float(m.group(1))
        # fallback: read /proc/stat manually
        with open("/proc/stat") as f:
            line=f.readline()
        vals=list(map(int,line.split()[1:]))
        idle=vals[3]
        total=sum(vals)
        return round((1-idle/total)*100,1)
    except:return 0

def send_webhook(cfg,ram,cpu,reason="status"):
    if not cfg.get("webhook_enabled") or not cfg.get("webhook_url"):return
    try:
        ts=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ram_bar="█"*int(ram//10)+"░"*(10-int(ram//10))
        cpu_bar="█"*int(cpu//10)+"░"*(10-int(cpu//10))
        ram_color=0xFF0000 if ram>=cfg["ram_limit"] else 0xFFAA00 if ram>=70 else 0x00FF88
        status="🔴 OVERLOADED" if ram>=cfg["ram_limit"] else "🟡 HIGH" if ram>=70 else "🟢 OK"

        embed={
            "embeds":[{
                "title":"🎮 Roblox Auto-Rejoin — Status Report",
                "color":ram_color,
                "fields":[
                    {"name":"📊 RAM Usage","value":f"`{ram_bar}` **{ram:.1f}%**","inline":True},
                    {"name":"⚡ CPU Usage","value":f"`{cpu_bar}` **{cpu:.1f}%**","inline":True},
                    {"name":"🏓 Status","value":status,"inline":True},
                    {"name":"🎯 Place ID","value":f"`{cfg['place_id']}`","inline":True},
                    {"name":"📋 Trigger","value":f"`{reason}`","inline":True},
                    {"name":"🕐 Time","value":f"`{ts}`","inline":True},
                ],
                "footer":{"text":"Roblox Auto-Rejoin Monitor v5.0"}
            }]
        }
        data=json.dumps(embed).encode("utf-8")
        req=urllib.request.Request(
            cfg["webhook_url"],data=data,
            headers={"Content-Type":"application/json"},method="POST"
        )
        urllib.request.urlopen(req,timeout=10)
        log("Webhook sent ✓","WEBHOOK")

        # Send screenshot if available
        shot=take_screenshot()
        if shot and os.path.exists(shot):
            import mimetypes
            boundary="----WebKitFormBoundary"
            with open(shot,"rb") as f:img=f.read()
            body=(
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="status.png"\r\n'
                f"Content-Type: image/png\r\n\r\n"
            ).encode()+img+f"\r\n--{boundary}--\r\n".encode()
            req2=urllib.request.Request(
                cfg["webhook_url"],data=body,
                headers={"Content-Type":f"multipart/form-data; boundary={boundary}"},
                method="POST"
            )
            urllib.request.urlopen(req2,timeout=15)
            log("Screenshot sent ✓","WEBHOOK")
    except Exception as e:
        log(f"Webhook error: {e}","WARN")

def webhook_loop(cfg,stop_event):
    while not stop_event.is_set():
        time.sleep(cfg["webhook_interval"])
        if stop_event.is_set():break
        ram=get_ram();cpu=get_cpu()
        send_webhook(cfg,ram,cpu,"scheduled")

# ══════════════════════════════════════════════════
# ROBLOX CONTROL
# ══════════════════════════════════════════════════
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
    log("Killing all Roblox instances...","KILL")
    for proc in psutil.process_iter(["name","cmdline","pid"]):
        try:
            n=(proc.info["name"]or"").lower()
            c=" ".join(proc.info["cmdline"]or[]).lower()
            if "roblox" in n or ROBLOX_PKG in c:os.kill(proc.pid,signal.SIGKILL)
        except:pass
    try:subprocess.run(["am","force-stop",ROBLOX_PKG],timeout=5,capture_output=True)
    except:pass
    time.sleep(2)

def launch(place_id):
    log(f"Launching {cl(place_id,'93')}","ACTION")
    try:
        r=subprocess.run([
            "am","start","-n",f"{ROBLOX_PKG}/com.roblox.client.ActivityProtocolLaunch",
            "-a","android.intent.action.VIEW",
            "-d",f"roblox://placeId={place_id}&launchData=rejoin"
        ],capture_output=True,text=True,timeout=10)
        if r.returncode==0:log(cl("Launched ✓","92"),"OK");return True
    except:pass
    try:
        r=subprocess.run([
            "am","start","-a","android.intent.action.VIEW",
            "-d",f"roblox://placeId={place_id}","-p",ROBLOX_PKG
        ],capture_output=True,text=True,timeout=10)
        if r.returncode==0:log(cl("Launched via deep link ✓","92"),"OK");return True
    except:pass
    try:
        subprocess.run(["termux-open-url",f"roblox://placeId={place_id}"],capture_output=True,timeout=10)
        log(cl("Launched via termux-open-url ✓","92"),"OK");return True
    except:pass
    log(cl("All launch methods failed!","91"),"ERROR");return False

def rejoin(cfg,reason,fresh=False,delay=0):
    log(f"{cl('REJOIN','1;95')} — {cl(reason,'93')}","ACTION")
    ram=get_ram();cpu=get_cpu()
    send_webhook(cfg,ram,cpu,f"rejoin:{reason}")
    if fresh:kill_roblox();time.sleep(3)
    clear_flags()
    if delay>0:
        log(f"Waiting {cl(seconds_to_str(delay),'93')} before rejoining...","ACTION")
        time.sleep(delay)
    launch(cfg["place_id"])
    log(f"Cooling down {cl(seconds_to_str(cfg['rejoin_cooldown']),'93')}...","ACTION")
    time.sleep(cfg["rejoin_cooldown"])

# ══════════════════════════════════════════════════
# MAIN MONITOR LOOP
# ══════════════════════════════════════════════════
def monitor(cfg):
    print()
    print(cl("╔════════════════════════════════════════════════════╗","92"))
    print(cl("║  Monitor ACTIVE — Ctrl+C to stop                   ║","92"))
    print(cl("╚════════════════════════════════════════════════════╝","92"))
    print()

    clear_flags()
    log("Initial launch...","ACTION")
    launch(cfg["place_id"])

    # Start webhook thread
    stop_event=threading.Event()
    if cfg.get("webhook_enabled") and cfg.get("webhook_url"):
        wt=threading.Thread(target=webhook_loop,args=(cfg,stop_event),daemon=True)
        wt.start()
        log(f"Webhook thread started — reporting every {cl(seconds_to_str(cfg['webhook_interval']),'93')}","WEBHOOK")
        # send initial status
        time.sleep(2)
        send_webhook(cfg,get_ram(),get_cpu(),"monitor_started")

    time.sleep(cfg["rejoin_cooldown"])

    crashes=0
    start_time=time.time()
    next_restart=start_time+cfg["restart_seconds"] if cfg["auto_restart"] else None

    try:
        while True:
            now=time.time()

            # ── Auto restart ──────────────────────────────
            if next_restart and now>=next_restart:
                log(f"Auto restart after {cl(seconds_to_str(now-start_time),'93')}","TIMER")
                rejoin(cfg,"auto_restart",fresh=True)
                next_restart=time.time()+cfg["restart_seconds"]
                crashes=0;continue

            ram=get_ram();cpu=get_cpu()
            if next_restart:
                remaining=int(next_restart-now)
                log(f"RAM:{cl(f'{ram:.1f}%','94')} CPU:{cl(f'{cpu:.1f}%','94')}  │  Restart in:{cl(seconds_to_str(remaining),'96')}","TIMER")
            else:
                log(f"RAM:{cl(f'{ram:.1f}%','94')}  CPU:{cl(f'{cpu:.1f}%','94')}","RAM")

            # ── RAM overload ──────────────────────────────
            if ram>=cfg["ram_limit"]:
                log(f"RAM overload! {cl(f'{ram:.1f}%','91')}","RAM")
                rejoin(cfg,f"ram({ram:.0f}%)",fresh=True)
                crashes=0
                if next_restart:next_restart=time.time()+cfg["restart_seconds"]
                continue

            # ── Disconnect flag ───────────────────────────
            if cfg["watch_flag"]:
                found,reason,_=check_flag()
                if found:
                    log(f"Disconnect flag! {cl(reason,'93')}","FLAG")
                    rejoin(cfg,f"flag:{reason}",fresh=False)
                    crashes=0;continue

            # ── Crash detection ───────────────────────────
            if not is_running():
                crashes+=1
                log(f"Roblox not running ({cl(str(crashes),'93')}/{cl(str(cfg['crash_confirm']),'93')})","WARN")
                if crashes>=cfg["crash_confirm"]:
                    log(f"Crash confirmed! Rejoining in {cl(seconds_to_str(cfg['crash_delay']),'93')}...","WARN")
                    rejoin(cfg,"crash",fresh=True,delay=cfg["crash_delay"])
                    crashes=0
                    if next_restart:next_restart=time.time()+cfg["restart_seconds"]
            else:
                if crashes>0:log(cl("Roblox running ✓","92"),"OK")
                crashes=0

            time.sleep(cfg["check_interval"])

    except KeyboardInterrupt:
        print()
        log(cl("Stopped.","93"),"WARN")
        stop_event.set()

# ══════════════════════════════════════════════════
# ENTRY
# ══════════════════════════════════════════════════
if __name__=="__main__":
    banner()
    games=load_games()
    cfg=load_config()

    if not games:
        print(cl("  No saved games — let's add your first game!","93"))
        time.sleep(1)
        games=game_manager(games)

    place_id,games=pick_game(games,cfg)
    cfg["place_id"]=place_id
    cfg=settings_menu(cfg)
    monitor(cfg)
