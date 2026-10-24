import os,sys,time,signal,subprocess,json,threading
from datetime import datetime

try:
    import psutil
except:
    subprocess.run([sys.executable,"-m","pip","install","psutil"],check=True)
    import psutil

try:
    import urllib.request,urllib.parse,urllib.error
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
    "auto_restart":False,
    "restart_seconds":7200,
    "watch_flag":True,
    "webhook_url":"",
    "webhook_interval":60,
    "webhook_enabled":False,
    "server_mode":"off",
    "roblosecurity":"",
}

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE) as f:
                saved=json.load(f)
            cfg={**DEFAULT_CFG,**saved}
            # fix stale test configs: if restart is under 5 min, reset to 2hr and disable
            if cfg.get("restart_seconds",7200)<300:
                cfg["restart_seconds"]=7200
                cfg["auto_restart"]=False
            return cfg
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
                v=v.strip()
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
    return cfg

# ══════════════════════════════════════════════════
# CPU — rooted Android (su top) with psutil fallback
# ══════════════════════════════════════════════════
_cpu_value=0.0
_cpu_lock=threading.Lock()

def _sample_cpu_once():
    import re
    try:
        r=subprocess.run(["su","-c","top -bn1"],capture_output=True,text=True,timeout=6)
        for line in r.stdout.splitlines():
            m=re.search(r'(\d+)%idle',line,re.I)
            if m:
                total_str=re.search(r'(\d+)%cpu',line,re.I)
                if total_str:
                    total=float(total_str.group(1));idle=float(m.group(1))
                    if total>0:return round((total-idle)/total*100,1)
            m2=re.search(r'(\d+\.?\d*)\s*%?\s*us',line,re.I)
            if m2:return round(float(m2.group(1)),1)
    except:pass
    try:
        def read_stat_root():
            r=subprocess.run(["su","-c","cat /proc/stat"],capture_output=True,text=True,timeout=3)
            line=r.stdout.splitlines()[0];vals=list(map(int,line.split()[1:8]))
            idle=vals[3]+vals[4];return idle,sum(vals)
        i1,t1=read_stat_root();time.sleep(1.0);i2,t2=read_stat_root();dt=t2-t1
        if dt>0:return round((1-(i2-i1)/dt)*100,1)
    except:pass
    try:return round(psutil.cpu_percent(interval=1.0),1)
    except:pass
    return 0.0

def _cpu_sampler():
    global _cpu_value
    while True:
        try:
            v=_sample_cpu_once()
            with _cpu_lock:_cpu_value=v
        except:pass
        time.sleep(3)

def _warmup_cpu():
    global _cpu_value
    try:psutil.cpu_percent(interval=None)
    except:pass
    t=threading.Thread(target=_cpu_sampler,daemon=True);t.start()
    for _ in range(20):
        time.sleep(0.5)
        with _cpu_lock:
            if _cpu_value>0.0:return
    try:
        v=round(psutil.cpu_percent(interval=1.5),1)
        if v>0.0:
            with _cpu_lock:_cpu_value=v
    except:pass

def get_cpu():
    with _cpu_lock:return _cpu_value

def get_ram():
    try:return psutil.virtual_memory().percent
    except:return 0.0

# ══════════════════════════════════════════════════
# SCREENSHOT
# ══════════════════════════════════════════════════
SCREENSHOT_PATH="/sdcard/roblox_status.png"

def take_screenshot():
    try:
        subprocess.run(["su","-c",f"screencap -p {SCREENSHOT_PATH}"],timeout=10,capture_output=True)
        if os.path.exists(SCREENSHOT_PATH) and os.path.getsize(SCREENSHOT_PATH)>0:return SCREENSHOT_PATH
    except:pass
    try:
        subprocess.run(["screencap","-p",SCREENSHOT_PATH],timeout=10,capture_output=True)
        if os.path.exists(SCREENSHOT_PATH) and os.path.getsize(SCREENSHOT_PATH)>0:return SCREENSHOT_PATH
    except:pass
    return None

# ══════════════════════════════════════════════════
# SMALL CAPS
# ══════════════════════════════════════════════════
_SMALL_CAPS="aᴀbʙcᴄdᴅeᴇfꜰgɢhʜiɪjᴊkᴋlʟmᴍnɴoᴏpᴘqǫrʀsꜱtᴛuᴜvᴠwᴡxхyʏzᴢ"
def to_small_caps(text):
    result=""
    for ch in text:
        if ch.islower():result+=_SMALL_CAPS[(ord(ch)-ord('a'))*2+1]
        elif ch.isupper():result+=_SMALL_CAPS[(ord(ch)-ord('A'))*2+1]
        else:result+=ch
    return result

_game_name_cache={}
_universe_id_cache={}

KNOWN_UNIVERSE_IDS={
    "107778070777162": 10563114921,
}

# ══════════════════════════════════════════════════
# CSRF TOKEN
# We try multiple Roblox endpoints to get a CSRF
# token since auth.roblox.com may be unreachable
# from Termux on some networks/devices.
# If ALL endpoints fail we proceed without a token
# — the server list API works without it when the
# right Referer/Origin headers are sent.
# ══════════════════════════════════════════════════
_csrf_token_cache=None
_csrf_token_lock=threading.Lock()

# Endpoints that return x-csrf-token in response headers on POST.
# We try them in order and stop at the first success.
_CSRF_ENDPOINTS=[
    "https://auth.roblox.com/v1/logout",
    "https://www.roblox.com/authentication/signoutfromallsessionsandreauthenticate",
    "https://economy.roblox.com/v1/user/currency",  # GET also works on some
]

def fetch_csrf_token(cookie):
    """
    Try several Roblox endpoints to obtain x-csrf-token.
    Each endpoint is tried with curl (headers in stdout via -D -)
    then urllib. Returns token string or None.
    """
    for url in _CSRF_ENDPOINTS:
        # curl: dump response headers to stdout with -D -
        try:
            cmd=[
                "curl","-s","--compressed","--max-time","8",
                "-A","Mozilla/5.0 RobloxRejoin/5.3",
                "-X","POST",
                "--cookie",f".ROBLOSECURITY={cookie}",
                "-H","Content-Length: 0",
                "-H","Origin: https://www.roblox.com",
                "-H","Referer: https://www.roblox.com/",
                "-D","-",  # headers → stdout
                "--output","/dev/null",  # discard body
                url
            ]
            r=subprocess.run(cmd,capture_output=True,text=True,timeout=10)
            for line in r.stdout.splitlines():
                if line.lower().startswith("x-csrf-token:"):
                    token=line.split(":",1)[1].strip()
                    if token:
                        log(f"CSRF token via curl ({url.split('/')[2]}): {token[:8]}...","OK")
                        return token
        except Exception as e:
            log(f"CSRF curl failed ({url.split('/')[2]}): {e}","WARN")

        # urllib fallback for same endpoint
        try:
            req=urllib.request.Request(
                url, data=b"",
                headers={
                    "User-Agent":"Mozilla/5.0 RobloxRejoin/5.3",
                    "Cookie":f".ROBLOSECURITY={cookie}",
                    "Content-Length":"0",
                    "Origin":"https://www.roblox.com",
                    "Referer":"https://www.roblox.com/",
                },
                method="POST"
            )
            try:
                urllib.request.urlopen(req,timeout=8)
            except urllib.error.HTTPError as e:
                token=e.headers.get("x-csrf-token","").strip()
                if token:
                    log(f"CSRF token via urllib ({url.split('/')[2]}): {token[:8]}...","OK")
                    return token
        except Exception as e:
            log(f"CSRF urllib failed ({url.split('/')[2]}): {e}","WARN")

    log("CSRF: all endpoints failed — will try server list without token","WARN")
    return None

def get_csrf_token(cookie, force_refresh=False):
    global _csrf_token_cache
    with _csrf_token_lock:
        if not force_refresh and _csrf_token_cache:
            return _csrf_token_cache
        token=fetch_csrf_token(cookie)
        if token:
            _csrf_token_cache=token
        return token

def invalidate_csrf_token():
    global _csrf_token_cache
    with _csrf_token_lock:
        _csrf_token_cache=None

# ══════════════════════════════════════════════════
# UNIVERSE ID HELPERS
# ══════════════════════════════════════════════════
def _fetch_universe_id_fresh(place_id):
    url=f"https://apis.roblox.com/universes/v1/places/{place_id}/universe"
    try:
        r=subprocess.run(
            ["curl","-s","--compressed","--max-time","8","-A","RobloxRejoin/5.3",url],
            capture_output=True,text=True,timeout=10
        )
        raw=r.stdout.strip()
        if raw:
            data=json.loads(raw)
            if not data.get("errors"):
                uid=data["universeId"]
                log(f"get_universe_id OK: universeId={uid}","OK")
                return uid
    except Exception as e:
        log(f"get_universe_id curl failed: {e}","WARN")
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"RobloxRejoin/5.3"})
        with urllib.request.urlopen(req,timeout=8) as r:
            uid=json.loads(r.read())["universeId"]
            log(f"get_universe_id urllib OK: universeId={uid}","OK")
            return uid
    except Exception as e:
        log(f"get_universe_id urllib failed: {e}","WARN")
    return None

def get_universe_id(place_id, force_refresh=False):
    if not force_refresh and place_id in KNOWN_UNIVERSE_IDS:
        return KNOWN_UNIVERSE_IDS[place_id]
    if not force_refresh and place_id in _universe_id_cache:
        return _universe_id_cache[place_id]
    uid=_fetch_universe_id_fresh(place_id)
    if uid is not None:
        _universe_id_cache[place_id]=uid
    return uid

def get_game_name(place_id):
    if place_id in _game_name_cache:
        return _game_name_cache[place_id]
    try:
        uid=get_universe_id(place_id)
        if uid is None:return None
        req=urllib.request.Request(
            f"https://games.roblox.com/v1/games?universeIds={uid}",
            headers={"User-Agent":"RobloxRejoin/5.3"}
        )
        with urllib.request.urlopen(req,timeout=5) as r:
            name=json.loads(r.read())["data"][0]["name"]
            _game_name_cache[place_id]=name
            return name
    except:pass
    return None

# ══════════════════════════════════════════════════
# HTTP HELPERS
# Build the full header set Roblox expects:
#   Cookie, x-csrf-token (if we have one),
#   Origin, Referer, Accept, User-Agent.
# Sending Origin+Referer often makes the server
# list API succeed even without a CSRF token.
# ══════════════════════════════════════════════════
_ROBLOX_HEADERS_BASE={
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 RobloxRejoin/5.3",
    "Accept":"application/json, text/plain, */*",
    "Accept-Language":"en-US,en;q=0.9",
    "Origin":"https://www.roblox.com",
    "Referer":"https://www.roblox.com/games/107778070777162/Steal-An-Egg",
}

def _build_curl_cmd(url, cookie, csrf_token, timeout):
    cmd=[
        "curl","-s","--compressed","--location",
        "--max-time",str(timeout),
        "-A",_ROBLOX_HEADERS_BASE["User-Agent"],
        "-H",f"Accept: {_ROBLOX_HEADERS_BASE['Accept']}",
        "-H",f"Accept-Language: {_ROBLOX_HEADERS_BASE['Accept-Language']}",
        "-H",f"Origin: {_ROBLOX_HEADERS_BASE['Origin']}",
        "-H",f"Referer: {_ROBLOX_HEADERS_BASE['Referer']}",
    ]
    if cookie:
        cmd+=["--cookie",f".ROBLOSECURITY={cookie}"]
    if csrf_token:
        cmd+=["-H",f"x-csrf-token: {csrf_token}"]
    cmd.append(url)
    return cmd

def _curl_get_json(url, cookie=None, csrf_token=None, timeout=12):
    cmd=_build_curl_cmd(url, cookie, csrf_token, timeout)
    try:
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout+2)
        raw=r.stdout.strip()
        if not raw:
            log(f"curl empty response (exit {r.returncode}): {r.stderr.strip()[:80]}","WARN")
            return None
        return json.loads(raw)
    except json.JSONDecodeError:
        log(f"curl non-JSON: {r.stdout[:200]}","WARN")
    except Exception as e:
        log(f"curl failed: {e}","WARN")
    return None

def _urllib_get_json(url, cookie=None, csrf_token=None, timeout=10):
    headers=dict(_ROBLOX_HEADERS_BASE)
    if cookie:
        headers["Cookie"]=f".ROBLOSECURITY={cookie}"
    if csrf_token:
        headers["x-csrf-token"]=csrf_token
    try:
        req=urllib.request.Request(url,headers=headers)
        with urllib.request.urlopen(req,timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body=e.read().decode("utf-8","ignore")
        log(f"urllib HTTP {e.code}: {body[:200]}","WARN")
        try:return json.loads(body)
        except:pass
    except Exception as e:
        log(f"urllib failed: {e}","WARN")
    return None

def _api_get_json(url, cookie=None, csrf_token=None, timeout=12):
    """curl first, urllib fallback. Logs Roblox errors, returns None on failure."""
    data=_curl_get_json(url, cookie=cookie, csrf_token=csrf_token, timeout=timeout)
    if data is None:
        data=_urllib_get_json(url, cookie=cookie, csrf_token=csrf_token, timeout=timeout)
    if data is None:
        return None
    if isinstance(data, dict) and data.get("errors"):
        errs=data["errors"]
        log(f"API error: {errs[0].get('message','?')} (code {errs[0].get('code','?')})","WARN")
        return None
    return data

# ══════════════════════════════════════════════════
# SERVER LIST
# Strategy (in order):
#  1. No token, just cookie + Origin/Referer headers
#  2. With CSRF token (cached)
#  3. Fresh CSRF token
#  4. Fresh universe ID + fresh CSRF token
# ══════════════════════════════════════════════════
def _fetch_servers_with_uid(uid, cookie, csrf_token, mode, place_id):
    sort_order="Asc" if mode=="lowest" else "Desc"
    all_servers=[]
    cursor=""

    for page in range(2):
        url=(
            f"https://games.roblox.com/v1/games/{uid}/servers/Public"
            f"?placeId={place_id}&limit=100&sortOrder={sort_order}"
            +(f"&cursor={urllib.parse.quote(cursor)}" if cursor else "")
        )
        data=_api_get_json(url, cookie=cookie, csrf_token=csrf_token, timeout=12)

        if data is None:
            log(f"get_servers: failed on page {page+1}","WARN")
            break

        servers=data.get("data",[])
        all_servers.extend(servers)
        log(f"get_servers: page {page+1} → {len(servers)} servers (total={len(all_servers)})","INFO")

        usable_so_far=[
            s for s in all_servers
            if s.get("accessCode") and s.get("playing") is not None
            and s.get("maxPlayers",0)>0 and s["playing"]<s["maxPlayers"]
        ]
        if usable_so_far and page==0:
            break

        cursor=data.get("nextPageCursor") or ""
        if not cursor:
            break

    return all_servers if all_servers else None

def get_servers(place_id, cookie, mode="highest"):
    if not cookie:
        log("get_servers: no .ROBLOSECURITY cookie set","WARN")
        return None,None

    uid=get_universe_id(place_id)
    if uid is None:
        log("get_servers: could not resolve universe ID","WARN")
        return None,None
    log(f"get_servers: universeId={uid} place={place_id} mode={mode}","INFO")

    # Attempt 1: no CSRF token — Origin+Referer headers often sufficient
    log("get_servers: attempt 1 — no CSRF token (Origin/Referer only)","INFO")
    all_servers=_fetch_servers_with_uid(uid, cookie, None, mode, place_id)

    # Attempt 2: cached CSRF token
    if not all_servers:
        log("get_servers: attempt 2 — with cached CSRF token","INFO")
        csrf=get_csrf_token(cookie)
        if csrf:
            all_servers=_fetch_servers_with_uid(uid, cookie, csrf, mode, place_id)

    # Attempt 3: force fresh CSRF token
    if not all_servers:
        log("get_servers: attempt 3 — fresh CSRF token","INFO")
        invalidate_csrf_token()
        csrf=get_csrf_token(cookie, force_refresh=True)
        all_servers=_fetch_servers_with_uid(uid, cookie, csrf, mode, place_id)

    # Attempt 4: fresh universe ID (in case game was re-published)
    if not all_servers and place_id not in KNOWN_UNIVERSE_IDS:
        log("get_servers: attempt 4 — fresh universe ID","INFO")
        uid2=get_universe_id(place_id, force_refresh=True)
        if uid2 and uid2!=uid:
            log(f"get_servers: new universeId={uid2}","WARN")
            all_servers=_fetch_servers_with_uid(uid2, cookie, csrf if 'csrf' in dir() else None, mode, place_id)

    if not all_servers:
        log(f"get_servers: all attempts failed (mode={mode})","WARN")
        return None,None

    usable=[
        s for s in all_servers
        if s.get("accessCode") and s.get("playing") is not None
        and s.get("maxPlayers",0)>0 and s["playing"]<s["maxPlayers"]
    ]
    if not usable:
        log(f"get_servers: no usable servers in {len(all_servers)} fetched","WARN")
        return None,None

    picked=(max if mode=="highest" else min)(usable, key=lambda s:s["playing"])
    code=picked["accessCode"]
    count=picked["playing"]
    total=picked["maxPlayers"]
    log(f"Server selected ({mode}): {count}/{total} players  code={code[:8]}...","OK")
    return code,count

# ══════════════════════════════════════════════════
# CPU / RAM tracking for Roblox process
# ══════════════════════════════════════════════════
_rblx_pid_cache=None
_rblx_prev_stat=None

def _get_rblx_pid():
    try:
        r=subprocess.run(["su","-c",f"pidof {ROBLOX_PKG}"],capture_output=True,text=True,timeout=3)
        return int(r.stdout.strip().split()[0])
    except:pass
    try:
        for proc in psutil.process_iter(["name","cmdline","pid"]):
            try:
                n=(proc.info["name"]or"").lower()
                c=" ".join(proc.info["cmdline"]or[]).lower()
                if "roblox" in n or ROBLOX_PKG in c:return proc.pid
            except:pass
    except:pass
    return None

def _read_proc_stat(pid):
    try:
        r=subprocess.run(["su","-c",f"cat /proc/{pid}/stat"],capture_output=True,text=True,timeout=3)
        fields=r.stdout.split()
        return int(fields[13])+int(fields[14])
    except:return None

def _read_proc_ram(pid):
    try:
        import re
        r=subprocess.run(["su","-c",f"cat /proc/{pid}/status"],capture_output=True,text=True,timeout=3)
        m=re.search(r'VmRSS:\s*(\d+)',r.stdout)
        return int(m.group(1))//1024 if m else 0
    except:return 0

def get_roblox_process_stats():
    global _rblx_pid_cache,_rblx_prev_stat
    if _rblx_pid_cache is not None:
        try:
            r=subprocess.run(["su","-c",f"kill -0 {_rblx_pid_cache}"],capture_output=True,timeout=2)
            if r.returncode!=0:_rblx_pid_cache=None;_rblx_prev_stat=None
        except:_rblx_pid_cache=None;_rblx_prev_stat=None

    if _rblx_pid_cache is None:
        pid=_get_rblx_pid()
        if pid is None:_rblx_prev_stat=None;return 0,0.0,None
        _rblx_pid_cache=pid
        ticks=_read_proc_stat(pid)
        _rblx_prev_stat=(ticks,time.time()) if ticks is not None else None
        return _read_proc_ram(pid),0.0,pid

    pid=_rblx_pid_cache
    ram_mb=_read_proc_ram(pid)
    cpu=0.0
    ticks=_read_proc_stat(pid)
    if ticks is not None and _rblx_prev_stat is not None:
        prev_ticks,prev_time=_rblx_prev_stat
        elapsed=time.time()-prev_time
        clk_tck=os.sysconf('SC_CLK_TCK') if hasattr(os,'sysconf') else 100
        if elapsed>0:cpu=round(((ticks-prev_ticks)/clk_tck)/elapsed*100,1)
    if ticks is not None:_rblx_prev_stat=(ticks,time.time())
    return ram_mb,cpu,pid

# ══════════════════════════════════════════════════
# DISCORD WEBHOOK
# ══════════════════════════════════════════════════
def send_webhook(cfg,ram,cpu,reason="status",uptime_secs=0):
    if not cfg.get("webhook_enabled") or not cfg.get("webhook_url"):return
    url=cfg["webhook_url"].strip()
    if not url.startswith("https://discord.com/api/webhooks/"):
        log("Webhook URL invalid","WARN");return
    try:
        import uuid
        ts=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ram_free=get_ram_free_mb()
        device=get_device_model()
        shot=take_screenshot()
        has_shot=shot and os.path.exists(shot) and os.path.getsize(shot)>0
        rblx_ram,rblx_cpu,rblx_pid=get_roblox_process_stats()
        rblx_running=rblx_pid is not None

        if not rblx_running:status_dot="🔴";status_txt="OFFLINE";embed_color=0xFF4444
        elif ram>=cfg["ram_limit"]:status_dot="🔴";status_txt="OVERLOADED";embed_color=0xFF4444
        elif ram>=70:status_dot="🟡";status_txt="HIGH RAM";embed_color=0xFFAA00
        else:status_dot="🟢";status_txt="Online";embed_color=0x57F287

        raw_name=get_game_name(cfg["place_id"])
        game_name_str=(raw_name or "Roblox").upper()
        proc_dot="🟢" if rblx_running else "🔴"

        def pbar(pct,total=20):
            filled=int(round(pct/100*total))
            return "█"*filled+"░"*(total-filled)

        try:
            total_ram_mb=int(psutil.virtual_memory().total//(1024*1024))
            used_ram_mb=total_ram_mb-ram_free
        except:total_ram_mb=0;used_ram_mb=0

        desc_lines=[
            f"**Last Updated:** {ts}","",
            "**Device Information:**",
            f"📱 **|** Device: `{device}`",
            f"⚙️ **|** CPU: `{pbar(cpu)}` {cpu:.1f}% / 100%",
            f"💾 **|** RAM: `{pbar(ram)}` {used_ram_mb} MB / {total_ram_mb} MB","",
            "**Instance Status:**",
            f"{status_dot} **|** Status: **{status_txt}**","",
            "**Application Details**",
            f"{proc_dot} {ROBLOX_PKG.upper()} · {game_name_str}",
            f"└ ⏱ `{seconds_to_str(uptime_secs)}`  **|**  💾 `{rblx_ram} MB`  **|**  ⚡ `{rblx_cpu:.1f}%`","",
            "**Session Details**",
            f"🎯 **|** Place ID: `{cfg['place_id']}`",
            f"⏱️ **|** Uptime: `{seconds_to_str(uptime_secs)}`",
            f"🕐 **|** Time: `{ts}`",
        ]
        embed_obj={
            "title":"📊 0x Rejoin Update",
            "description":"\n".join(desc_lines),
            "color":embed_color,
            "footer":{"text":"Roblox Auto-Rejoin v5.3"}
        }
        if has_shot:embed_obj["image"]={"url":"attachment://screen.png"}
        payload={"embeds":[embed_obj]}

        boundary="boundary"+uuid.uuid4().hex;CRLF=b"\r\n"
        def field(name,data,filename=None,ctype="application/octet-stream"):
            if filename:
                hdr=(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{filename}\"\r\nContent-Type: {ctype}\r\n\r\n").encode()
            else:
                hdr=(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n").encode()
            return hdr+data+CRLF

        body=b""
        body+=field("payload_json",json.dumps(payload).encode("utf-8"))
        if has_shot:
            with open(shot,"rb") as f:img_data=f.read()
            body+=field("files[0]",img_data,filename="screen.png",ctype="image/png")
        body+=f"--{boundary}--\r\n".encode()

        req=urllib.request.Request(url,data=body,
            headers={"Content-Type":f"multipart/form-data; boundary={boundary}","User-Agent":"RobloxRejoin/5.3"},
            method="POST")
        with urllib.request.urlopen(req,timeout=20) as resp:
            if resp.status in(200,204):pass  # silent — webhook sent ok
            else:log(f"Webhook failed: {resp.status}","WARN")
    except urllib.error.HTTPError as e:
        log(f"Webhook HTTP {e.code}: {e.read().decode('utf-8','ignore')[:100]}","WARN")
    except Exception as e:
        log(f"Webhook error: {e}","WARN")

def webhook_loop(cfg,stop_event,start_time_ref):
    while not stop_event.is_set():
        time.sleep(cfg["webhook_interval"])
        if stop_event.is_set():break
        send_webhook(cfg,get_ram(),get_cpu(),"scheduled",uptime_secs=int(time.time()-start_time_ref[0]))

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
    # Try su (rooted) force-stop first — most reliable on Android
    try:subprocess.run(["su","-c",f"am force-stop {ROBLOX_PKG}"],timeout=8,capture_output=True)
    except:pass
    # Also try without su
    try:subprocess.run(["am","force-stop",ROBLOX_PKG],timeout=8,capture_output=True)
    except:pass
    # Kill by PID via su
    try:
        r=subprocess.run(["su","-c",f"pidof {ROBLOX_PKG}"],capture_output=True,text=True,timeout=3)
        pid=r.stdout.strip().split()[0]
        subprocess.run(["su","-c",f"kill -9 {pid}"],timeout=3,capture_output=True)
    except:pass
    # psutil fallback
    for proc in psutil.process_iter(["name","cmdline","pid"]):
        try:
            n=(proc.info["name"]or"").lower()
            c=" ".join(proc.info["cmdline"]or[]).lower()
            if "roblox" in n or ROBLOX_PKG in c:os.kill(proc.pid,signal.SIGKILL)
        except:pass
    time.sleep(5)  # wait longer for Android to fully kill the app

def launch(place_id,access_code=None):
    if access_code:
        url=(f"roblox://experiences/start?accessCode={urllib.parse.quote(access_code)}&launchData=rejoin")
        for cmd in [
            ["am","start","-n",f"{ROBLOX_PKG}/com.roblox.client.ActivityProtocolLaunch","-a","android.intent.action.VIEW","-d",url],
            ["am","start","-a","android.intent.action.VIEW","-d",url,"-p",ROBLOX_PKG],
        ]:
            try:
                r=subprocess.run(cmd,capture_output=True,text=True,timeout=10)
                if r.returncode==0:return True
            except:pass
        try:subprocess.run(["termux-open-url",url],capture_output=True,timeout=10);return True
        except:pass
        log("Access-code launch failed — falling back to matchmaking","WARN")

    for cmd in [
        ["am","start","-n",f"{ROBLOX_PKG}/com.roblox.client.ActivityProtocolLaunch","-a","android.intent.action.VIEW","-d",f"roblox://placeId={place_id}&launchData=rejoin"],
        ["am","start","-a","android.intent.action.VIEW","-d",f"roblox://placeId={place_id}","-p",ROBLOX_PKG],
    ]:
        try:
            r=subprocess.run(cmd,capture_output=True,text=True,timeout=10)
            if r.returncode==0:return True
        except:pass
    try:subprocess.run(["termux-open-url",f"roblox://placeId={place_id}"],capture_output=True,timeout=10);return True
    except:pass
    return False

def rejoin(cfg,reason,fresh=False,delay=0,uptime_secs=0):
    global _last_event
    send_webhook(cfg,get_ram(),get_cpu(),f"rejoin:{reason}",uptime_secs=uptime_secs)
    if fresh:kill_roblox();time.sleep(5)
    clear_flags()
    if delay>0:time.sleep(delay)

    access_code=None
    sm=cfg.get("server_mode","off")
    if sm in("highest","lowest"):
        cookie=cfg.get("roblosecurity","").strip()
        if cookie:
            _last_event=f"fetching {sm} server..."
            code,count=get_servers(cfg["place_id"],cookie,mode=sm)
            if code:access_code=code;_last_event=f"joining {sm} server ({count} players)"
            else:_last_event="server fetch failed — using matchmaking"
        else:
            log("server_mode set but no cookie — using matchmaking","WARN")

    launch(cfg["place_id"],access_code=access_code)
    time.sleep(cfg["rejoin_cooldown"])

# ══════════════════════════════════════════════════
# MAIN MONITOR LOOP
# ══════════════════════════════════════════════════
def get_device_model():
    for prop in ["ro.product.model","ro.product.name"]:
        try:
            r=subprocess.run(["getprop",prop],capture_output=True,text=True,timeout=3)
            m=r.stdout.strip()
            if m:return m
        except:pass
    return "Unknown"

def get_ram_free_mb():
    try:return int(psutil.virtual_memory().available//(1024*1024))
    except:return 0

_last_event=""

def draw_dashboard(cfg,ram,cpu,uptime,crashes,next_restart,rblx_ram,rblx_cpu,rblx_running,game_name):
    import re,shutil
    os.system("clear")
    now_str=datetime.now().strftime("%H:%M:%S")
    TW=shutil.get_terminal_size((30,20)).columns
    W=min(TW-2,36)  # never wider than terminal, max 36

    def strip(txt):return re.sub(r'\033\[[0-9;]*m','',txt)
    def row(txt,col="97"):
        plain=strip(txt)
        if len(plain)>W:txt=txt[:W];plain=plain[:W]
        pad=max(0,W-len(plain))
        return cl("|","96")+cl(txt,col)+" "*pad+cl("|","96")
    def div():return cl("+"+"-"*W+"+","96")

    if ram>=cfg["ram_limit"]:stxt="OVERLOADED";scol="91"
    elif not rblx_running:stxt="OFFLINE";scol="91"
    elif crashes>0:stxt=f"CHECKING ({crashes}/{cfg['crash_confirm']})";scol="93"
    else:stxt="INGAME";scol="92"

    gname=(game_name or "Roblox")[:12]
    restart_str=""
    if next_restart:
        remaining=int(next_restart-time.time())
        if remaining>0:restart_str=f" | restart {seconds_to_str(remaining)}"

    event=(_last_event[:W-2] if _last_event else "monitoring...")
    sm=cfg.get("server_mode","off")
    sm_tag={"off":"","highest":" FULL","lowest":" EMPTY"}.get(sm,"")

    lines=[
        div(),
        row(f" 0x REJOIN v5.3","1;97"),
        div(),
        row(f" CPU:{cpu:.1f}% RAM:{ram:.1f}% UP:{seconds_to_str(uptime)}","93"),
        div(),
        row(f" {stxt}  {gname}",scol),
        row(f" rblx RAM:{rblx_ram}MB CPU:{rblx_cpu:.1f}%{sm_tag}","2"),
        div(),
        row(f" {event}","96"),
        row(f" {now_str}{restart_str}","2"),
        div(),
        cl(" Ctrl+C to stop","2"),
    ]
    print("\n".join(lines),flush=True)

def monitor(cfg):
    global _last_event
    os.system("clear")
    print(cl("\n  Starting 0x Rejoin...","96"),flush=True)
    _last_event="seeding cpu..."
    _warmup_cpu()

    clear_flags()
    _last_event="launching roblox"
    _initial_code=None
    _sm=cfg.get("server_mode","off")
    if _sm in("highest","lowest"):
        _cookie=cfg.get("roblosecurity","").strip()
        if _cookie:
            _last_event=f"fetching {_sm} server..."
            _code,_count=get_servers(cfg["place_id"],_cookie,mode=_sm)
            if _code:_initial_code=_code;_last_event=f"joining {_sm} server ({_count} players)"
            else:_last_event="server fetch failed — using matchmaking"
    launch(cfg["place_id"],access_code=_initial_code)

    start_time=time.time()
    start_time_ref=[start_time]
    stop_event=threading.Event()

    if cfg.get("webhook_enabled") and cfg.get("webhook_url"):
        wt=threading.Thread(target=webhook_loop,args=(cfg,stop_event,start_time_ref),daemon=True)
        wt.start()
        _last_event="webhook started"
        time.sleep(5)
        send_webhook(cfg,get_ram(),get_cpu(),"monitor_started",uptime_secs=0)

    time.sleep(cfg["rejoin_cooldown"])
    crashes=0
    next_restart=start_time+cfg["restart_seconds"] if cfg["auto_restart"] else None
    game_name=get_game_name(cfg["place_id"])
    # grace period: ignore crash-checks for this many seconds after any rejoin/restart
    _rejoin_grace_until=time.time()+cfg["rejoin_cooldown"]

    try:
        while True:
            now=time.time()
            uptime=int(now-start_time)
            ram=get_ram();cpu=get_cpu()
            rblx_ram,rblx_cpu,rblx_pid=get_roblox_process_stats()
            rblx_running=rblx_pid is not None
            draw_dashboard(cfg,ram,cpu,uptime,crashes,next_restart,rblx_ram,rblx_cpu,rblx_running,game_name)

            if next_restart and now>=next_restart:
                _last_event="auto restart triggered"
                rejoin(cfg,"auto_restart",fresh=True,uptime_secs=uptime)
                # reset uptime and schedule next restart
                start_time=time.time()
                start_time_ref[0]=start_time
                next_restart=start_time+cfg["restart_seconds"]
                crashes=0
                _rejoin_grace_until=time.time()+cfg["rejoin_cooldown"]
                continue

            if ram>=cfg["ram_limit"]:
                _last_event=f"ram overload {ram:.1f}% — rejoining"
                rejoin(cfg,f"ram({ram:.0f}%)",fresh=True,uptime_secs=uptime)
                crashes=0
                if next_restart:next_restart=time.time()+cfg["restart_seconds"]
                _rejoin_grace_until=time.time()+cfg["rejoin_cooldown"]
                continue

            if cfg["watch_flag"]:
                found,reason,_=check_flag()
                if found:
                    _last_event=f"flag: {reason} — rejoining"
                    rejoin(cfg,f"flag:{reason}",fresh=False,uptime_secs=uptime)
                    crashes=0
                    _rejoin_grace_until=time.time()+cfg["rejoin_cooldown"]
                    continue

            # skip crash detection during grace period (e.g. right after kill+relaunch)
            if now<_rejoin_grace_until:
                _last_event=f"waiting for roblox to start... ({int(_rejoin_grace_until-now)}s)"
                time.sleep(cfg["check_interval"])
                continue

            if not is_running():
                crashes+=1
                _last_event=f"roblox not running ({crashes}/{cfg['crash_confirm']})"
                if crashes>=cfg["crash_confirm"]:
                    _last_event=f"crash! rejoining in {seconds_to_str(cfg['crash_delay'])}..."
                    rejoin(cfg,"crash",fresh=True,delay=cfg["crash_delay"],uptime_secs=uptime)
                    crashes=0
                    if next_restart:next_restart=time.time()+cfg["restart_seconds"]
                    _rejoin_grace_until=time.time()+cfg["rejoin_cooldown"]
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
