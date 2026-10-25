import os,sys,time,signal,subprocess,json,threading
from datetime import datetime

try:
    import termios
    _TTY0=termios.tcgetattr(0)
except:_TTY0=None
_orig_run=subprocess.run
def _run(*a,**k):
    k.setdefault("stdin",subprocess.DEVNULL);return _orig_run(*a,**k)
subprocess.run=_run

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
{cl('║','96')}  {cl('Roblox Auto-Rejoin','1;97')} {cl('🎮','0')}  {cl('v5.5','2')}                      {cl('║','96')}
{cl('║','96')}  {cl('Game Manager · Server Pick · Discord Webhook','2')}   {cl('║','96')}
{cl('╚══════════════════════════════════════════════════╝','96')}
""")

DEFAULT_CFG={
    "place_id":"",
    "check_interval":5,
    "rejoin_cooldown":25,
    "crash_delay":30,
    "crash_confirm":3,
    "ram_limit":90.0,
    "auto_restart":True,
    "restart_seconds":7200,
    "watch_flag":True,
    "webhook_url":"",
    "webhook_interval":60,
    "webhook_enabled":False,
    "server_mode":"off",
    "roblosecurity":"",
    "packages":["com.roblox.client"],
    "launch_stagger":15,
    "lobby_cpu":4.0,
    "seq_join":True,
    "seq_gap":5,
    "seq_timeout":150,
    "heartbeat":False,
    "hb_timeout":45,
    "hb_grace":120,
    "hb_ids":[],
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
        print(f"  {cl('16','95')}. Sequential join       {cl('On' if cfg.get('seq_join',True) else 'Off','93')}  gap {cfg.get('seq_gap',5)}s")
        print(f"  {cl('17','95')}. Heartbeat (executor) {cl('On' if cfg.get('heartbeat') else 'Off','93')}  timeout {cfg.get('hb_timeout',45)}s")
        print(f"  {cl('18','95')}. Heartbeat account names {cl(','.join(cfg.get('hb_ids') or []) or 'auto','2')}")
        print(f"  {cl('15','95')}. Lobby CPU limit       {cl(str(cfg.get('lobby_cpu',4.0))+'%','93')}")
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
                v=v.strip()
                if v.startswith("_|"):v=v
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
        elif c=="15":
            v=inp("Lobby CPU limit % (below this for 1 min = stuck on lobby)",cfg.get("lobby_cpu",4.0))
            try:cfg["lobby_cpu"]=max(0.5,float(v))
            except:pass
        elif c=="16":
            v=inp("Sequential join? (y/n)","y" if cfg.get("seq_join",True) else "n").lower()
            cfg["seq_join"]=v in("y","yes")
            if cfg["seq_join"]:
                g=inp("Seconds to wait after one is in-game",cfg.get("seq_gap",5))
                try:cfg["seq_gap"]=max(0,int(g))
                except:pass
        elif c=="17":
            v=inp("Use executor heartbeat? (y/n)","y" if cfg.get("heartbeat") else "n").lower()
            cfg["heartbeat"]=v in("y","yes")
            if cfg["heartbeat"]:
                g=inp("Rejoin if no heartbeat for (seconds)",cfg.get("hb_timeout",45))
                try:cfg["hb_timeout"]=max(15,int(g))
                except:pass
        elif c=="18":
            print(cl("  Roblox usernames in the same order as your instances, e.g. acc1,acc2 (blank = use package names)","2"))
            v=inp("Names",",".join(cfg.get("hb_ids") or []))
            cfg["hb_ids"]=[x.strip() for x in v.split(",") if x.strip()]
    return cfg

_cpu_value=0.0
_cpu_lock=threading.Lock()

def _sample_cpu_once():
    import re
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
    try:
        r=subprocess.run(["su","-c","top -bn1"],capture_output=True,text=True,timeout=6)
        for line in r.stdout.splitlines():
            mc=re.search(r'(\d+(?:\.\d+)?)%cpu',line,re.I)
            mi=re.search(r'(\d+(?:\.\d+)?)%idle',line,re.I)
            if mc and mi:
                total=float(mc.group(1));idle=float(mi.group(1))
                if total>0:return round((total-idle)/total*100,1)
            mu=re.search(r'(\d+\.?\d*)\s*%?\s*us',line,re.I)
            if mu:return round(float(mu.group(1)),1)
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
    t=threading.Thread(target=_cpu_sampler,daemon=True)
    t.start()
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

SCREENSHOT_PATH="/sdcard/roblox_status.png"

def take_screenshot():
    try:
        r=subprocess.run(["su","-c",f"screencap -p {SCREENSHOT_PATH}"],timeout=10,capture_output=True)
        if os.path.exists(SCREENSHOT_PATH) and os.path.getsize(SCREENSHOT_PATH)>0:return SCREENSHOT_PATH
    except:pass
    try:
        subprocess.run(["screencap","-p",SCREENSHOT_PATH],timeout=10,capture_output=True)
        if os.path.exists(SCREENSHOT_PATH) and os.path.getsize(SCREENSHOT_PATH)>0:return SCREENSHOT_PATH
    except:pass
    return None

_SMALL_CAPS="aᴀbʙcᴄdᴅeᴇfꜰgɢhʜiɪjᴊkᴋlʟmᴍnɴoᴏpᴘqǫrʀsꜱtᴛuᴜvᴠwᴡxхyʏzᴢ"
def to_small_caps(text):
    result=""
    for ch in text:
        if ch.islower():idx=ord(ch)-ord('a');result+=_SMALL_CAPS[idx*2+1]
        elif ch.isupper():idx=ord(ch)-ord('A');result+=_SMALL_CAPS[idx*2+1]
        else:result+=ch
    return result

_game_name_cache={}
_universe_id_cache={}

def get_universe_id(place_id):
    if place_id in _universe_id_cache:return _universe_id_cache[place_id]
    try:
        req=urllib.request.Request(f"https://apis.roblox.com/universes/v1/places/{place_id}/universe",headers={"User-Agent":"RobloxRejoin/5.1"})
        with urllib.request.urlopen(req,timeout=5) as r:
            uid=json.loads(r.read())["universeId"]
            _universe_id_cache[place_id]=uid
            return uid
    except:pass
    return None

def get_game_name(place_id):
    if place_id in _game_name_cache:return _game_name_cache[place_id]
    try:
        uid=get_universe_id(place_id)
        if uid is None:return None
        req2=urllib.request.Request(f"https://games.roblox.com/v1/games?universeIds={uid}",headers={"User-Agent":"RobloxRejoin/5.1"})
        with urllib.request.urlopen(req2,timeout=5) as r2:
            name=json.loads(r2.read())["data"][0]["name"]
            _game_name_cache[place_id]=name
            return name
    except:pass
    return None

def get_servers(place_id,cookie,mode="highest"):
    uid=get_universe_id(place_id)
    if uid is None:log("get_servers: could not resolve universe ID","WARN");return None,None
    if not cookie:log("get_servers: no .ROBLOSECURITY cookie set","WARN");return None,None
    sort_order="Asc" if mode=="lowest" else "Desc"
    all_servers=[];cursor=""
    for page in range(2):
        url=(f"https://games.roblox.com/v1/games/{uid}/servers/Public?limit=100&sortOrder={sort_order}"+(f"&cursor={urllib.parse.quote(cursor)}" if cursor else ""))
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"RobloxRejoin/5.2","Cookie":f".ROBLOSECURITY={cookie}","Accept":"application/json"})
            with urllib.request.urlopen(req,timeout=10) as r:data=json.loads(r.read())
            servers=data.get("data",[]);all_servers.extend(servers)
            usable_so_far=[s for s in all_servers if s.get("accessCode") and s.get("playing") is not None and s.get("maxPlayers",0)>0 and s["playing"]<s["maxPlayers"]]
            if usable_so_far and page==0:break
            cursor=data.get("nextPageCursor") or ""
            if not cursor:break
        except urllib.error.HTTPError as e:body=e.read().decode("utf-8","ignore");log(f"get_servers HTTP {e.code}: {body[:80]}","WARN");break
        except Exception as e:log(f"get_servers error: {e}","WARN");break
    usable=[s for s in all_servers if s.get("accessCode") and s.get("playing") is not None and s.get("maxPlayers",0)>0 and s["playing"]<s["maxPlayers"]]
    if not usable:log(f"get_servers: no usable servers found (fetched {len(all_servers)}, mode={mode})","WARN");return None,None
    picked=max(usable,key=lambda s:s["playing"]) if mode=="highest" else min(usable,key=lambda s:s["playing"])
    code=picked["accessCode"];count=picked["playing"];total=picked["maxPlayers"]
    log(f"Server selected ({mode}): {count}/{total} players  code={code[:8]}...","OK")
    return code,count

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
    found=[]
    def add(p):
        if _PKG_RE.match(p) and p not in found and not p.startswith("com.termux"):found.append(p)
    for cmd in ('pm query-activities --brief -a android.intent.action.VIEW -d "roblox://placeId=1"',
                'cmd package query-activities --brief -a android.intent.action.VIEW -d "roblox://placeId=1"'):
        out=_sh_out(cmd)
        for m in re.finditer(r'([A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+)/[A-Za-z0-9_.$]+',out):add(m.group(1))
        if found:break
    out=_sh_out("pm list packages")
    for ln in out.splitlines():
        if ln.startswith("package:") and "roblox" in ln.lower():add(ln.split(":",1)[1].strip())
    scan=('for p in $(pm list packages -3 | cut -d: -f2); do dumpsys package $p 2>/dev/null | grep -q ActivityProtocolLaunch && echo "FOUND=$p"; done')
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
            if not found:print(cl("  Nothing detected — use M to add package names by hand.","91"));time.sleep(2);continue
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
            if sel:cfg["packages"]=sel;print(cl(f"  ✓ {len(sel)} instance(s) selected","92"))
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
                if 0<=k<len(cur):cur.pop(k);cfg["packages"]=cur or [ROBLOX_PKG]
            except:pass
        elif c=="C":cfg["packages"]=[ROBLOX_PKG]
    return cfg

_inst_pkgs=[]
_inst_stats={}
_inst_state={}
_inst_lock=threading.Lock()
_inst_started=False
_proc_visible=False
INSTANCES=[]

def set_sampler_packages(pkgs):
    global _inst_pkgs
    with _inst_lock:_inst_pkgs=[p for p in pkgs if _PKG_RE.match(p)]

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
                parts=ln.split();pk=parts[0][4:];pid=int(parts[1][4:])
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
        if not d:_inst_state.pop(pk,None);res[pk]=(0,0.0,None);continue
        cpu=0.0;st=_inst_state.get(pk)
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
    _ensure_sampler()
    with _inst_lock:return _inst_stats.get(pkg,(0,0.0,None))

_dumpsys_cache={"out":"","t":0}
_dumpsys_lock=threading.Lock()
_home_pkg_cache={"pkg":None,"t":0}

def _get_dumpsys_activities():
    """Fetch dumpsys activity activities once and cache for 3s so all instances share one call."""
    now=time.time()
    with _dumpsys_lock:
        if now-_dumpsys_cache["t"]<3.0 and _dumpsys_cache["out"]:
            return _dumpsys_cache["out"]
    out=""
    for argv in (["su","-c","dumpsys activity activities"],["dumpsys","activity","activities"]):
        try:
            r=subprocess.run(argv,capture_output=True,text=True,timeout=8)
            if r.stdout.strip():out=r.stdout;break
        except:pass
    with _dumpsys_lock:
        _dumpsys_cache["out"]=out
        _dumpsys_cache["t"]=time.time()
    return out

def _get_home_pkg():
    """Package of the device's home launcher (cached 5 min). Not hardcoded."""
    if _home_pkg_cache["pkg"] and time.time()-_home_pkg_cache["t"]<300:
        return _home_pkg_cache["pkg"]
    pkg=None
    out=_sh_out("pm resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME",timeout=8)
    for ln in reversed(out.splitlines()):
        m=re.match(r'^\s*([A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+)/',ln)
        if m:pkg=m.group(1);break
    _home_pkg_cache["pkg"]=pkg;_home_pkg_cache["t"]=time.time()
    return pkg

def _resumed_pkgs(out):
    """Packages that currently hold the resumed (focused) activity on any display."""
    res=set()
    for m in re.finditer(r'[Rr]esumedActivity[^\n]*?ActivityRecord\{[0-9a-f]+ u\d+ ([^/\s]+)/',out):
        res.add(m.group(1))
    return res

def _get_pkg_activity_state(pkg,out):
    """
    State of one package from a pre-fetched dumpsys output.
      'ingame'    - package has a live (not finishing/destroyed) activity record
      'minimized' - device is on the home screen, or the package's task is gone/finishing
      'offline'   - package not in dumpsys at all
    Activity names are NOT used, so any Roblox clone / package name works.
    A STOPPED activity alone is NOT treated as minimized, because with several
    instances only one can be foreground and the rest are legitimately stopped.
    """
    if not out or pkg not in out:return 'offline'
    # Home screen = the launcher currently owns the resumed activity.
    home=_get_home_pkg()
    resumed=_resumed_pkgs(out)
    if home and home in resumed and pkg not in resumed:return 'minimized'
    recs=list(re.finditer(rf'ActivityRecord\{{[0-9a-f]+ u\d+ {re.escape(pkg)}/(\S+)',out))
    if not recs:return 'minimized'   # process exists but its task/activity is gone
    dead_ev=False;alive_ev=False
    for m in recs:
        nxt=out.find("ActivityRecord{",m.end())
        end=min(len(out),m.end()+3000) if nxt==-1 else min(nxt,m.end()+3000)
        blk=out[m.end():end]
        if ("finishing=true" in blk) or re.search(r'state=(DESTROYED|DESTROYING|FINISHING)',blk):dead_ev=True
        elif "finishing=false" in blk:alive_ev=True
    if dead_ev and not alive_ev:return 'minimized'
    return 'ingame'

# ───────── In-game check via Roblox presence API (per-instance account) ─────────
_acct={}          # pkg -> {"cookie":..., "uid":..., "t":...}
_presence={"t":0,"data":{},"neg":{}}
_presence_lock=threading.Lock()
_presence_err=[""]

def _read_cookie(pkg):
    """Read this app's own .ROBLOSECURITY from its app data (needs root). Returns '' on failure."""
    import sqlite3,tempfile
    try:
        out=_sh_out(f"find /data/data/{pkg} /data/user/0/{pkg} -name Cookies 2>/dev/null",timeout=15)
        paths=[p.strip() for p in out.splitlines() if p.strip().endswith("Cookies")]
        for p in paths:
            try:
                r=subprocess.run(["su","-c",f"cat '{p}'"],capture_output=True,timeout=15)
                if not r.stdout:continue
                tmp=os.path.join(tempfile.gettempdir(),f".ck_{abs(hash(pkg))}.db")
                with open(tmp,"wb") as f:f.write(r.stdout)
                try:
                    con=sqlite3.connect(tmp)
                    rows=con.execute("SELECT value,encrypted_value FROM cookies WHERE name='.ROBLOSECURITY' AND host_key LIKE '%roblox.com'").fetchall()
                    con.close()
                finally:
                    try:os.remove(tmp)
                    except:pass
                for v,ev in rows:
                    if v:return v
            except:pass
    except:pass
    return ""

def _rbx_req(url,cookie,data=None,csrf=None):
    h={"User-Agent":"RobloxRejoin/5.4","Cookie":f".ROBLOSECURITY={cookie}","Accept":"application/json"}
    if data is not None:h["Content-Type"]="application/json"
    if csrf:h["X-CSRF-TOKEN"]=csrf
    req=urllib.request.Request(url,data=json.dumps(data).encode() if data is not None else None,headers=h,method="POST" if data is not None else "GET")
    return urllib.request.urlopen(req,timeout=10)

def _get_uid(pkg):
    a=_acct.get(pkg)
    if a and a.get("uid") and time.time()-a["t"]<1800:return a
    ck=_read_cookie(pkg)
    if not ck:
        _acct[pkg]={"cookie":"","uid":None,"t":time.time()-1500};return _acct[pkg]  # retry in ~5 min
    uid=None
    try:
        with _rbx_req("https://users.roblox.com/v1/users/authenticated",ck) as r:uid=json.loads(r.read()).get("id")
    except Exception as e:_presence_err[0]=f"uid: {e}"
    _acct[pkg]={"cookie":ck,"uid":uid,"t":time.time()}
    return _acct[pkg]

def _fetch_presence(pkgs):
    """One batched presence call for all instances. Returns {pkg: type or None}. 2 = in a game."""
    accts={p:_get_uid(p) for p in pkgs}
    ids={p:a["uid"] for p,a in accts.items() if a.get("uid")}
    if not ids:return {}
    ck=next(a["cookie"] for a in accts.values() if a.get("uid"))
    body={"userIds":list(ids.values())}
    csrf=None;data=None
    for _ in range(2):
        try:
            with _rbx_req("https://presence.roblox.com/v1/presence/users",ck,data=body,csrf=csrf) as r:data=json.loads(r.read());break
        except urllib.error.HTTPError as e:
            if e.code==403 and e.headers.get("x-csrf-token") and not csrf:csrf=e.headers["x-csrf-token"];continue
            _presence_err[0]=f"presence HTTP {e.code}";return {}
        except Exception as e:_presence_err[0]=f"presence: {e}";return {}
    if not data:return {}
    by={u.get("userId"):u.get("userPresenceType") for u in data.get("userPresences",[])}
    return {p:by.get(uid) for p,uid in ids.items()}

def _presence_ingame(pkgs):
    """Set of pkgs CONFIRMED not in a game (2 consecutive negative reads). Unknown -> not included."""
    now=time.time()
    with _presence_lock:
        if now-_presence["t"]>=20:
            _presence["t"]=now
            try:res=_fetch_presence(pkgs)
            except Exception as e:_presence_err[0]=str(e);res={}
            _presence["data"]=res
            for p,t in res.items():
                if t is None:continue
                _presence["neg"][p]=0 if t==2 else _presence["neg"].get(p,0)+1
        return {p for p in pkgs if _presence["neg"].get(p,0)>=2 and _presence["data"].get(p) is not None and _presence["data"].get(p)!=2}

def get_running_set(pkgs):
    """Set of packages that are running AND have a live activity (not home/minimized/finishing)."""
    _ensure_sampler()
    with _inst_lock:st=dict(_inst_stats)
    run={p for p in pkgs if st.get(p,(0,0.0,None))[2] is not None}
    if not run:
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
    out=_get_dumpsys_activities()
    if not out:return run   # dumpsys unavailable -> trust process check, avoid false rejoins
    res={p for p in run if _get_pkg_activity_state(p,out)=='ingame'}
    return _apply_presence(res)

def _apply_presence(res):
    """Drop instances that Roblox says are NOT in a game (sitting on the app home / lobby)."""
    if not res:return res
    now=time.time();check=[]
    for p in res:
        inst=next((i for i in INSTANCES if i["pkg"]==p),None)
        # grace period after a launch: the game needs time to load and presence lags
        if inst and now<(inst.get("busy_until") or 0)+60:continue
        check.append(p)
    if not check:return res
    try:bad=_presence_ingame(check)
    except:bad=set()
    return {p for p in res if p not in bad}

def inst_status(inst,running):
    if inst["launch_at"] is not None:return "OFFLINE"
    if time.time()<inst["busy_until"]:return "LAUNCHING"
    if inst["pkg"] in running:return "INGAME"
    _,_,pid=get_instance_stats(inst["pkg"])
    if pid is not None:return "LOBBY"
    return "CHECKING" if inst["crashes"]>0 else "OFFLINE"

_last_hook=0.0
_session_start=[time.time()]

def send_webhook(cfg,ram,cpu,reason="status",uptime_secs=0):
    global _last_hook
    if not cfg.get("webhook_enabled") or not cfg.get("webhook_url"):return
    url=cfg["webhook_url"].strip()
    if not url.startswith("https://discord.com/api/webhooks/"):
        log(cl("Webhook URL invalid — must start with https://discord.com/api/webhooks/","91"),"WARN");return
    try:
        import uuid
        _last_hook=time.time()
        ts=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ram_free=get_ram_free_mb();device=get_device_model()
        shot=take_screenshot()
        has_shot=shot and os.path.exists(shot) and os.path.getsize(shot)>0
        insts=list(INSTANCES);pkgs=[i["pkg"] for i in insts]
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
            filled=int(round(pct/100*total));return "█"*filled+"░"*(total-filled)
        try:
            total_ram_mb=int(psutil.virtual_memory().total//(1024*1024));used_ram_mb=total_ram_mb-ram_free
        except:total_ram_mb=0;used_ram_mb=0
        dots={"INGAME":"🟢","LAUNCHING":"🟡","CHECKING":"🟡","OFFLINE":"🔴","LOBBY":"🟠"}
        desc_lines=[f"**Last Updated:** {ts}","","**Device Information:**",f"📱 **|** Device: `{device}`",f"⚙️ **|** CPU: `{pbar(cpu)}` {cpu:.1f}% / 100%",f"💾 **|** RAM: `{pbar(ram)}` {used_ram_mb} MB / {total_ram_mb} MB","",f"**Instances ({n_ing}/{len(rows)} ingame):**"]
        now=time.time()
        for i,(inst,status,ram_mb,rcpu) in enumerate(rows,1):
            up=seconds_to_str(now-inst["start"]) if inst["start"] and status!="OFFLINE" else "-"
            desc_lines.append(f"{i}. {dots.get(status,'⚪')} **{inst['pkg']}** : {status.capitalize()}")
            desc_lines.append(f"└ ⏱ `{up}` **|** 💾 `{ram_mb} MB` **|** ⚡ `{rcpu:.1f}%`")
        desc_lines+=["","**Session Details**",f"🎯 **|** Game: `{game_name_str}`",f"🔢 **|** Place ID: `{cfg['place_id']}`",f"⏱️ **|** Uptime: `{seconds_to_str(uptime_secs)}`",f"🕐 **|** Time: `{ts}`"]
        description="\n".join(desc_lines)[:4000]
        embed_obj={"title":"📊 0x Rejoin Update","description":description,"color":embed_color,"footer":{"text":f"Roblox Auto-Rejoin v5.5 · {reason}"[:200]}}
        if has_shot:embed_obj["image"]={"url":"attachment://screen.png"}
        payload={"embeds":[embed_obj]}
        boundary="boundary"+uuid.uuid4().hex;CRLF=b"\r\n"
        def field(name,data,filename=None,ctype="application/octet-stream"):
            if filename:hdr=(f"--{boundary}\r\n"f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'f"Content-Type: {ctype}\r\n\r\n").encode()
            else:hdr=(f"--{boundary}\r\n"f'Content-Disposition: form-data; name="{name}"\r\n\r\n').encode()
            return hdr+data+CRLF
        body=b""
        body+=field("payload_json",json.dumps(payload).encode("utf-8"))
        if has_shot:
            with open(shot,"rb") as f:img_data=f.read()
            body+=field("files[0]",img_data,filename="screen.png",ctype="image/png")
        body+=f"--{boundary}--\r\n".encode()
        req=urllib.request.Request(url,data=body,headers={"Content-Type":f"multipart/form-data; boundary={boundary}","User-Agent":"RobloxRejoin/5.3"},method="POST")
        with urllib.request.urlopen(req,timeout=20) as resp:
            if resp.status in(200,204):log("Webhook sent ✓"+("+screenshot" if has_shot else ""),"WEBHOOK")
            else:log(f"Webhook failed: {resp.status}","WARN")
    except urllib.error.HTTPError as e:
        try:body_txt=e.read().decode("utf-8","ignore")
        except:body_txt=""
        log(f"Webhook HTTP {e.code}: {body_txt[:100]}","WARN")
    except Exception as e:log(f"Webhook error: {e}","WARN")

def fire_webhook(cfg,reason,min_gap=20):
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
    if access_code:
        url=(f"roblox://experiences/start?accessCode={urllib.parse.quote(access_code)}&launchData=rejoin")
        try:
            r=subprocess.run(["am","start","-n",f"{pkg}/com.roblox.client.ActivityProtocolLaunch","-f","0x10008000","-a","android.intent.action.VIEW","-d",url],capture_output=True,text=True,timeout=10)
            if r.returncode==0:return True
        except:pass
        try:
            r=subprocess.run(["am","start","-f","0x10008000","-a","android.intent.action.VIEW","-d",url,"-p",pkg],capture_output=True,text=True,timeout=10)
            if r.returncode==0:return True
        except:pass
        try:subprocess.run(["termux-open-url",url],capture_output=True,timeout=10);return True
        except:pass
        log("Access-code launch failed — falling back to default matchmaking","WARN")
    try:
        r=subprocess.run(["am","start","-n",f"{pkg}/com.roblox.client.ActivityProtocolLaunch","-f","0x10008000","-a","android.intent.action.VIEW","-d",f"roblox://placeId={place_id}&launchData=rejoin"],capture_output=True,text=True,timeout=10)
        if r.returncode==0:return True
    except:pass
    try:
        r=subprocess.run(["am","start","-f","0x10008000","-a","android.intent.action.VIEW","-d",f"roblox://placeId={place_id}","-p",pkg],capture_output=True,text=True,timeout=10)
        if r.returncode==0:return True
    except:pass
    try:subprocess.run(["termux-open-url",f"roblox://placeId={place_id}"],capture_output=True,timeout=10);return True
    except:pass
    return False

def _do_launch(cfg,inst):
    global _last_event
    pk=inst["pkg"];access=None;sm=cfg.get("server_mode","off")
    if sm in("highest","lowest"):
        cookie=cfg.get("roblosecurity","").strip()
        if cookie:
            _last_event=f"{pk[-16:]}: fetching {sm} server..."
            code,count=get_servers(cfg["place_id"],cookie,mode=sm)
            if code:access=code
        else:log("server_mode set but no .ROBLOSECURITY cookie — using matchmaking","WARN")
    ok=launch(cfg["place_id"],access_code=access,pkg=pk)
    now=time.time()
    inst["launch_at"]=None;inst["start"]=now;inst["crashes"]=0
    inst["busy_until"]=now+cfg["rejoin_cooldown"]
    inst["next_restart"]=now+cfg["restart_seconds"] if cfg.get("auto_restart") else None
    inst["hook_at"]=inst["busy_until"] if inst.get("reason") else None
    inst["reason"]=None;inst["seq_confirm"]=None
    _last_event=f"{pk[-16:]}: launched"+("" if ok else " (failed)")

def _begin_rejoin(cfg,inst,reason,fresh,delay):
    global _last_event
    pk=inst["pkg"]
    _last_event=f"{pk[-16:]}: {reason} — rejoining"
    fire_webhook(cfg,f"{reason}:{pk}")
    if fresh:kill_roblox(pk)
    inst["crashes"]=0;inst["reason"]=reason;inst["next_restart"]=None
    inst["launch_at"]=time.time()+max(0,delay)

def get_device_model():
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
    try:vm=psutil.virtual_memory();return int(vm.available//(1024*1024))
    except:return 0

_last_event=""

def _bar(pct,w=12):
    filled=int(round(max(0,min(100,pct))/100*w));return "█"*filled+"░"*(w-filled)

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
    now=time.time();now_str=datetime.now().strftime("%H:%M:%S");W=44
    rest=[i["next_restart"]-now for i in insts if i.get("next_restart")]
    restart_str=f"  ↺ restart in {seconds_to_str(min(rest))}" if rest and min(rest)>0 else ""
    gname=(game_name or "Roblox").upper();event=_last_event if _last_event else "monitoring..."
    sm=cfg.get("server_mode","off");sm_tag={"highest":" · FULL","lowest":" · EMPTY"}.get(sm,"")
    STATUS_DOT={"INGAME":cl("●","92"),"LAUNCHING":cl("◐","93"),"CHECKING":cl("◐","93"),"OFFLINE":cl("○","91"),"LOBBY":cl("◑","93")}
    STATUS_COL={"INGAME":"92","LAUNCHING":"93","CHECKING":"93","OFFLINE":"91","LOBBY":"93"}
    lines=["",cl(f"  0x REJOIN  v5.5  ·  {gname}{sm_tag}","1;97"),cl("  "+"─"*W,"2"),
           f"  {cl('CPU','2')} {cl(_bar(cpu),'0')}{cl(f' {cpu:5.1f}%',_cpu_color(cpu))}   {cl('RAM','2')} {cl(_bar(ram),'0')}{cl(f' {ram:5.1f}%',_ram_color(ram))}   {cl('⏱','2')} {cl(seconds_to_str(uptime),'97')}",
           cl("  "+"─"*W,"2")]
    for n,inst in enumerate(insts,1):
        status=inst_status(inst,running);ram_mb,rcpu,_pid=get_instance_stats(inst["pkg"])
        up=seconds_to_str(now-inst["start"]) if inst["start"] and status!="OFFLINE" else "--"
        dot=STATUS_DOT.get(status,cl("○","2"));scol=STATUS_COL.get(status,"97");pkg_short=inst["pkg"][-20:]
        lines.append(f"  {dot} {cl(pkg_short,'97')}  {cl(status,scol)}")
        lines.append(f"    {cl('RAM','2')} {cl(f'{ram_mb}MB','97')}  {cl('CPU','2')} {cl(_bar(rcpu,8),'0')}{cl(f' {rcpu:.1f}%',_cpu_color(rcpu))}  {cl('UP','2')} {cl(up,'97')}")
    lines.append(cl("  "+"─"*W,"2"))
    lines.append(f"  {cl(now_str,'2')}  {cl(event[:W-12],'97')}")
    if cfg.get("heartbeat"):
        try:
            bits=[]
            for inst in insts:
                h=_hb_state(cfg,inst["pkg"])
                bits.append(f"{inst['pkg'][-6:]}:"+("--" if h is None else (h[1] if h[1]!="alive" else f"{int(now-h[0])}s")))
            lines.append(cl("  heartbeat "+"  ".join(bits),"2"))
        except:pass
    if restart_str:lines.append(cl(restart_str,"93"))
    lines.append(f"  {cl('ctrl+c to stop','2')}")
    lines.append("")
    try:
        if _TTY0:termios.tcsetattr(0,termios.TCSANOW,_TTY0)
    except:pass
    sys.stdout.write("\033[H\033[2J"+"\r\n".join(lines)+"\r\n");sys.stdout.flush()

_hb_cache={"path":{},"read":{},"miss":{}}

def _hb_id(cfg,pk):
    pkgs=cfg.get("packages") or [ROBLOX_PKG];ids=cfg.get("hb_ids") or []
    try:i=pkgs.index(pk)
    except:i=-1
    return ids[i] if 0<=i<len(ids) and ids[i] else None

def _hb_scan_all(pk):
    """Scan all executor paths for any hb_*.txt file, return (path, username) or None."""
    # Check known paths first
    for d in EXECUTOR_PATHS:
        try:
            if not os.path.isdir(d):continue
            for fn in os.listdir(d):
                if fn.startswith("hb_") and fn.endswith(".txt"):
                    return os.path.join(d,fn),fn[3:-4]
        except:pass
    # Deep search in Android data folder
    try:
        out=_sh_out(f"find /sdcard/Android/data/{pk} -maxdepth 7 -name 'hb_*.txt' 2>/dev/null",timeout=20)
        for l in out.splitlines():
            l=l.strip()
            if l:
                fn=os.path.basename(l)
                return l,fn[3:-4]
    except:pass
    return None

_hb_auto={}  # pk -> (path, username)

def _hb_state(cfg,pk):
    """Read the executor heartbeat file -> (timestamp, status) or None."""
    hid=_hb_id(cfg,pk);now=time.time()
    c=_hb_cache["read"].get(pk)
    if c and now-c[0]<3:return c[1]
    cands=[];p=_hb_cache["path"].get(pk)
    if p:
        cands=[p]
    else:
        if hid:
            # username configured — search by name
            name=f"hb_{hid}.txt"
            if now-_hb_cache["miss"].get(pk,0)>45:
                cands=[os.path.join(d,name) for d in EXECUTOR_PATHS]
                out=_sh_out(f"find /sdcard/Android/data/{pk} -maxdepth 7 -name '{name}' 2>/dev/null",timeout=20)
                cands+=[l.strip() for l in out.splitlines() if l.strip()]
        else:
            # no username set — auto-detect any hb_*.txt
            cached=_hb_auto.get(pk)
            if cached:
                cands=[cached[0]]
            elif now-_hb_cache["miss"].get(pk,0)>45:
                found=_hb_scan_all(pk)
                if found:
                    _hb_auto[pk]=found;cands=[found[0]]
    res=None
    for p in cands:
        try:txt=open(p).read() if os.path.exists(p) else _sh_out(f"cat '{p}'",timeout=5)
        except:txt=""
        txt=(txt or "").strip()
        if not txt:continue
        parts=txt.split("|")
        try:ts=float(parts[0])
        except:continue
        res=(ts,parts[2].strip().lower() if len(parts)>2 else "alive");_hb_cache["path"][pk]=p;break
    if res is None:
        _hb_cache["path"].pop(pk,None);_hb_auto.pop(pk,None);_hb_cache["miss"][pk]=now
    _hb_cache["read"][pk]=(now,res)
    return res

def _seq_can_launch(cfg,inst,insts,running,now):
    """Sequential join: launch only after every earlier instance is confirmed in-game (+gap)."""
    if not cfg.get("seq_join",True) or len(insts)<2:return True
    gap=cfg.get("seq_gap",5);tmo=cfg.get("seq_timeout",150)
    for o in insts:
        if o is inst or o["launch_at"] is not None or not o.get("start"):continue
        if now>=o["start"]+tmo:continue          # waited long enough, don't block forever
        up=o["pkg"] in running and now>=o["busy_until"] and get_instance_stats(o["pkg"])[1]>=cfg.get("lobby_cpu",4.0)
        if up:
            if o.get("seq_confirm") is None:o["seq_confirm"]=now
            if now<o["seq_confirm"]+gap:return False
            continue
        return False
    return True

def monitor(cfg):
    global _last_event
    os.system("clear");print(cl("\n  Starting 0x Rejoin...","96"),flush=True)
    pkgs=[p for p in (cfg.get("packages") or [ROBLOX_PKG]) if _PKG_RE.match(p)] or [ROBLOX_PKG]
    set_sampler_packages(pkgs)
    _last_event="seeding cpu...";_warmup_cpu()
    single=len(pkgs)==1
    if single:clear_flags()
    start_time=time.time();_session_start[0]=start_time
    stagger=max(0,int(cfg.get("launch_stagger",15)))
    insts=[]
    for i,pk in enumerate(pkgs):
        insts.append({"pkg":pk,"launch_at":start_time+(0 if cfg.get("seq_join",True) else i*stagger),"busy_until":0,"crashes":0,
                      "start":None,"next_restart":None,"reason":None,"hook_at":None,"idle_count":0})
    INSTANCES[:]=insts;_last_event=f"launching {len(pkgs)} instance(s)"
    start_time_ref=[start_time];stop_event=threading.Event()
    if cfg.get("webhook_enabled") and cfg.get("webhook_url"):
        threading.Thread(target=webhook_loop,args=(cfg,stop_event,start_time_ref),daemon=True).start()
    startup_hook_at=start_time+(len(pkgs)-1)*stagger+cfg["rejoin_cooldown"]+5
    game_name=get_game_name(cfg["place_id"]);last_overload=0.0
    try:
        while True:
            now=time.time();uptime=int(now-start_time)
            ram=get_ram();cpu=get_cpu();running=get_running_set(pkgs)
            if single and cfg["watch_flag"]:
                found,reason,_=check_flag()
                if found and insts[0]["launch_at"] is None and now>=insts[0]["busy_until"]:
                    clear_flags();_begin_rejoin(cfg,insts[0],f"flag:{reason}",False,0)
            for inst in insts:
                pk=inst["pkg"]
                if inst["launch_at"] is not None:
                    if now>=inst["launch_at"] and _seq_can_launch(cfg,inst,insts,running,now):_do_launch(cfg,inst)
                    continue
                if inst.get("hook_at") and now>=inst["hook_at"]:
                    inst["hook_at"]=None;fire_webhook(cfg,f"rejoined:{pk}")
                if now<inst["busy_until"]:continue
                if inst["next_restart"] and now>=inst["next_restart"]:
                    _begin_rejoin(cfg,inst,"auto_restart",True,0);continue
                if cfg.get("heartbeat") and pk in running and now>=inst["busy_until"]+cfg.get("hb_grace",30):
                    hb=_hb_state(cfg,pk)
                    if hb is not None:
                        lost=(now-hb[0])>cfg.get("hb_timeout",45)
                        disc=hb[1]=="disconnect"
                        if lost or disc:
                            _fr=(now-inst.get("last_lobby",0))<300
                            inst["last_lobby"]=now
                            _begin_rejoin(cfg,inst,"disconnected" if disc else "heartbeat lost",_fr,cfg["crash_delay"] if _fr else 0)
                            continue
                if pk not in running:
                    inst["crashes"]+=1;inst["idle_count"]=0
                    _last_event=f"{pk[-16:]}: not running ({inst['crashes']}/{cfg['crash_confirm']})"
                    if inst["crashes"]>=cfg["crash_confirm"]:
                        _begin_rejoin(cfg,inst,"crash",True,cfg["crash_delay"])
                else:
                    if inst["crashes"]>0:_last_event=f"{pk[-16:]}: running ✓"
                    inst["crashes"]=0
                    # ── Bubble detection (tuned down) ──────────────────
                    # Only trigger if CPU is basically dead (< 0.3%) for a
                    # long time (>120s) — avoids false positives on idle games
                    _,rcpu,_=get_instance_stats(pk)
                    busy_secs=now-inst["busy_until"] if inst["busy_until"] else 999
                    if rcpu<cfg.get("lobby_cpu",4.0) and busy_secs>60:
                        inst["idle_count"]=inst.get("idle_count",0)+1
                        if inst["idle_count"]>=8:
                            _last_event=f"{pk[-16:]}: stuck on lobby, rejoining"
                            inst["idle_count"]=0
                            _fr=(now-inst.get("last_lobby",0))<300
                            inst["last_lobby"]=now
                            _begin_rejoin(cfg,inst,"lobby",_fr,cfg["crash_delay"] if _fr else 0)
                    else:
                        inst["idle_count"]=0
            if ram>=cfg["ram_limit"] and now-last_overload>=max(60,cfg["rejoin_cooldown"]*2):
                cands=[i for i in insts if i["launch_at"] is None and now>=i["busy_until"] and i["pkg"] in running]
                if cands:
                    worst=max(cands,key=lambda i:get_instance_stats(i["pkg"])[0])
                    _begin_rejoin(cfg,worst,f"ram({ram:.0f}%)",True,0);last_overload=time.time()
            if startup_hook_at and now>=startup_hook_at:
                startup_hook_at=None;fire_webhook(cfg,"monitor_started",min_gap=0)
            draw_dashboard(cfg,ram,cpu,uptime,insts,running,game_name)
            time.sleep(cfg["check_interval"])
    except KeyboardInterrupt:
        os.system("clear");print(cl("\n  Stopped.\n","93"),flush=True);stop_event.set()

if __name__=="__main__":
    banner();games=load_games();cfg=load_config()
    if not games:
        print(cl("  No saved games — let's add your first game!","93"));time.sleep(1)
        games=game_manager(games)
    place_id,games=pick_game(games,cfg)
    cfg["place_id"]=place_id;cfg=settings_menu(cfg);monitor(cfg)
