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
{cl('║','96')}  {cl('Roblox Auto-Rejoin','1;97')} {cl('🎮','0')}  {cl('v5.1','2')}                      {cl('║','96')}
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
                return {**DEFAULT_CFG,**saved}
    except:pass
    return dict(DEFAULT_CFG)

def save_config(cfg):
    try:
        with open(CONFIG_FILE,"w") as f:json.dump(cfg,f,indent=2)
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
# SETTINGS MENU
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
        wshow=(wurl[:35]+"...") if len(wurl)>35 else wurl if wurl else cl("Not set","91")

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

        c=inp("Edit number or S to start").strip().upper()
        if c=="S":
            save_config(cfg)
            print(cl("\n  ✓ Config saved!","92"));time.sleep(0.5);break
        elif c=="R":
            cfg={**DEFAULT_CFG,"place_id":cfg["place_id"]}
            print(cl("  ✓ Reset","92"));time.sleep(0.5)
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
            if v:cfg["webhook_url"]=v.strip()
        elif c=="10":
            unit=inp("Unit — minutes (m) or hours (h)","m").lower()
            if unit in("h","hours"):
                v=inp("Every X hours",max(1,cfg["webhook_interval"]//3600))
                try:cfg["webhook_interval"]=max(10,int(float(v)*3600))
                except:pass
            else:
                v=inp("Every X minutes",max(1,cfg["webhook_interval"]//60))
                try:cfg["webhook_interval"]=max(10,int(float(v)*60))
                except:pass
    return cfg

# ══════════════════════════════════════════════════
# CPU — rooted Android (su top) with psutil fallback
# ══════════════════════════════════════════════════
_cpu_value=0.0
_cpu_lock=threading.Lock()

def _sample_cpu_once():
    """Try su top first (root), then psutil blocking."""
    import re
    # Method 1: su top — most reliable on rooted Android
    try:
        r=subprocess.run(
            ["su","-c","top -bn1"],
            capture_output=True,text=True,timeout=6
        )
        for line in r.stdout.splitlines():
            # Android top: "%cpu" line like "800%cpu 123%user 0%nice 456%sys 321%idle"
            m=re.search(r'(\d+)%idle',line,re.I)
            if m:
                total_str=re.search(r'(\d+)%cpu',line,re.I)
                if total_str:
                    total=float(total_str.group(1))
                    idle=float(m.group(1))
                    if total>0:
                        return round((total-idle)/total*100,1)
            # Fallback pattern: "Cpu(s): X.X us"
            m2=re.search(r'(\d+\.?\d*)\s*%?\s*us',line,re.I)
            if m2:
                return round(float(m2.group(1)),1)
    except:pass

    # Method 2: su cat /proc/stat delta (root, 1s window)
    try:
        def read_stat_root():
            r=subprocess.run(["su","-c","cat /proc/stat"],capture_output=True,text=True,timeout=3)
            line=r.stdout.splitlines()[0]
            vals=list(map(int,line.split()[1:8]))
            idle=vals[3]+vals[4]
            return idle,sum(vals)
        i1,t1=read_stat_root()
        time.sleep(1.0)
        i2,t2=read_stat_root()
        dt=t2-t1
        if dt>0:return round((1-(i2-i1)/dt)*100,1)
    except:pass

    # Method 3: psutil blocking (last resort)
    try:
        return round(psutil.cpu_percent(interval=1.0),1)
    except:pass
    return 0.0

def _cpu_sampler():
    global _cpu_value
    while True:
        try:
            v=_sample_cpu_once()
            with _cpu_lock:
                _cpu_value=v
        except:pass
        time.sleep(3)

def _warmup_cpu():
    """Prime psutil cpu_percent (first call always returns 0), then start sampler."""
    global _cpu_value
    # psutil.cpu_percent needs a throwaway first call to establish a baseline;
    # without this the first real sample returns 0.0
    try:psutil.cpu_percent(interval=None)
    except:pass
    t=threading.Thread(target=_cpu_sampler,daemon=True)
    t.start()
    # Wait up to 10s for first real reading (su top can take ~6s on some devices)
    for _ in range(20):
        time.sleep(0.5)
        with _cpu_lock:
            if _cpu_value>0.0:
                return
    # If still 0 after 10s (no root, psutil failed), force one blocking read now
    try:
        v=round(psutil.cpu_percent(interval=1.5),1)
        if v>0.0:
            with _cpu_lock:
                _cpu_value=v
    except:pass

def get_cpu():
    with _cpu_lock:
        return _cpu_value

def get_ram():
    try:return psutil.virtual_memory().percent
    except:return 0.0

# ══════════════════════════════════════════════════
# SCREENSHOT
# ══════════════════════════════════════════════════
SCREENSHOT_PATH="/sdcard/roblox_status.png"

def take_screenshot():
    try:
        # With root — works even when screen is off
        r=subprocess.run(
            ["su","-c",f"screencap -p {SCREENSHOT_PATH}"],
            timeout=10,capture_output=True
        )
        if os.path.exists(SCREENSHOT_PATH) and os.path.getsize(SCREENSHOT_PATH)>0:
            return SCREENSHOT_PATH
    except:pass
    # Fallback without root
    try:
        subprocess.run(["screencap","-p",SCREENSHOT_PATH],timeout=10,capture_output=True)
        if os.path.exists(SCREENSHOT_PATH) and os.path.getsize(SCREENSHOT_PATH)>0:
            return SCREENSHOT_PATH
    except:pass
    return None

# ══════════════════════════════════════════════════
# SMALL CAPS + GAME INFO + PROCESS STATS
# ══════════════════════════════════════════════════
_SMALL_CAPS="aᴀbʙcᴄdᴅeᴇfꜰgɢhʜiɪjᴊkᴋlʟmᴍnɴoᴏpᴘqǫrʀsꜱtᴛuᴜvᴠwᴡxхyʏzᴢ"
def to_small_caps(text):
    result=""
    for ch in text:
        if ch.islower():
            idx=ord(ch)-ord('a')
            result+=_SMALL_CAPS[idx*2+1]
        elif ch.isupper():
            idx=ord(ch)-ord('A')
            result+=_SMALL_CAPS[idx*2+1]
        else:
            result+=ch
    return result

_game_name_cache={}
def get_game_name(place_id):
    if place_id in _game_name_cache:
        return _game_name_cache[place_id]
    try:
        req=urllib.request.Request(
            f"https://games.roblox.com/v1/games?universeIds=",
            headers={"User-Agent":"RobloxRejoin/5.1"}
        )
        # First get universe ID from place ID
        req=urllib.request.Request(
            f"https://apis.roblox.com/universes/v1/places/{place_id}/universe",
            headers={"User-Agent":"RobloxRejoin/5.1"}
        )
        with urllib.request.urlopen(req,timeout=5) as r:
            uid=json.loads(r.read())["universeId"]
        # Then get game name
        req2=urllib.request.Request(
            f"https://games.roblox.com/v1/games?universeIds={uid}",
            headers={"User-Agent":"RobloxRejoin/5.1"}
        )
        with urllib.request.urlopen(req2,timeout=5) as r2:
            name=json.loads(r2.read())["data"][0]["name"]
            _game_name_cache[place_id]=name
            return name
    except:pass
    return None

# CPU tracking for Roblox process: store previous /proc/pid/stat values for delta
_rblx_pid_cache=None
_rblx_prev_stat=None  # (utime+stime, wall_time) from last reading

def _get_rblx_pid():
    """Get PID of Roblox via su pidof (works on rooted Android)."""
    try:
        r=subprocess.run(["su","-c",f"pidof {ROBLOX_PKG}"],
                         capture_output=True,text=True,timeout=3)
        pid=r.stdout.strip().split()[0]
        return int(pid)
    except:pass
    # fallback: psutil (works if termux has access)
    try:
        for proc in psutil.process_iter(["name","cmdline","pid"]):
            try:
                n=(proc.info["name"]or"").lower()
                c=" ".join(proc.info["cmdline"]or[]).lower()
                if "roblox" in n or ROBLOX_PKG in c:
                    return proc.pid
            except:pass
    except:pass
    return None

def _read_proc_stat(pid):
    """Read utime+stime (in clock ticks) from /proc/pid/stat via su."""
    try:
        r=subprocess.run(["su","-c",f"cat /proc/{pid}/stat"],
                         capture_output=True,text=True,timeout=3)
        fields=r.stdout.split()
        utime=int(fields[13]);stime=int(fields[14])
        return utime+stime
    except:return None

def _read_proc_ram(pid):
    """Read RSS in MB from /proc/pid/status via su."""
    try:
        import re
        r=subprocess.run(["su","-c",f"cat /proc/{pid}/status"],
                         capture_output=True,text=True,timeout=3)
        m=re.search(r'VmRSS:\s*(\d+)',r.stdout)
        return int(m.group(1))//1024 if m else 0
    except:return 0

def get_roblox_process_stats():
    """Return (ram_mb, cpu_pct, pid) for the Roblox process, or (0, 0.0, None)."""
    global _rblx_pid_cache,_rblx_prev_stat
    import re

    # verify cached pid is still alive
    if _rblx_pid_cache is not None:
        try:
            r=subprocess.run(["su","-c",f"kill -0 {_rblx_pid_cache}"],
                             capture_output=True,timeout=2)
            if r.returncode!=0:
                _rblx_pid_cache=None;_rblx_prev_stat=None
        except:
            _rblx_pid_cache=None;_rblx_prev_stat=None

    # find pid if not cached
    if _rblx_pid_cache is None:
        pid=_get_rblx_pid()
        if pid is None:
            _rblx_prev_stat=None
            return 0,0.0,None
        _rblx_pid_cache=pid
        # prime: store first stat reading, return 0 cpu this tick
        ticks=_read_proc_stat(pid)
        _rblx_prev_stat=(ticks,time.time()) if ticks is not None else None
        ram_mb=_read_proc_ram(pid)
        return ram_mb,0.0,pid

    pid=_rblx_pid_cache
    ram_mb=_read_proc_ram(pid)

    # CPU delta from /proc/pid/stat
    cpu=0.0
    ticks=_read_proc_stat(pid)
    if ticks is not None and _rblx_prev_stat is not None:
        prev_ticks,prev_time=_rblx_prev_stat
        elapsed=time.time()-prev_time
        clk_tck=os.sysconf('SC_CLK_TCK') if hasattr(os,'sysconf') else 100
        delta_ticks=ticks-prev_ticks
        if elapsed>0:
            cpu=round((delta_ticks/clk_tck)/elapsed*100,1)
    if ticks is not None:
        _rblx_prev_stat=(ticks,time.time())

    return ram_mb,cpu,pid

# ══════════════════════════════════════════════════
# DISCORD WEBHOOK — embed + screenshot in one request
# ══════════════════════════════════════════════════
def send_webhook(cfg,ram,cpu,reason="status",uptime_secs=0):
    if not cfg.get("webhook_enabled") or not cfg.get("webhook_url"):return
    url=cfg["webhook_url"].strip()
    if not url.startswith("https://discord.com/api/webhooks/"):
        log(cl("Webhook URL invalid — must start with https://discord.com/api/webhooks/","91"),"WARN")
        return
    try:
        import uuid
        ts=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ram_free=get_ram_free_mb()
        device=get_device_model()

        # Take screenshot first so we can attach it to the embed image
        shot=take_screenshot()
        has_shot=shot and os.path.exists(shot) and os.path.getsize(shot)>0

        # Roblox process stats — check running state BEFORE setting status dot
        rblx_ram,rblx_cpu,rblx_pid=get_roblox_process_stats()
        rblx_running=rblx_pid is not None

        if not rblx_running:
            status_dot="🔴";status_txt="OFFLINE"
            embed_color=0xFF4444
        elif ram>=cfg["ram_limit"]:
            status_dot="🔴";status_txt="OVERLOADED"
            embed_color=0xFF4444
        elif ram>=70:
            status_dot="🟡";status_txt="HIGH RAM"
            embed_color=0xFFAA00
        else:
            status_dot="🟢";status_txt="Online"
            embed_color=0x57F287

        # Game name (small caps)
        raw_name=get_game_name(cfg["place_id"])
        game_sc=to_small_caps(raw_name) if raw_name else to_small_caps("roblox")
        proc_dot="🟢" if rblx_running else "🔴"

        pkg_sc=to_small_caps(ROBLOX_PKG)

        desc_lines=[
            f"**Last Updated:** {ts}",
            "",
            "**Device Information:**",
            f"📱 **|** Device: `{device}`",
            f"⚙️ **|** CPU: `{cpu:.1f}%`",
            f"💾 **|** RAM: `{ram_free} MB free` ({ram:.1f}% used)",
            "",
            "**Instance Status:**",
            f"{status_dot} **|** Status: **{status_txt}**",
            "",
            "**Application Details**",
            f"{proc_dot} {pkg_sc} · {game_sc}",
            f"└ ⏱ `{seconds_to_str(uptime_secs)}`  **|**  💾 `{rblx_ram} MB`  **|**  ⚡ `{rblx_cpu:.1f}%`",
            "",
            "**Session Details**",
            f"🎯 **|** Place ID: `{cfg['place_id']}`",
            f"⏱️ **|** Uptime: `{seconds_to_str(uptime_secs)}`",
            f"🕐 **|** Time: `{ts}`",
        ]
        description="\n".join(desc_lines)

        embed_obj={
            "title":"📊 0x Rejoin Update",
            "description":description,
            "color":embed_color,
            "footer":{"text":"Roblox Auto-Rejoin v5.1"}
        }
        # Attach screenshot inline to the embed if available
        if has_shot:
            embed_obj["image"]={"url":"attachment://screen.png"}

        payload={"embeds":[embed_obj]}

        boundary="boundary"+uuid.uuid4().hex
        CRLF=b"\r\n"

        def field(name,data,filename=None,ctype="application/octet-stream"):
            if filename:
                hdr=(
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
                    f"Content-Type: {ctype}\r\n\r\n"
                ).encode()
            else:
                hdr=(
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                ).encode()
            return hdr+data+CRLF

        body=b""
        body+=field("payload_json",json.dumps(payload).encode("utf-8"))
        if has_shot:
            with open(shot,"rb") as f:img_data=f.read()
            body+=field("files[0]",img_data,filename="screen.png",ctype="image/png")
        body+=f"--{boundary}--\r\n".encode()

        req=urllib.request.Request(
            url,data=body,
            headers={
                "Content-Type":f"multipart/form-data; boundary={boundary}",
                "User-Agent":"RobloxRejoin/5.1"
            },
            method="POST"
        )
        with urllib.request.urlopen(req,timeout=20) as resp:
            if resp.status in(200,204):
                log("Webhook sent ✓"+("+screenshot" if has_shot else ""),"WEBHOOK")
            else:
                log(f"Webhook failed: {resp.status}","WARN")

    except urllib.error.HTTPError as e:
        body=e.read().decode("utf-8","ignore")
        log(f"Webhook HTTP {e.code}: {body[:100]}","WARN")
    except Exception as e:
        log(f"Webhook error: {e}","WARN")

def webhook_loop(cfg,stop_event,start_time_ref):
    while not stop_event.is_set():
        time.sleep(cfg["webhook_interval"])
        if stop_event.is_set():break
        uptime=int(time.time()-start_time_ref[0])
        send_webhook(cfg,get_ram(),get_cpu(),"scheduled",uptime_secs=uptime)

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
    try:
        r=subprocess.run([
            "am","start","-n",f"{ROBLOX_PKG}/com.roblox.client.ActivityProtocolLaunch",
            "-a","android.intent.action.VIEW",
            "-d",f"roblox://placeId={place_id}&launchData=rejoin"
        ],capture_output=True,text=True,timeout=10)
        if r.returncode==0:return True
    except:pass
    try:
        r=subprocess.run([
            "am","start","-a","android.intent.action.VIEW",
            "-d",f"roblox://placeId={place_id}","-p",ROBLOX_PKG
        ],capture_output=True,text=True,timeout=10)
        if r.returncode==0:return True
    except:pass
    try:
        subprocess.run(["termux-open-url",f"roblox://placeId={place_id}"],capture_output=True,timeout=10)
        return True
    except:pass
    return False

def rejoin(cfg,reason,fresh=False,delay=0,uptime_secs=0):
    send_webhook(cfg,get_ram(),get_cpu(),f"rejoin:{reason}",uptime_secs=uptime_secs)
    if fresh:kill_roblox();time.sleep(3)
    clear_flags()
    if delay>0:time.sleep(delay)
    launch(cfg["place_id"])
    time.sleep(cfg["rejoin_cooldown"])

# ══════════════════════════════════════════════════
# MAIN MONITOR LOOP
# ══════════════════════════════════════════════════
def get_device_model():
    """Return Android device model string."""
    try:
        r=subprocess.run(["getprop","ro.product.model"],capture_output=True,text=True,timeout=3)
        m=r.stdout.strip()
        if m:return m
    except:pass
    try:
        r=subprocess.run(["getprop","ro.product.name"],capture_output=True,text=True,timeout=3)
        m=r.stdout.strip()
        if m:return m
    except:pass
    return "Unknown"

def get_ram_free_mb():
    """Return free RAM in MB."""
    try:
        vm=psutil.virtual_memory()
        return int(vm.available//(1024*1024))
    except:return 0

_last_event=""  # tracks last action for dashboard

def draw_dashboard(cfg,ram,cpu,uptime,crashes,next_restart,rblx_ram,rblx_cpu,rblx_running,game_name):
    os.system("clear")
    now_str=datetime.now().strftime("%H:%M:%S")
    W=48  # card width

    def row(left,right="",sep="│"):
        # pad content to fit card
        inner=f"  {left}"
        if right:inner=inner.ljust(W-len(right)-3)+right
        return cl(f"│","96")+inner.ljust(W)+cl("│","96")

    def divider(ch="─"):
        return cl("├"+"─"*W+"┤","96")

    # status
    if ram>=cfg["ram_limit"]:
        sdot=cl("●","91");stxt=cl("OVERLOADED","91")
    elif not rblx_running:
        sdot=cl("●","91");stxt=cl("OFFLINE","91")
    elif crashes>0:
        sdot=cl("●","93");stxt=cl(f"CHECKING ({crashes}/{cfg['crash_confirm']})","93")
    else:
        sdot=cl("●","92");stxt=cl("INGAME","92")

    restart_str=""
    if next_restart:
        remaining=int(next_restart-time.time())
        if remaining>0:restart_str=f"restart {cl(seconds_to_str(remaining),'96')}"

    gname=game_name or "Roblox"

    lines=[]
    lines.append(cl("┌"+"─"*W+"┐","96"))
    lines.append(cl("│","96")+cl(f"  0x REJOIN  ·  v5.1".center(W),"1;97")+cl("│","96"))
    lines.append(cl("├"+"─"*W+"┤","96"))
    # device stats row
    cpu_col=cl(f"⚡ {cpu:.1f}%","93")
    ram_col=cl(f"💾 {ram:.1f}%","94")
    up_col =cl(f"⏱ {seconds_to_str(uptime)}","96")
    lines.append(cl("│","96")+f"  {cpu_col}    {ram_col}    {up_col}".ljust(W+24)+cl("│","96"))
    lines.append(cl("├"+"─"*W+"┤","96"))
    # instance header
    lines.append(cl("│","96")+cl(f"  #1  {ROBLOX_PKG}","97").ljust(W+4)+cl("│","96"))
    lines.append(cl("│","96")+f"  {sdot} {stxt}    {cl(gname,'93')}".ljust(W+20)+cl("│","96"))
    lines.append(cl("│","96")+cl(f"  RAM: {rblx_ram}MB  ·  CPU: {rblx_cpu:.1f}%","2").ljust(W+4)+cl("│","96"))
    lines.append(cl("├"+"─"*W+"┤","96"))
    # last event + time
    lines.append(cl("│","96")+cl(f"  {_last_event}","2").ljust(W+4)+cl("│","96"))
    lines.append(cl("│","96")+cl(f"  {now_str}","2").ljust(W+4)+(f"  {restart_str}  " if restart_str else "  ").ljust(0)+cl("│","96"))
    lines.append(cl("└"+"─"*W+"┘","96"))
    lines.append(cl("  Ctrl+C to stop","2"))

    print("\n".join(lines),flush=True)

def monitor(cfg):
    global _last_event
    os.system("clear")
    print(cl("\n  Starting 0x Rejoin...","96"),flush=True)

    # Seed CPU baseline
    _last_event="seeding cpu..."
    _warmup_cpu()

    clear_flags()
    _last_event="launching roblox"
    launch(cfg["place_id"])

    start_time=time.time()
    start_time_ref=[start_time]

    stop_event=threading.Event()
    if cfg.get("webhook_enabled") and cfg.get("webhook_url"):
        wt=threading.Thread(target=webhook_loop,args=(cfg,stop_event,start_time_ref),daemon=True)
        wt.start()
        _last_event="webhook started"
        # Give the CPU sampler a full cycle (sleep 3s + sample time) before
        # firing the startup webhook so cpu shows a real value, not 0.0
        time.sleep(5)
        send_webhook(cfg,get_ram(),get_cpu(),"monitor_started",uptime_secs=0)

    time.sleep(cfg["rejoin_cooldown"])

    crashes=0
    next_restart=start_time+cfg["restart_seconds"] if cfg["auto_restart"] else None
    game_name=get_game_name(cfg["place_id"])

    try:
        while True:
            now=time.time()
            uptime=int(now-start_time)
            ram=get_ram();cpu=get_cpu()
            rblx_ram,rblx_cpu,rblx_pid=get_roblox_process_stats()
            rblx_running=rblx_pid is not None

            draw_dashboard(cfg,ram,cpu,uptime,crashes,next_restart,rblx_ram,rblx_cpu,rblx_running,game_name)

            if next_restart and now>=next_restart:
                _last_event=f"auto restart triggered"
                rejoin(cfg,"auto_restart",fresh=True,uptime_secs=uptime)
                next_restart=time.time()+cfg["restart_seconds"]
                crashes=0;continue

            if ram>=cfg["ram_limit"]:
                _last_event=f"ram overload {ram:.1f}% — rejoining"
                rejoin(cfg,f"ram({ram:.0f}%)",fresh=True,uptime_secs=uptime)
                crashes=0
                if next_restart:next_restart=time.time()+cfg["restart_seconds"]
                continue

            if cfg["watch_flag"]:
                found,reason,_=check_flag()
                if found:
                    _last_event=f"flag: {reason} — rejoining"
                    rejoin(cfg,f"flag:{reason}",fresh=False,uptime_secs=uptime)
                    crashes=0;continue

            if not is_running():
                crashes+=1
                _last_event=f"roblox not running ({crashes}/{cfg['crash_confirm']})"
                if crashes>=cfg["crash_confirm"]:
                    _last_event=f"crash! rejoining in {seconds_to_str(cfg['crash_delay'])}..."
                    rejoin(cfg,"crash",fresh=True,delay=cfg["crash_delay"],uptime_secs=uptime)
                    crashes=0
                    if next_restart:next_restart=time.time()+cfg["restart_seconds"]
            else:
                if crashes>0:_last_event="roblox running ✓"
                crashes=0
                if _last_event.startswith("roblox not"):_last_event="monitoring..."

            time.sleep(cfg["check_interval"])

    except KeyboardInterrupt:
        os.system("clear")
        print(cl("\n  Stopped.\n","93"),flush=True)
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
