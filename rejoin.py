import os,sys,time,signal,subprocess,json
from datetime import datetime

try:
    import psutil
except:
    subprocess.run([sys.executable,"-m","pip","install","psutil"],check=True)
    import psutil

ROBLOX_PKG="com.roblox.client"
FLAG_FILENAME="disconnect.flag"
GAMES_FILE=os.path.expanduser("~/roblox_games.json")
EXECUTOR_PATHS=[
    "/sdcard/Fluxus/workspace/","/sdcard/Delta/workspace/",
    "/sdcard/AceusX/workspace/","/sdcard/ArceusX/workspace/",
    "/sdcard/Hydrogen/workspace/","/sdcard/Codex/workspace/",
    "/sdcard/Trigon/workspace/","/sdcard/Xeno/workspace/",
    os.path.expanduser("~/"),"/sdcard/"
]

# ─── COLORS ───────────────────────────────────────────────
R="\033[91m";G="\033[92m";Y="\033[93m";B="\033[94m"
M="\033[95m";C="\033[96m";W="\033[97m";DIM="\033[2m"
RESET="\033[0m";BOLD="\033[1m"
def cl(t,c):return f"\033[{c}m{t}{RESET}"

# ─── LOGGING ──────────────────────────────────────────────
def log(msg,level="INFO"):
    icons={"INFO":cl("ℹ","96"),"OK":cl("✓","92"),"WARN":cl("!","93"),
           "ERROR":cl("✗","91"),"ACTION":cl("»","95"),"FLAG":cl("⚑","93"),
           "KILL":cl("☠","91"),"RAM":cl("▣","94"),"TIMER":cl("◷","96")}
    ts=cl(datetime.now().strftime("%H:%M:%S"),"2")
    print(f"[{ts}] {icons.get(level,'·')} {msg}",flush=True)

def ask(prompt,default=None):
    suffix=f" [{cl(str(default),'93')}]" if default is not None else ""
    try:
        val=input(f"  {cl('→','96')} {prompt}{suffix}: ").strip()
        return val if val else str(default) if default is not None else val
    except(EOFError,KeyboardInterrupt):
        print();sys.exit(0)

def ask_int(prompt,default,mn=1,mx=99999):
    while True:
        raw=ask(prompt,default)
        try:
            v=int(raw)
            if mn<=v<=mx:return v
            print(cl(f"  Enter a number between {mn} and {mx}","91"))
        except:print(cl("  Enter a valid number","91"))

def ask_float(prompt,default,mn=0.1,mx=99999):
    while True:
        raw=ask(prompt,default)
        try:
            v=float(raw)
            if mn<=v<=mx:return v
            print(cl(f"  Enter a number between {mn} and {mx}","91"))
        except:print(cl("  Enter a valid number","91"))

def ask_yn(prompt,default="y"):
    while True:
        raw=ask(f"{prompt} (y/n)",default).lower()
        if raw in("y","yes"):return True
        if raw in("n","no"):return False
        print(cl("  Enter y or n","91"))

def seconds_to_str(s):
    s=int(s)
    if s<60:return f"{s}s"
    elif s<3600:return f"{s//60}m {s%60}s"
    else:return f"{s//3600}h {(s%3600)//60}m"

def divider(char="─",color="96",width=48):
    print(cl(char*width,color))

def banner():
    print(f"""
{cl('╔════════════════════════════════════════════════╗','96')}
{cl('║','96')}   {cl('Roblox Auto-Rejoin Monitor','1;97')} {cl('🎮','0')}              {cl('║','96')}
{cl('║','96')}   {cl('v4.0 — Game Manager + Full Customisation','2')}    {cl('║','96')}
{cl('╚════════════════════════════════════════════════╝','96')}
""")

# ─── GAME LIST MANAGER ────────────────────────────────────
def load_games():
    try:
        if os.path.exists(GAMES_FILE):
            with open(GAMES_FILE,"r") as f:
                return json.load(f)
    except:pass
    return []

def save_games(games):
    try:
        with open(GAMES_FILE,"w") as f:
            json.dump(games,f,indent=2)
    except Exception as e:
        print(cl(f"  Could not save games: {e}","91"))

def print_game_list(games):
    if not games:
        print(cl("  No saved games yet.","2"))
        return
    print()
    print(cl("  Saved Games:","97;1"))
    divider()
    for i,g in enumerate(games,1):
        name=cl(g["name"],"93;1")
        pid=cl(g["place_id"],"96")
        print(f"  {cl(str(i),'95;1')}. {name}  {cl('—','2')} Place ID: {pid}")
    divider()

def game_manager(games):
    while True:
        banner()
        print(cl("  ── Game Manager ──────────────────────────────","96"))
        print_game_list(games)
        print()
        print(f"  {cl('A','92')}. Add a game")
        if games:
            print(f"  {cl('D','91')}. Delete a game")
            print(f"  {cl('R','93')}. Rename a game")
        print(f"  {cl('B','96')}. Back to main menu")
        print()
        choice=ask("Choose option").upper()

        if choice=="A":
            print()
            print(cl("  ── Add Game ──────────────────────────────────","96"))
            name=ask("Game name (e.g. Steal an Egg)")
            if not name:continue
            pid=ask("Place ID (numbers from game URL)")
            if not pid or not pid.isdigit():
                print(cl("  Invalid Place ID — numbers only","91"))
                time.sleep(1);continue
            games.append({"name":name,"place_id":pid})
            save_games(games)
            print(cl(f"  ✓ '{name}' saved!","92"))
            time.sleep(1)

        elif choice=="D" and games:
            print()
            print_game_list(games)
            raw=ask("Enter number to delete (or 0 to cancel)","0")
            try:
                idx=int(raw)-1
                if 0<=idx<len(games):
                    removed=games.pop(idx)
                    save_games(games)
                    print(cl(f"  ✓ '{removed['name']}' deleted!","92"))
                    time.sleep(1)
            except:pass

        elif choice=="R" and games:
            print()
            print_game_list(games)
            raw=ask("Enter number to rename (or 0 to cancel)","0")
            try:
                idx=int(raw)-1
                if 0<=idx<len(games):
                    new_name=ask(f"New name for '{games[idx]['name']}'")
                    if new_name:
                        games[idx]["name"]=new_name
                        save_games(games)
                        print(cl(f"  ✓ Renamed to '{new_name}'!","92"))
                        time.sleep(1)
            except:pass

        elif choice=="B":
            break

    return games

def pick_game(games):
    """Show game picker, return chosen place_id."""
    while True:
        print()
        print(cl("  ── Select Game to Join ───────────────────────","96"))
        print()
        if games:
            for i,g in enumerate(games,1):
                name=cl(g["name"],"93;1")
                pid=cl(g["place_id"],"96")
                print(f"  {cl(str(i),'95;1')}. {name}  {cl('—','2')} {pid}")
            print()
            print(f"  {cl('M','92')}. Enter Place ID manually")
            print(f"  {cl('E','96')}. Manage games (add/delete/rename)")
            print()
            choice=ask("Choose a game (number, M or E)")

            if choice.upper()=="E":
                games=game_manager(games)
                continue
            elif choice.upper()=="M":
                pid=ask("Enter Place ID")
                if pid and pid.isdigit():return pid,games
                else:print(cl("  Invalid Place ID","91"))
            else:
                try:
                    idx=int(choice)-1
                    if 0<=idx<len(games):
                        chosen=games[idx]
                        print(cl(f"\n  ✓ Selected: {chosen['name']}","92"))
                        time.sleep(0.5)
                        return chosen["place_id"],games
                    else:print(cl("  Invalid choice","91"))
                except:print(cl("  Invalid choice","91"))
        else:
            print(cl("  No saved games yet — enter a Place ID manually","93"))
            print(f"  {cl('A','92')}. Add a game first")
            print(f"  {cl('M','92')}. Enter Place ID manually")
            print()
            choice=ask("Choose option").upper()
            if choice=="A":
                games=game_manager(games)
            elif choice=="M":
                pid=ask("Enter Place ID")
                if pid and pid.isdigit():return pid,games
                else:print(cl("  Invalid Place ID","91"))

# ─── SETTINGS MENU ────────────────────────────────────────
def settings_menu(place_id):
    print()
    print(cl("  ── Monitor Settings ──────────────────────────","96"))
    print()

    check_interval=ask_int("Check interval (seconds)",5,1,60)
    rejoin_cooldown=ask_int("Rejoin cooldown (seconds after launching)",25,5,300)

    print()
    print(cl("  ── Crash Settings ────────────────────────────","96"))
    print()
    crash_delay=ask_int("Crash rejoin delay (seconds to wait before rejoining)",30,0,600)
    crash_confirm=ask_int("Crash confirm checks (checks before acting)",2,1,10)

    print()
    print(cl("  ── RAM Settings ──────────────────────────────","96"))
    print()
    ram_limit=ask_float("RAM % limit before kill+rejoin",90,10,99)

    print()
    print(cl("  ── Auto Restart ──────────────────────────────","96"))
    print()
    auto_restart=ask_yn("Enable auto restart?","y")
    restart_seconds=None
    if auto_restart:
        unit=ask("Restart interval unit — hours (h) or minutes (m)","h").lower()
        if unit in("h","hours"):
            val=ask_float("Restart every X hours",2,0.1,24)
            restart_seconds=int(val*3600)
        else:
            val=ask_float("Restart every X minutes",120,1,1440)
            restart_seconds=int(val*60)
        print(cl(f"  ✓ Auto restart every {seconds_to_str(restart_seconds)}","92"))

    print()
    print(cl("  ── Disconnect Flag ───────────────────────────","96"))
    print()
    watch_flag=ask_yn("Watch executor disconnect flag files?","y")

    print()
    print(cl("  ── Summary ───────────────────────────────────","96"))
    divider()
    print(f"  {cl('Place ID:','97')}         {cl(place_id,'93')}")
    print(f"  {cl('Check every:','97')}      {cl(seconds_to_str(check_interval),'93')}")
    print(f"  {cl('Rejoin cooldown:','97')}  {cl(seconds_to_str(rejoin_cooldown),'93')}")
    print(f"  {cl('Crash delay:','97')}      {cl(seconds_to_str(crash_delay),'93')}")
    print(f"  {cl('Crash confirms:','97')}   {cl(str(crash_confirm),'93')} checks")
    print(f"  {cl('RAM limit:','97')}        {cl(str(ram_limit)+'%','93')}")
    print(f"  {cl('Auto restart:','97')}     {cl(seconds_to_str(restart_seconds),'93') if auto_restart else cl('Off','91')}")
    print(f"  {cl('Flag watching:','97')}    {cl('On','92') if watch_flag else cl('Off','91')}")
    divider()
    print()

    go=ask_yn("Start monitor with these settings?","y")
    if not go:
        print(cl("  Cancelled.","91"))
        sys.exit(0)

    return {
        "place_id":place_id,
        "check_interval":check_interval,
        "rejoin_cooldown":rejoin_cooldown,
        "crash_delay":crash_delay,
        "crash_confirm":crash_confirm,
        "ram_limit":ram_limit,
        "auto_restart":auto_restart,
        "restart_seconds":restart_seconds,
        "watch_flag":watch_flag,
    }

# ─── ROBLOX CONTROL ───────────────────────────────────────
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
            if "roblox" in n or ROBLOX_PKG in c:
                os.kill(proc.pid,signal.SIGKILL)
        except:pass
    try:subprocess.run(["am","force-stop",ROBLOX_PKG],timeout=5,capture_output=True)
    except:pass
    time.sleep(2)

def launch(place_id):
    log(f"Launching {cl(place_id,'93')}","ACTION")
    try:
        r=subprocess.run([
            "am","start","-n",
            f"{ROBLOX_PKG}/com.roblox.client.ActivityProtocolLaunch",
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
    if fresh:kill_roblox();time.sleep(3)
    clear_flags()
    if delay>0:
        log(f"Waiting {cl(seconds_to_str(delay),'93')} before rejoining...","ACTION")
        time.sleep(delay)
    launch(cfg["place_id"])
    log(f"Cooling down {cl(seconds_to_str(cfg['rejoin_cooldown']),'93')}...","ACTION")
    time.sleep(cfg["rejoin_cooldown"])

def get_ram():
    try:return psutil.virtual_memory().percent
    except:return 0

# ─── MAIN MONITOR LOOP ────────────────────────────────────
def monitor(cfg):
    print()
    print(cl("╔════════════════════════════════════════════════╗","92"))
    print(cl("║  Monitor ACTIVE — Ctrl+C to stop               ║","92"))
    print(cl("╚════════════════════════════════════════════════╝","92"))
    print()

    clear_flags()
    log("Initial launch...","ACTION")
    launch(cfg["place_id"])
    time.sleep(cfg["rejoin_cooldown"])

    crashes=0
    start_time=time.time()
    next_restart=start_time+cfg["restart_seconds"] if cfg["auto_restart"] else None

    while True:
        try:
            now=time.time()

            # ── Auto restart ────────────────────────────────
            if next_restart and now>=next_restart:
                log(f"Auto restart triggered after {cl(seconds_to_str(now-start_time),'93')}","TIMER")
                rejoin(cfg,"auto_restart",fresh=True)
                next_restart=time.time()+cfg["restart_seconds"]
                crashes=0;continue

            ram=get_ram()
            if next_restart:
                remaining=int(next_restart-now)
                log(f"RAM: {cl(f'{ram:.1f}%','94')}  │  Restart in: {cl(seconds_to_str(remaining),'96')}","TIMER")
            else:
                log(f"RAM: {cl(f'{ram:.1f}%','94')}","RAM")

            # ── RAM overload ────────────────────────────────
            if ram>=cfg["ram_limit"]:
                log(f"RAM overload! {cl(f'{ram:.1f}%','91')}","RAM")
                rejoin(cfg,f"ram({ram:.0f}%)",fresh=True)
                crashes=0
                if next_restart:next_restart=time.time()+cfg["restart_seconds"]
                continue

            # ── Disconnect flag ─────────────────────────────
            if cfg["watch_flag"]:
                found,reason,_=check_flag()
                if found:
                    log(f"Disconnect flag! {cl(reason,'93')}","FLAG")
                    rejoin(cfg,f"flag:{reason}",fresh=False)
                    crashes=0;continue

            # ── Crash detection ─────────────────────────────
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
            break
        except Exception as e:
            log(f"Error: {cl(str(e),'91')}","ERROR")
            time.sleep(cfg["check_interval"])

# ─── ENTRY ────────────────────────────────────────────────
if __name__=="__main__":
    banner()
    games=load_games()

    # If no saved games yet, go straight to game manager
    if not games:
        print(cl("  No saved games found — let's add your first game!","93"))
        time.sleep(1)
        games=game_manager(games)

    place_id,games=pick_game(games)
    cfg=settings_menu(place_id)
    monitor(cfg)
