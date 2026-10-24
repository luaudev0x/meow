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
{cl('║','96')}  {cl('Roblox Auto-Rejoin','1;97')} {cl('🎮','0')}  {cl('v5.3','2')}                      {cl('║','96')}
{cl('║','96')}  {cl('Game Manager · Server Pick · Discord Webhook','2')}   {cl('║','96')}
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
    "server_mode":"off",      # off / highest / lowest
    "roblosecurity":"",       # .ROBLOSECURITY cookie value
    "packages":["com.roblox.client"],   # Roblox / clone packages to manage
    "launch_stagger":15,      # seconds between launching each instance
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
        print(cl("  ── Server Selection ──────────────────────────","96"))
        print()
        sm=cfg.get("server_mode","off")
        sm_col={"off":"91","highest":"92","lowest":"93"}.get(sm,"91")
        cookie=cfg.get("roblosecurity","")
        cshow=("set ✓" if cookie else cl("Not set","91"))
        print(f"  {cl('8','95')}. Server mode          {cl(sm.upper(),sm_col)}")
        print(f"  {cl('9','95')}. .ROBLOSECURITY        {cl(cshow,'92' if cookie else '91')}")
        print()
        print(cl("  ── Discord Webhook ───────────────────────────","96"))
        print()
        print(f"  {cl('10','95')}. Webhook enabled       {cl('On','92') if cfg['webhook_enabled'] else cl('Off','91')}")
        print(f"  {cl('11','95')}. Webhook URL           {cl(wshow,'96')}")
        print(f"  {cl('12','95')}. Webhook interval     {wstr}")
        print()
        print(cl("  ── Roblox Instances ──────────────────────────","96"))
        print()
        _pk=cfg.get("packages") or [ROBLOX_PKG]
        print(f"  {cl('13','95')}. Instances             {cl(str(len(_pk)),'93')}  {cl(', '.join(_pk)[:24],'2')}")
        print(f"  {cl('14','95')}. Launch gap            {cl(seconds_to_str(cfg.get('launch_stagger',15)),'93')}")
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
            cfg={**DEFAULT_CFG,"place_id":cfg["place_id"],"packages":cfg.get("packages") or [ROBLOX_PKG]}
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
            print(f"\n  {cl('1','92')}. Off (default matchmaking)")
            print(f"  {cl('2','92')}. Highest population")
            print(f"  {cl('3','92')}. Lowest population\n")
            sc=inp("Server mode (1/2/3)","1")
            cfg["server_mode"]={"1":"off","2":"highest","3":"lowest"}.get(sc,cfg.get("server_mode","off"))
            if cfg["server_mode"]!="off" and not cfg.get("roblosecurity",""):
                print(cl("  ⚠  .ROBLOSECURITY cookie required for server selection — set it in option 9","93"))
                time.sleep(2)
        elif c=="9":
            print(cl("  Paste your .ROBLOSECURITY cookie value (from browser cookies on roblox.com).","2"))
            print(cl("  Leave blank to keep current.\n","2"))
            v=inp(".ROBLOSECURITY","")
            if v:
                # strip the leading underscore-prefixed wrapper some browsers show
                v=v.strip()
                if v.startswith("_|"):v=v  # already raw
                cfg["roblosecurity"]=v
                print(cl("  ✓ Cookie saved","92"))
            time.sleep(0.8)
        elif c=="10":
            v=inp("Enable webhook? (y/n)","y" if cfg["webhook_enabled"] else "n").lower()
            cfg["webhook_enabled"]=v in("y","yes")
        elif c=="11":
            v=inp("Discord Webhook URL",cfg["webhook_url"] or "")
            if v:cfg["webhook_url"]=v.strip()
        elif c=="12":
            unit=inp("Unit — minutes (m) or hours (h)","m").lower()
            if unit in("h","hours"):
                v=inp("Every X hours",max(1,cfg["webhook_interval"]//3600))
                try:cfg["webhook_interval"]=max(10,int(float(v)*3600))
                except:pass
            else:
                v=inp("Every X minutes",max(1,cfg["webhook_interval"]//60))
                try:cfg["webhook_interval"]=max(10,int(float(v)*60))
                except:pass
        elif c=="13":
            cfg=instances_menu(cfg)
        elif c=="14":
            v=inp("Seconds between launching each instance",cfg.get("launch_stagger",15))
            try:cfg["launch_stagger"]=max(0,int(v))
            except:pass
    return cfg

# ══════════════════════════════════════════════════
# CPU — rooted Android (su top) with psutil fallback
# ══════════════════════════════════════════════════
_cpu_value=0.0
_cpu_lock=threading.Lock()

def _sample_cpu_once():
    """Try /proc/stat delta first (most reliable), then su top, then psutil."""
    import re

    # Method 1: /proc/stat delta — works without root on most Android (1s window)
    try:
        def _read_stat():
            for argv in (["su","-c","cat /proc/stat"],["cat","/proc/stat"]):
                try:
                    r=subprocess.run(argv,capture_output=True,text=True,timeout=3)
                    first=r.stdout.splitlines()[0] if r.stdout else ""
                    if first.startswith("cpu"):
                        vals=list(map(int,first.split()[1:8]))
                        idle=vals[3]+vals[4]
                        return idle,sum(vals)
                except:pass
            return None,None
        i1,t1=_read_stat()
        if t1 is not None:
            time.sleep(1.0)
            i2,t2=_read_stat()
            if t2 is not None:
                dt=t2-t1
                if dt>0:
                    return round((1-(i2-i1)/dt)*100,1)
    except:pass

    # Method 2: su top -bn1 — Android format "800%cpu 321%idle ..."
    try:
        r=subprocess.run(["su","-c","top -bn1"],capture_output=True,text=True,timeout=6)
        for line in r.stdout.splitlines():
            # Android busybox top: "400%cpu  12%user  0%nice 180%sys 208%idle"
            mc=re.search(r'(\d+(?:\.\d+)?)%cpu',line,re.I)
            mi=re.search(r'(\d+(?:\.\d+)?)%idle',line,re.I)
            if mc and mi:
                total=float(mc.group(1))
                idle=float(mi.group(1))
                if total>0:
                    return round((total-idle)/total*100,1)
            # Linux top: "Cpu(s): 12.3%us, 4.5%sy, ..."
            mu=re.search(r'(\d+\.?\d*)\s*%?\s*us',line,re.I)
            if mu:
                return round(float(mu.group(1)),1)
    except:pass

    # Method 3: psutil (last resort)
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
_universe_id_cache={}

def get_universe_id(place_id):
    """Return universeId for a place_id, cached. Returns None on failure."""
    if place_id in _universe_id_cache:
        return _universe_id_cache[place_id]
    try:
        req=urllib.request.Request(
            f"https://apis.roblox.com/universes/v1/places/{place_id}/universe",
            headers={"User-Agent":"RobloxRejoin/5.1"}
        )
        with urllib.request.urlopen(req,timeout=5) as r:
            uid=json.loads(r.read())["universeId"]
            _universe_id_cache[place_id]=uid
            return uid
    except:pass
    return None

def get_game_name(place_id):
    if place_id in _game_name_cache:
        return _game_name_cache[place_id]
    try:
        uid=get_universe_id(place_id)
        if uid is None:return None
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

def get_servers(place_id,cookie,mode="highest"):
    """
    Fetch public server list and return the access code of the
    highest- or lowest-populated server.
    Returns (access_code, player_count) or (None, None) on failure.

    Key fix: use sortOrder=Asc for lowest (empties first, so page 1
    already has the least-populated servers) and sortOrder=Desc for
    highest (fullest first). This means we only need ONE page fetch
    instead of paging through hundreds of servers.

    The .ROBLOSECURITY cookie is only used for this API lookup —
    it does NOT need to belong to the account that will actually join.
    One cookie shared across all instances is fine.
    """
    uid=get_universe_id(place_id)
    if uid is None:
        log("get_servers: could not resolve universe ID","WARN")
        return None,None
    if not cookie:
        log("get_servers: no .ROBLOSECURITY cookie set","WARN")
        return None,None

    # Sort order: Asc puts emptiest servers on page 1 (lowest mode),
    # Desc puts fullest servers on page 1 (highest mode).
    sort_order="Asc" if mode=="lowest" else "Desc"

    all_servers=[]
    cursor=""
    # With the correct sort order we only need 1-2 pages at most,
    # but fetch up to 2 pages (200 servers) as a safety buffer in
    # case the first page is all private/VIP servers with no accessCode.
    for page in range(2):
        url=(
            f"https://games.roblox.com/v1/games/{uid}/servers/Public"
            f"?limit=100&sortOrder={sort_order}"
            +(f"&cursor={urllib.parse.quote(cursor)}" if cursor else "")
        )
        try:
            req=urllib.request.Request(
                url,
                headers={
                    "User-Agent":"RobloxRejoin/5.2",
                    "Cookie":f".ROBLOSECURITY={cookie}",
                    "Accept":"application/json",
                }
            )
            with urllib.request.urlopen(req,timeout=10) as r:
                data=json.loads(r.read())
            servers=data.get("data",[])
            all_servers.extend(servers)

            # Filter usable from this page right away
            usable_so_far=[
                s for s in all_servers
                if s.get("accessCode") and s.get("playing") is not None
                and s.get("maxPlayers",0)>0
                and s["playing"]<s["maxPlayers"]
            ]
            # If we already have a good candidate on page 1, stop paging —
            # the sort order guarantees page 1 has the best match.
            if usable_so_far and page==0:
                all_servers=list(all_servers)  # keep what we have
                break

            cursor=data.get("nextPageCursor") or ""
            if not cursor:break
        except urllib.error.HTTPError as e:
            body=e.read().decode("utf-8","ignore")
            log(f"get_servers HTTP {e.code}: {body[:80]}","WARN")
            break
        except Exception as e:
            log(f"get_servers error: {e}","WARN")
            break

    # Final filter: must have accessCode, a player count, and not be full
    usable=[
        s for s in all_servers
        if s.get("accessCode") and s.get("playing") is not None
        and s.get("maxPlayers",0)>0
        and s["playing"]<s["maxPlayers"]
    ]
    if not usable:
        log(f"get_servers: no usable servers found (fetched {len(all_servers)}, mode={mode})","WARN")
        return None,None

    # Because sortOrder already puts the best match first on page 1,
    # pick accordingly from the filtered list.
    if mode=="highest":
        picked=max(usable,key=lambda s:s["playing"])
    else:  # lowest
        picked=min(usable,key=lambda s:s["playing"])

    code=picked["accessCode"]
    count=picked["playing"]
    total=picked["maxPlayers"]
    log(f"Server selected ({mode}): {count}/{total} players  code={code[:8]}...","OK")
    return code,count

# ══════════════════════════════════════════════════
# MULTI-INSTANCE: detection + per-package stats sampler
# ══════════════════════════════════════════════════
import re
_PKG_RE=re.compile(r'^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+$')

def _sh_out(cmd,timeout=25):
    for argv in (["su","-c",cmd],["sh","-c",cmd]):
        try:
            r=subprocess.run(argv,capture_output=True,text=True,timeout=timeout)
            if r.stdout.strip():return r.stdout
        except:pass
    return ""

def _natural_key(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)',s)]

def detect_roblox_packages():
    """Find Roblox and Roblox-clone packages. Uses several methods; needs root for the best ones."""
    found=[]
    def add(p):
        if _PKG_RE.match(p) and p not in found and not p.startswith("com.termux"):found.append(p)
    # 1) every app that handles roblox:// links
    for cmd in ('pm query-activities --brief -a android.intent.action.VIEW -d "roblox://placeId=1"',
                'cmd package query-activities --brief -a android.intent.action.VIEW -d "roblox://placeId=1"'):
        out=_sh_out(cmd)
        for m in re.finditer(r'([A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+)/[A-Za-z0-9_.$]+',out):add(m.group(1))
        if found:break
    # 2) package names that contain "roblox"
    out=_sh_out("pm list packages")
    for ln in out.splitlines():
        if ln.startswith("package:") and "roblox" in ln.lower():add(ln.split(":",1)[1].strip())
    # 3) third-party apps that contain the Roblox launch activity (finds renamed clones)
    scan=('for p in $(pm list packages -3 | cut -d: -f2); do '
          'dumpsys package $p 2>/dev/null | grep -q ActivityProtocolLaunch && echo "FOUND=$p"; done')
    for ln in _sh_out(scan,timeout=120).splitlines():
        if ln.startswith("FOUND="):add(ln[6:].strip())
    return sorted(found,key=_natural_key)

def scan_instances():
    print(cl("  Scanning installed apps (can take up to ~30s)...","2"),flush=True)
    return detect_roblox_packages()

def instances_menu(cfg):
    while True:
        banner()
        print(cl("  ── Roblox Instances ──────────────────────────","96"))
        pk=cfg.get("packages") or [ROBLOX_PKG]
        print()
        for i,p in enumerate(pk,1):print(f"  {cl(str(i),'95;1')}. {cl(p,'93')}")
        print()
        print(f"  {cl('A','92')}. Auto-detect instances")
        print(f"  {cl('M','96')}. Add package manually")
        print(f"  {cl('D','91')}. Remove one")
        print(f"  {cl('C','93')}. Reset to {ROBLOX_PKG} only")
        print(f"  {cl('0','96')}. Back")
        print()
        c=inp("Option").strip().upper()
        if c=="0":break
        elif c=="A":
            found=scan_instances()
            if not found:
                print(cl("  Nothing detected — use M to add package names by hand.","91"));time.sleep(2);continue
            print()
            for i,p in enumerate(found,1):print(f"  {cl(str(i),'95;1')}. {cl(p,'93')}")
            print()
            v=inp("Use which? (all / numbers like 1,2,5 / 0 = cancel)","all").lower().strip()
            if v in("0","cancel"):continue
            if v in("all","a",""):sel=list(found)
            else:
                sel=[]
                for t in v.replace(" ","").split(","):
                    try:
                        k=int(t)-1
                        if 0<=k<len(found) and found[k] not in sel:sel.append(found[k])
                    except:pass
            if sel:
                cfg["packages"]=sel
                print(cl(f"  ✓ {len(sel)} instance(s) selected","92"))
            time.sleep(1)
        elif c=="M":
            v=inp("Package name (e.g. free.nokaA)").strip()
            if _PKG_RE.match(v):
                cur=list(cfg.get("packages") or [])
                if v not in cur:cur.append(v)
                cfg["packages"]=cur
                print(cl(f"  ✓ added {v}","92"))
            else:print(cl("  Invalid package name","91"))
            time.sleep(1)
        elif c=="D":
            r=inp("Number to remove (0=cancel)","0")
            try:
                k=int(r)-1
                cur=list(cfg.get("packages") or [])
                if 0<=k<len(cur):
                    cur.pop(k);cfg["packages"]=cur or [ROBLOX_PKG]
            except:pass
        elif c=="C":
            cfg["packages"]=[ROBLOX_PKG]
    return cfg

# ── per-package CPU / RAM sampler (one background thread for ALL instances) ──
_inst_pkgs=[]
_inst_stats={}          # pkg -> (ram_mb, cpu_pct, pid)
_inst_state={}          # pkg -> last /proc reading, for CPU delta
_inst_lock=threading.Lock()
_inst_started=False
_proc_visible=False
INSTANCES=[]

def set_sampler_packages(pkgs):
    global _inst_pkgs
    with _inst_lock:
        _inst_pkgs=[p for p in pkgs if _PKG_RE.match(p)]

_LIST_CMD=('[ -r /proc/1/stat ] && echo VISIBLE=1; '
           'for pk in @@LIST@@; do p=$(pidof $pk | cut -d" " -f1); '
           '[ -n "$p" ] && { echo "PKG=$pk PID=$p"; cat /proc/$p/stat; grep VmRSS /proc/$p/status; }; done')

def _inst_sh(cmd,timeout=8):
    for argv in (["su","-c",cmd],["sh","-c",cmd]):
        try:
            r=subprocess.run(argv,capture_output=True,text=True,timeout=timeout)
            if "VISIBLE=" in r.stdout or "PKG=" in r.stdout:return r.stdout
        except:pass
    return ""

def _sample_instances():
    global _proc_visible
    with _inst_lock:pkgs=list(_inst_pkgs)
    if not pkgs:return {}
    out=_inst_sh(_LIST_CMD.replace("@@LIST@@"," ".join(pkgs)))
    _proc_visible="VISIBLE=" in out
    found={};cur=None
    for ln in out.splitlines():
        ln=ln.rstrip()
        if ln.startswith("PKG="):
            try:
                parts=ln.split()
                pk=parts[0][4:];pid=int(parts[1][4:])
                cur=found.setdefault(pk,{"pid":pid,"ticks":None,"start":None,"ram":0})
            except:cur=None
        elif cur is not None and ln.startswith(f"{cur['pid']} ("):
            try:
                rest=ln.rpartition(")")[2].split()
                cur["ticks"]=int(rest[11])+int(rest[12]);cur["start"]=rest[19]
            except:pass
        elif cur is not None and ln.startswith("VmRSS"):
            try:cur["ram"]=int(ln.split()[1])//1024
            except:pass
    now=time.time()
    try:clk=os.sysconf("SC_CLK_TCK")
    except:clk=100
    ncpu=os.cpu_count() or 1
    res={}
    for pk in pkgs:
        d=found.get(pk)
        if not d:
            _inst_state.pop(pk,None)
            res[pk]=(0,0.0,None);continue
        cpu=0.0
        st=_inst_state.get(pk)
        if d["ticks"] is not None:
            if st and st["pid"]==d["pid"] and st["start"]==d["start"] and st["t"]:
                el=now-st["t"]
                if el>0:cpu=max(0.0,min(100.0,round((d["ticks"]-st["ticks"])/clk/el*100/ncpu,1)))
            _inst_state[pk]={"pid":d["pid"],"start":d["start"],"ticks":d["ticks"],"t":now}
        res[pk]=(d["ram"],cpu,d["pid"])
    return res

def _inst_loop():
    global _inst_stats
    while True:
        try:
            v=_sample_instances()
            with _inst_lock:_inst_stats=v
        except:pass
        time.sleep(2)

def _ensure_sampler():
    global _inst_started,_inst_stats
    if _inst_started:return
    _inst_started=True
    try:
        v=_sample_instances()
        with _inst_lock:_inst_stats=v
    except:pass
    threading.Thread(target=_inst_loop,daemon=True).start()

def get_instance_stats(pkg):
    """(ram_mb, cpu_pct 0-100, pid) for one package, or (0, 0.0, None) when it isn't running."""
    _ensure_sampler()
    with _inst_lock:return _inst_stats.get(pkg,(0,0.0,None))

def get_running_set(pkgs):
    """Set of packages currently running, checked once for all instances."""
    _ensure_sampler()
    with _inst_lock:st=dict(_inst_stats)
    run={p for p in pkgs if st.get(p,(0,0.0,None))[2] is not None}
    if _proc_visible:return run          # we can see all processes: this is authoritative
    missing=[p for p in pkgs if p not in run]
    if missing:
        try:
            for proc in psutil.process_iter(["name"]):
                n=(proc.info["name"] or "")
                if n in missing:run.add(n)
        except:pass
        missing=[p for p in pkgs if p not in run]
    if missing:
        try:
            r=subprocess.run(["am","stack","list"],capture_output=True,text=True,timeout=5)
            for p in missing:
                if p in r.stdout:run.add(p)
        except:pass
    return run

def inst_status(inst,running):
    if inst["launch_at"] is not None:return "OFFLINE"
    if time.time()<inst["busy_until"]:return "LAUNCHING"
    if inst["pkg"] in running:return "INGAME"
    return "CHECKING" if inst["crashes"]>0 else "OFFLINE"

# ══════════════════════════════════════════════════
# DISCORD WEBHOOK — embed + screenshot in one request
# ══════════════════════════════════════════════════
_last_hook=0.0
_session_start=[time.time()]

def send_webhook(cfg,ram,cpu,reason="status",uptime_secs=0):
    global _last_hook
    if not cfg.get("webhook_enabled") or not cfg.get("webhook_url"):return
    url=cfg["webhook_url"].strip()
    if not url.startswith("https://discord.com/api/webhooks/"):
        log(cl("Webhook URL invalid — must start with https://discord.com/api/webhooks/","91"),"WARN")
        return
    try:
        import uuid
        _last_hook=time.time()
        ts=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ram_free=get_ram_free_mb()
        device=get_device_model()

        shot=take_screenshot()
        has_shot=shot and os.path.exists(shot) and os.path.getsize(shot)>0

        insts=list(INSTANCES)
        pkgs=[i["pkg"] for i in insts]
        running=get_running_set(pkgs) if pkgs else set()
        rows=[]
        for inst in insts:
            ram_mb,rcpu,_pid=get_instance_stats(inst["pkg"])
            rows.append((inst,inst_status(inst,running),ram_mb,rcpu))
        n_ing=sum(1 for r in rows if r[1]=="INGAME")
        n_off=sum(1 for r in rows if r[1]=="OFFLINE")
        n_wait=sum(1 for r in rows if r[1] in("LAUNCHING","CHECKING"))

        if n_off or ram>=cfg["ram_limit"]:embed_color=0xFF4444
        elif n_wait:embed_color=0xFFAA00
        else:embed_color=0x57F287

        raw_name=get_game_name(cfg["place_id"])
        game_name_str=(raw_name or "Roblox").upper()

        def pbar(pct,total=20):
            filled=int(round(pct/100*total))
            return "█"*filled+"░"*(total-filled)

        try:
            total_ram_mb=int(psutil.virtual_memory().total//(1024*1024))
            used_ram_mb=total_ram_mb-ram_free
        except:
            total_ram_mb=0;used_ram_mb=0

        dots={"INGAME":"🟢","LAUNCHING":"🟡","CHECKING":"🟡","OFFLINE":"🔴"}
        desc_lines=[
            f"**Last Updated:** {ts}",
            "",
            "**Device Information:**",
            f"📱 **|** Device: `{device}`",
            f"⚙️ **|** CPU: `{pbar(cpu)}` {cpu:.1f}% / 100%",
            f"💾 **|** RAM: `{pbar(ram)}` {used_ram_mb} MB / {total_ram_mb} MB",
            "",
            f"**Instances ({n_ing}/{len(rows)} ingame):**",
        ]
        now=time.time()
        for i,(inst,status,ram_mb,rcpu) in enumerate(rows,1):
            up=seconds_to_str(now-inst["start"]) if inst["start"] and status!="OFFLINE" else "-"
            desc_lines.append(f"{i}. {dots.get(status,'⚪')} **{inst['pkg']}** : {status.capitalize()}")
            desc_lines.append(f"└ ⏱ `{up}` **|** 💾 `{ram_mb} MB` **|** ⚡ `{rcpu:.1f}%`")
        desc_lines+=[
            "",
            "**Session Details**",
            f"🎯 **|** Game: `{game_name_str}`",
            f"🔢 **|** Place ID: `{cfg['place_id']}`",
            f"⏱️ **|** Uptime: `{seconds_to_str(uptime_secs)}`",
            f"🕐 **|** Time: `{ts}`",
        ]
        description="\n".join(desc_lines)[:4000]

        embed_obj={
            "title":"📊 0x Rejoin Update",
            "description":description,
            "color":embed_color,
            "footer":{"text":f"Roblox Auto-Rejoin v5.3 · {reason}"[:200]}
        }
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
                "User-Agent":"RobloxRejoin/5.3"
            },
            method="POST"
        )
        with urllib.request.urlopen(req,timeout=20) as resp:
            if resp.status in(200,204):
                log("Webhook sent ✓"+("+screenshot" if has_shot else ""),"WEBHOOK")
            else:
                log(f"Webhook failed: {resp.status}","WARN")
    except urllib.error.HTTPError as e:
        try:body_txt=e.read().decode("utf-8","ignore")
        except:body_txt=""
        log(f"Webhook HTTP {e.code}: {body_txt[:100]}","WARN")
    except Exception as e:
        log(f"Webhook error: {e}","WARN")

def fire_webhook(cfg,reason,min_gap=20):
    """Event webhook in a background thread (never blocks the monitor), rate-limited."""
    global _last_hook
    if not (cfg.get("webhook_enabled") and cfg.get("webhook_url")):return
    if time.time()-_last_hook<min_gap:return
    _last_hook=time.time()
    up=int(time.time()-_session_start[0])
    threading.Thread(target=send_webhook,args=(cfg,get_ram(),get_cpu(),reason,up),daemon=True).start()

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

def kill_roblox(pkg=ROBLOX_PKG):
    """Force-stop ONE Roblox package (other instances are left alone)."""
    try:
        for proc in psutil.process_iter(["name","pid"]):
            try:
                n=(proc.info["name"] or "")
                if n==pkg or n.startswith(pkg+":"):os.kill(proc.pid,signal.SIGKILL)
            except:pass
    except:pass
    for argv in (["am","force-stop",pkg],["su","-c",f"am force-stop {pkg}"]):
        try:subprocess.run(argv,timeout=8,capture_output=True)
        except:pass
    time.sleep(2)

def launch(place_id,access_code=None,pkg=ROBLOX_PKG):
    """
    Launch Roblox into place_id.
    If access_code is provided, uses the experiences/start deep-link to join
    a specific server; otherwise uses default matchmaking.
    """
    if access_code:
        # Specific-server join via accessCode
        url=(
            f"roblox://experiences/start"
            f"?accessCode={urllib.parse.quote(access_code)}"
            f"&launchData=rejoin"
        )
        try:
            r=subprocess.run([
                "am","start","-n",f"{pkg}/com.roblox.client.ActivityProtocolLaunch",
                "-a","android.intent.action.VIEW","-d",url
            ],capture_output=True,text=True,timeout=10)
            if r.returncode==0:return True
        except:pass
        try:
            r=subprocess.run([
                "am","start","-a","android.intent.action.VIEW","-d",url,"-p",pkg
            ],capture_output=True,text=True,timeout=10)
            if r.returncode==0:return True
        except:pass
        try:
            subprocess.run(["termux-open-url",url],capture_output=True,timeout=10)
            return True
        except:pass
        # If accessCode launch fails, fall through to default matchmaking below
        log("Access-code launch failed — falling back to default matchmaking","WARN")

    # Default matchmaking (no specific server)
    try:
        r=subprocess.run([
            "am","start","-n",f"{pkg}/com.roblox.client.ActivityProtocolLaunch",
            "-a","android.intent.action.VIEW",
            "-d",f"roblox://placeId={place_id}&launchData=rejoin"
        ],capture_output=True,text=True,timeout=10)
        if r.returncode==0:return True
    except:pass
    try:
        r=subprocess.run([
            "am","start","-a","android.intent.action.VIEW",
            "-d",f"roblox://placeId={place_id}","-p",pkg
        ],capture_output=True,text=True,timeout=10)
        if r.returncode==0:return True
    except:pass
    try:
        subprocess.run(["termux-open-url",f"roblox://placeId={place_id}"],capture_output=True,timeout=10)
        return True
    except:pass
    return False


def _do_launch(cfg,inst):
    global _last_event
    pk=inst["pkg"]
    access=None
    sm=cfg.get("server_mode","off")
    if sm in("highest","lowest"):
        cookie=cfg.get("roblosecurity","").strip()
        if cookie:
            _last_event=f"{pk[-16:]}: fetching {sm} server..."
            code,count=get_servers(cfg["place_id"],cookie,mode=sm)
            if code:access=code
        else:
            log("server_mode set but no .ROBLOSECURITY cookie — using matchmaking","WARN")
    ok=launch(cfg["place_id"],access_code=access,pkg=pk)
    now=time.time()
    inst["launch_at"]=None
    inst["start"]=now
    inst["crashes"]=0
    inst["busy_until"]=now+cfg["rejoin_cooldown"]
    inst["next_restart"]=now+cfg["restart_seconds"] if cfg.get("auto_restart") else None
    inst["hook_at"]=inst["busy_until"] if inst.get("reason") else None
    inst["reason"]=None
    _last_event=f"{pk[-16:]}: launched"+("" if ok else " (failed)")

def _begin_rejoin(cfg,inst,reason,fresh,delay):
    global _last_event
    pk=inst["pkg"]
    _last_event=f"{pk[-16:]}: {reason} — rejoining"
    fire_webhook(cfg,f"{reason}:{pk}")
    if fresh:kill_roblox(pk)
    inst["crashes"]=0
    inst["reason"]=reason
    inst["next_restart"]=None
    inst["launch_at"]=time.time()+max(0,delay)


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

def _bar(pct,w=12):
    filled=int(round(max(0,min(100,pct))/100*w))
    return "█"*filled+"░"*(w-filled)

def _cpu_color(p):
    if p>=80:return "91"
    if p>=50:return "93"
    return "92"

def _ram_color(p):
    if p>=85:return "91"
    if p>=65:return "93"
    return "96"

_dash_init=False
def draw_dashboard(cfg,ram,cpu,uptime,insts,running,game_name):
    global _dash_init
    now=time.time()
    now_str=datetime.now().strftime("%H:%M:%S")
    W=44

    rest=[i["next_restart"]-now for i in insts if i.get("next_restart")]
    restart_str=f"  ↺ restart in {seconds_to_str(min(rest))}" if rest and min(rest)>0 else ""
    gname=(game_name or "Roblox").upper()
    event=_last_event if _last_event else "monitoring..."
    sm=cfg.get("server_mode","off")
    sm_tag={"highest":" · FULL","lowest":" · EMPTY"}.get(sm,"")

    STATUS_DOT={"INGAME":cl("●","92"),"LAUNCHING":cl("◐","93"),"CHECKING":cl("◐","93"),"OFFLINE":cl("○","91")}
    STATUS_COL={"INGAME":"92","LAUNCHING":"93","CHECKING":"93","OFFLINE":"91"}

    lines=[]
    lines.append("")
    lines.append(cl(f"  0x REJOIN  v5.3  ·  {gname}{sm_tag}","1;97"))
    lines.append(cl("  "+"─"*W,"2"))
    lines.append(f"  {cl('CPU','2')} {cl(_bar(cpu),'0')}{cl(f' {cpu:5.1f}%',_cpu_color(cpu))}   "
                 f"{cl('RAM','2')} {cl(_bar(ram),'0')}{cl(f' {ram:5.1f}%',_ram_color(ram))}   "
                 f"{cl('⏱','2')} {cl(seconds_to_str(uptime),'97')}")
    lines.append(cl("  "+"─"*W,"2"))

    for n,inst in enumerate(insts,1):
        status=inst_status(inst,running)
        ram_mb,rcpu,_pid=get_instance_stats(inst["pkg"])
        up=seconds_to_str(now-inst["start"]) if inst["start"] and status!="OFFLINE" else "--"
        dot=STATUS_DOT.get(status,cl("○","2"))
        scol=STATUS_COL.get(status,"97")
        pkg_short=inst["pkg"][-20:]
        lines.append(f"  {dot} {cl(pkg_short,'97')}  {cl(status,scol)}")
        lines.append(f"    {cl('RAM','2')} {cl(f'{ram_mb}MB','97')}  "
                     f"{cl('CPU','2')} {cl(_bar(rcpu,8),'0')}{cl(f' {rcpu:.1f}%',_cpu_color(rcpu))}  "
                     f"{cl('UP','2')} {cl(up,'97')}")

    lines.append(cl("  "+"─"*W,"2"))
    lines.append(f"  {cl(now_str,'2')}  {cl(event[:W-12],'97')}")
    if restart_str:lines.append(cl(restart_str,"93"))
    lines.append(f"  {cl('ctrl+c to stop','2')}")
    lines.append("")

    if not _dash_init:
        print("\033[2J",end="",flush=True)
        _dash_init=True
    print("\033[H",end="",flush=True)
    for l in lines:
        print(f"\033[2K{l}")
    print("\033[J",end="",flush=True)

def monitor(cfg):
    global _last_event
    os.system("clear")
    print(cl("\n  Starting 0x Rejoin...","96"),flush=True)

    pkgs=[p for p in (cfg.get("packages") or [ROBLOX_PKG]) if _PKG_RE.match(p)] or [ROBLOX_PKG]
    set_sampler_packages(pkgs)

    _last_event="seeding cpu..."
    _warmup_cpu()

    single=len(pkgs)==1
    if single:clear_flags()

    start_time=time.time()
    _session_start[0]=start_time
    stagger=max(0,int(cfg.get("launch_stagger",15)))
    insts=[]
    for i,pk in enumerate(pkgs):
        insts.append({"pkg":pk,"launch_at":start_time+i*stagger,"busy_until":0,"crashes":0,
                      "start":None,"next_restart":None,"reason":None,"hook_at":None})
    INSTANCES[:]=insts
    _last_event=f"launching {len(pkgs)} instance(s)"

    start_time_ref=[start_time]
    stop_event=threading.Event()
    if cfg.get("webhook_enabled") and cfg.get("webhook_url"):
        threading.Thread(target=webhook_loop,args=(cfg,stop_event,start_time_ref),daemon=True).start()
    startup_hook_at=start_time+(len(pkgs)-1)*stagger+cfg["rejoin_cooldown"]+5

    game_name=get_game_name(cfg["place_id"])
    last_overload=0.0
    try:
        while True:
            now=time.time()
            uptime=int(now-start_time)
            ram=get_ram();cpu=get_cpu()
            running=get_running_set(pkgs)

            if single and cfg["watch_flag"]:
                found,reason,_=check_flag()
                if found and insts[0]["launch_at"] is None and now>=insts[0]["busy_until"]:
                    clear_flags()
                    _begin_rejoin(cfg,insts[0],f"flag:{reason}",False,0)

            for inst in insts:
                pk=inst["pkg"]
                if inst["launch_at"] is not None:
                    if now>=inst["launch_at"]:_do_launch(cfg,inst)
                    continue
                if inst.get("hook_at") and now>=inst["hook_at"]:
                    inst["hook_at"]=None
                    fire_webhook(cfg,f"rejoined:{pk}")
                if now<inst["busy_until"]:continue
                if inst["next_restart"] and now>=inst["next_restart"]:
                    _begin_rejoin(cfg,inst,"auto_restart",True,0);continue
                if pk not in running:
                    inst["crashes"]+=1
                    _last_event=f"{pk[-16:]}: not running ({inst['crashes']}/{cfg['crash_confirm']})"
                    if inst["crashes"]>=cfg["crash_confirm"]:
                        _begin_rejoin(cfg,inst,"crash",True,cfg["crash_delay"])
                else:
                    if inst["crashes"]>0:_last_event=f"{pk[-16:]}: running ✓"
                    inst["crashes"]=0

            # device RAM overload: restart only the heaviest instance, then wait before acting again
            if ram>=cfg["ram_limit"] and now-last_overload>=max(60,cfg["rejoin_cooldown"]*2):
                cands=[i for i in insts if i["launch_at"] is None and now>=i["busy_until"] and i["pkg"] in running]
                if cands:
                    worst=max(cands,key=lambda i:get_instance_stats(i["pkg"])[0])
                    _begin_rejoin(cfg,worst,f"ram({ram:.0f}%)",True,0)
                    last_overload=time.time()

            if startup_hook_at and now>=startup_hook_at:
                startup_hook_at=None
                fire_webhook(cfg,"monitor_started",min_gap=0)

            draw_dashboard(cfg,ram,cpu,uptime,insts,running,game_name)
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
