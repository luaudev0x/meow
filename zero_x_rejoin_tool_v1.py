"""ZERO X REJOIN TOOL V1 FREE VERSION

Run:
    python zero_x_rejoin_tool_v1.py

Select clones with option 6, enable option 15 for Auto sort on launch, then S.
The selected clone count determines the grid. Each clone opens at its prepared
size and position, and its bounds are checked before the next clone launches.
The working Termux-compatible window preparation is retained; no touch input
or drag/resize fallback is used. Root is required for this layout feature.

Main-menu groups:
  5. Webhook: choose On or Off; when On, enter the Discord webhook URL,
     set its interval, then Save. Back/Cancel discards the submenu changes.
 14. Config: CPU limit, RAM limit, and overload confirmation checks.
     Save applies all three settings together; Back/Cancel discards changes.

Confirmed crash restarts have no extra crash-delay setting. Polling, crash
confirmation, and the normal rejoin cooldown retain their separate functions.
Shared disconnect-flag watching is always enabled for single-instance runs.
Multiple-instance runs retain their existing per-instance heartbeat handling.
Previous settings load from ~/roblox_config.json; retired delay values are
discarded and a previously disabled flag watcher is enabled automatically.

For a read-only check of already-open windows:
    python zero_x_rejoin_tool_v1.py --layout-test
This check does not open, stop, move, or resize windows. It gives 10 seconds to
show the windows, then checks their bounds. Normal rejoin opens clones in place.
Keep the same orientation while running. If saved-layout preparation fails,
the sequence stops and writes ~/roblox_auto_sort_report.json with its reason.
"""
import os,sys,time,signal,subprocess,json,threading
from datetime import datetime

if __name__ == "__main__" and "--help" in sys.argv:
    print(__doc__)
    sys.exit(0)

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
except ImportError:
    if __name__ == "__main__" and "--layout-test" in sys.argv:
        psutil = None  # The standalone window check needs only the standard library.
    else:
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

"""Terminal settings for ZERO X REJOIN TOOL V1 FREE VERSION."""


def banner():
    import shutil
    import textwrap
    os.system("clear")
    title = "ZERO X REJOIN TOOL V1 FREE VERSION"
    columns = max(8, shutil.get_terminal_size((80, 24)).columns)
    lines = textwrap.wrap(title, width=max(1, min(48, columns - 6)))
    width = max(len(line) for line in lines) + 4
    print()
    print(cl("╔" + "═" * width + "╗", "96"))
    for line in lines:
        print(cl("║", "96") + "  " + cl(line.ljust(width - 4), "1;97")
              + "  " + cl("║", "96"))
    print(cl("╚" + "═" * width + "╝", "96"))
    print()


def _menu_row(number, label, value=""):
    color = "96" if str(number) == "0" else "95"
    print(f"  {cl(str(number).rjust(2), color)}. {label:<25}{value}")


def _menu_on_off(value):
    return cl("On", "92") if value else cl("Off", "91")


def _menu_commit(cfg, changes):
    saved = normalize_config({**cfg, **changes})
    if save_config(saved) is False:
        return None
    return saved


def _menu_int(prompt, current, minimum=0):
    value = inp(prompt, current).strip()
    if value.upper() == "B":
        return current
    try:
        number = int(value)
        if number < minimum:
            raise ValueError
        return number
    except (TypeError, ValueError, OverflowError):
        print(cl(f"  Enter a whole number of at least {minimum}.", "91"))
        return current


def _menu_percent(prompt, current, minimum=1.0):
    import math
    value = inp(prompt, current).strip()
    if value.upper() == "B":
        return current
    try:
        number = float(value)
        if not math.isfinite(number) or not minimum <= number <= 100.0:
            raise ValueError
        return number
    except (TypeError, ValueError, OverflowError):
        print(cl(f"  Enter a percentage from {minimum:g} to 100.", "91"))
        return current


def _menu_yes_no(prompt, current):
    while True:
        value = inp(prompt + " (y/n, B=back)", "y" if current else "n").strip().lower()
        if value == "b":
            return None
        if value in ("y", "yes", "on", "1"):
            return True
        if value in ("n", "no", "off", "0"):
            return False
        print(cl("  Enter y or n, or B to go back.", "91"))


def _menu_duration(current, minimum, default_unit="m"):
    import math
    factors = {"s": 1, "m": 60, "h": 3600}
    names = {"s": "seconds", "m": "minutes", "h": "hours"}
    aliases = {"seconds": "s", "minutes": "m", "hours": "h"}
    while True:
        unit = inp("Unit: seconds (s), minutes (m), hours (h), B=back",
                   default_unit).strip().lower()
        if unit == "b":
            return None
        unit = aliases.get(unit, unit)
        if unit in factors:
            break
        print(cl("  Choose s, m, or h.", "91"))
    default = f"{current / factors[unit]:g}"
    while True:
        value = inp("Every X " + names[unit] + " (B=back)", default).strip()
        if value.upper() == "B":
            return None
        try:
            seconds = float(value) * factors[unit]
            if not math.isfinite(seconds) or seconds < minimum:
                raise ValueError
            return int(seconds)
        except (TypeError, ValueError, OverflowError):
            print(cl(f"  Enter a finite interval of at least {minimum} seconds.", "91"))


def _menu_valid_webhook_url(value):
    import re
    from urllib.parse import urlsplit
    try:
        if not isinstance(value, str) or not value or any(c.isspace() for c in value):
            return False
        parsed = urlsplit(value)
        return (value.startswith("https://discord.com/api/webhooks/")
                and parsed.scheme == "https" and parsed.netloc == "discord.com"
                and not parsed.fragment
                and re.fullmatch(r"/api/webhooks/[0-9]+/[A-Za-z0-9_-]+", parsed.path) is not None)
    except (ValueError, TypeError):
        return False


def webhook_menu(cfg):
    draft = {key: cfg.get(key, DEFAULT_CFG[key])
             for key in ("webhook_enabled", "webhook_url", "webhook_interval")}
    while True:
        banner()
        print(cl("  Webhook", "96;1"))
        print(f"  Current: {_menu_on_off(draft['webhook_enabled'])}")
        print()
        print(f"  {cl('1', '92')}. On")
        print(f"  {cl('2', '91')}. Off")
        print(f"  {cl('B', '96')}. Back without saving")
        print()
        choice = inp("Choose On or Off", "1" if draft["webhook_enabled"] else "2").strip().lower()
        if choice == "b":
            return cfg
        if choice in ("1", "on", "y", "yes"):
            draft["webhook_enabled"] = True
        elif choice in ("2", "off", "n", "no"):
            draft["webhook_enabled"] = False
        else:
            print(cl("  Choose 1 for On, 2 for Off, or B to go back.", "91"))
            continue

        if draft["webhook_enabled"]:
            while True:
                prompt = "Discord webhook URL (Enter keeps saved URL, B=back)" if draft["webhook_url"] else "Discord webhook URL (B=back)"
                value = inp(prompt).strip()
                if value.upper() == "B":
                    return cfg
                candidate = value or draft["webhook_url"]
                if _menu_valid_webhook_url(candidate):
                    draft["webhook_url"] = candidate
                    break
                print(cl("  Use https://discord.com/api/webhooks/ID/TOKEN.", "91"))
            interval = _menu_duration(draft["webhook_interval"], 10)
            if interval is None:
                return cfg
            draft["webhook_interval"] = interval

        print()
        print(f"  Webhook: {_menu_on_off(draft['webhook_enabled'])}")
        if draft["webhook_enabled"]:
            print(cl("  URL: set ✓", "92"))
            print(f"  Interval: {seconds_to_str(draft['webhook_interval'])}")
        print(f"  {cl('S', '92')}. Save")
        print(f"  {cl('E', '93')}. Edit")
        print(f"  {cl('B', '96')}. Cancel without saving")
        while True:
            action = inp("S to save, E to edit, or B to cancel").strip().upper()
            if action == "S":
                saved = _menu_commit(cfg, draft)
                if saved is not None:
                    return saved
                print(cl("  Save failed. Retry S, edit with E, or cancel with B.", "91"))
                continue
            if action == "B":
                return cfg
            if action == "E":
                break
            print(cl("  Choose S, E, or B.", "91"))


def config_menu(cfg):
    draft = {key: cfg.get(key, DEFAULT_CFG[key])
             for key in ("cpu_limit", "ram_limit", "overload_confirm")}
    save_error = False
    while True:
        banner()
        print(cl("  Config", "96;1"))
        if save_error:
            print(cl("  Save failed. Retry S, or cancel with B.", "91"))
        print()
        _menu_row(1, "CPU limit (overload)", cl(f"{draft['cpu_limit']:g}%", "93"))
        _menu_row(2, "RAM limit", cl(f"{draft['ram_limit']:g}%", "93"))
        _menu_row(3, "Overload confirm checks", cl(str(draft["overload_confirm"]), "93"))
        print()
        print(f"  {cl('S', '92')}. Save")
        print(f"  {cl('B', '96')}. Cancel without saving")
        print()
        choice = inp("Edit number, S to save, or B to cancel").strip().upper()
        if choice == "B":
            return cfg
        if choice == "S":
            saved = _menu_commit(cfg, draft)
            if saved is not None:
                return saved
            save_error = True
            continue
        if choice == "1":
            draft["cpu_limit"] = _menu_percent("CPU limit % (50–100)", draft["cpu_limit"], 50.0)
        elif choice == "2":
            draft["ram_limit"] = _menu_percent("RAM limit % (1–100)", draft["ram_limit"], 1.0)
        elif choice == "3":
            draft["overload_confirm"] = _menu_int("Overload confirm checks", draft["overload_confirm"], 1)


def settings_menu(cfg):
    cfg = normalize_config(cfg)
    save_error = False
    while True:
        banner()
        if save_error:
            print(cl("  Settings could not be saved. Rejoin has not started.", "91"))
            print()
        restart = seconds_to_str(cfg["restart_seconds"]) if cfg["auto_restart"] else "Off"
        webhook = (_menu_on_off(True) + " · every " + seconds_to_str(cfg["webhook_interval"])
                   if cfg["webhook_enabled"] else _menu_on_off(False))
        packages = cfg.get("packages") or [ROBLOX_PKG]
        _menu_row(0, "Select Game", cl(cfg.get("place_id") or "Not set", "93"))
        _menu_row(1, "Check interval", cl(seconds_to_str(cfg["check_interval"]), "93"))
        _menu_row(2, "Rejoin cooldown", cl(seconds_to_str(cfg["rejoin_cooldown"]), "93"))
        _menu_row(3, "Crash confirm checks", cl(str(cfg["crash_confirm"]), "93") + " checks")
        _menu_row(4, "Auto restart", cl(restart, "93"))
        _menu_row(5, "Webhook", webhook)
        _menu_row(6, "Instances", cl(str(len(packages)), "93") + "  " + cl(", ".join(packages)[:24], "2"))
        _menu_row(7, "Launch gap", cl(seconds_to_str(cfg.get("launch_stagger", 15)), "93"))
        _menu_row(8, "Lobby CPU limit", cl(f"{cfg.get('lobby_cpu', 4.0):g}%", "93"))
        _menu_row(9, "Sequential join", _menu_on_off(cfg.get("seq_join", True)) + f"  gap {cfg.get('seq_gap', 5)}s")
        _menu_row(10, "Heartbeat (executor)", _menu_on_off(cfg.get("heartbeat")) + f"  timeout {cfg.get('hb_timeout', 45)}s")
        _menu_row(11, "Heartbeat account names", cl(",".join(cfg.get("hb_ids") or []) or "auto", "2"))
        _menu_row(12, "Lobby idle checks", cl(str(cfg.get("lobby_idle_count", 4)), "93") + " checks")
        _menu_row(13, "Lobby idle wait", cl(seconds_to_str(cfg.get("lobby_idle_wait", 30)), "93"))
        _menu_row(14, "Config", cl("CPU / RAM / overload", "2"))
        _menu_row(15, "Auto sort on launch", _menu_on_off(cfg.get("auto_sort")))
        print()
        print(f"  {cl('S', '92')}. Save & Start")
        print(f"  {cl('R', '93')}. Reset to defaults")
        print()
        choice = inp("Edit number or S to start").strip().upper()
        if choice == "S":
            if not cfg.get("place_id"):
                print(cl("  No game selected — choose option 0 first.", "91"))
                time.sleep(1)
                continue
            saved = normalize_config(cfg)
            if save_config(saved) is False:
                save_error = True
                continue
            cfg = saved
            print(cl("\n  ✓ Config saved!", "92"))
            time.sleep(0.5)
            return cfg
        if choice == "R":
            cfg = normalize_config({**DEFAULT_CFG, "place_id": cfg.get("place_id", ""),
                                    "packages": packages})
        elif choice == "0":
            cfg["place_id"], _ = pick_game(load_games(), cfg)
        elif choice == "1":
            cfg["check_interval"] = _menu_int("Check interval (seconds)", cfg["check_interval"], 1)
        elif choice == "2":
            cfg["rejoin_cooldown"] = _menu_int("Rejoin cooldown (seconds)", cfg["rejoin_cooldown"], 5)
        elif choice == "3":
            cfg["crash_confirm"] = _menu_int("Crash confirm checks", cfg["crash_confirm"], 1)
        elif choice == "4":
            enabled = _menu_yes_no("Enable auto restart?", cfg["auto_restart"])
            if enabled is False:
                cfg["auto_restart"] = False
            elif enabled is True:
                seconds = _menu_duration(cfg["restart_seconds"], 1, "h")
                if seconds is not None:
                    cfg.update(auto_restart=True, restart_seconds=seconds)
        elif choice == "5":
            cfg = webhook_menu(cfg)
        elif choice == "6":
            cfg = instances_menu(cfg)
        elif choice == "7":
            cfg["launch_stagger"] = _menu_int("Seconds between launching each instance", cfg.get("launch_stagger", 15), 0)
        elif choice == "8":
            cfg["lobby_cpu"] = _menu_percent("Lobby CPU limit % (below this = stuck on lobby)", cfg.get("lobby_cpu", 4.0), 0.5)
        elif choice == "9":
            enabled = _menu_yes_no("Sequential join?", cfg.get("seq_join", True))
            if enabled is not None:
                cfg["seq_join"] = enabled
                if enabled:
                    cfg["seq_gap"] = _menu_int("Seconds to wait after one is in-game", cfg.get("seq_gap", 5), 0)
        elif choice == "10":
            enabled = _menu_yes_no("Use executor heartbeat?", cfg.get("heartbeat", False))
            if enabled is not None:
                cfg["heartbeat"] = enabled
                if enabled:
                    cfg["hb_timeout"] = _menu_int("Rejoin if no heartbeat for (seconds)", cfg.get("hb_timeout", 45), 15)
        elif choice == "11":
            print(cl("  Usernames in instance order, e.g. acc1,acc2. Use auto to clear.", "2"))
            value = inp("Names", ",".join(cfg.get("hb_ids") or []) or "auto")
            cfg["hb_ids"] = [] if value.lower() == "auto" else [name.strip() for name in value.split(",") if name.strip()]
        elif choice == "12":
            cfg["lobby_idle_count"] = _menu_int("Lobby idle checks before rejoin", cfg.get("lobby_idle_count", 4), 1)
        elif choice == "13":
            cfg["lobby_idle_wait"] = _menu_int("Lobby idle wait seconds", cfg.get("lobby_idle_wait", 30), 10)
        elif choice == "14":
            cfg = config_menu(cfg)
        elif choice == "15":
            cfg["auto_sort"] = not cfg.get("auto_sort", False)

DEFAULT_CFG={
    "place_id":"",
    "check_interval":5,
    "rejoin_cooldown":25,
    "crash_confirm":3,
    "ram_limit":90.0,
    "auto_restart":True,
    "restart_seconds":7200,
    "watch_flag":True,
    "webhook_url":"",
    "webhook_interval":60,
    "webhook_enabled":False,
    "packages":["com.roblox.client"],
    "launch_stagger":15,
    "lobby_cpu":4.0,
    "seq_join":True,
    "seq_gap":5,
    "seq_timeout":150,
    "heartbeat":False,
    "hb_timeout":45,
    "hb_grace":30,
    "hb_ids":[],
    "lobby_idle_count":4,
    "lobby_idle_wait":30,
    "cpu_limit":85.0,
    "overload_confirm":3,
    "auto_sort":False,
}

def normalize_config(cfg):
    """Keep saved settings while retiring delay and making flag watching fixed."""
    import copy
    normalized = copy.deepcopy(DEFAULT_CFG)
    if isinstance(cfg, dict):
        normalized.update(copy.deepcopy(cfg))
    normalized.pop("crash_delay", None)
    normalized["watch_flag"] = True
    return normalized


def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE) as handle:
                return normalize_config(json.load(handle))
    except (OSError, ValueError, TypeError):
        pass
    return normalize_config({})


def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w") as handle:
            json.dump(normalize_config(cfg), handle, indent=2)
        return True
    except Exception as exc:
        log(f"Could not save config: {exc}", "WARN")
        return False


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
        print(cl("  ── Select Game ──────────────────────────────","96"))
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


# ---- Automatic floating-window layout ----
"""Pure geometry helpers for Android floating windows; no shell/UI side effects."""
import math
import re


_PKG_PATTERN = r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+"
_NUMBER = r"-?\d+(?:\.\d+)?"
_RECT_PATTERNS = (
    re.compile(r"\[\s*(%s)\s*,\s*(%s)\s*\]\s*\[\s*(%s)\s*,\s*(%s)\s*\]" % ((_NUMBER,) * 4)),
    re.compile(r"Rect\(\s*(%s)\s*,\s*(%s)\s*-\s*(%s)\s*,\s*(%s)\s*\)" % ((_NUMBER,) * 4)),
    re.compile(r"\(\s*(%s)\s*,\s*(%s)\s*\)\s*-\s*\(\s*(%s)\s*,\s*(%s)\s*\)" % ((_NUMBER,) * 4)),
)
_WINDOW_HEADER = re.compile(
    r"(?m)^(?P<indent>[ \t]*)Window[ \t]+#(?P<z>\d+)[ \t]+"
    r"Window\{(?P<token>[^\s}]+)[ \t]+u\d+[ \t]+(?P<title>[^}\r\n]*)\}[^\r\n]*$"
)
_WINDOW_TYPES = {"BASE_APPLICATION": 1, "APPLICATION": 2,
                 "APPLICATION_STARTING": 3, "WALLPAPER": 2013}


def _indent_width(line):
    return len(line[:len(line) - len(line.lstrip(" \t"))].expandtabs(8))


def iter_window_blocks(text):
    """Yield scoped dictionaries with header, title, body, token, and z.

    A window's fields are indented further than its numbered header. Stop at
    the next numbered header or a nonblank line that returns to the header's
    indentation. In particular, global focus/input/insets footers do not belong
    to the final window. Blank lines and deeper attribute continuations remain.
    """
    headers = list(_WINDOW_HEADER.finditer(text))
    for index, match in enumerate(headers):
        stop = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        body = text[match.end():stop]
        offset = 0
        header_indent = _indent_width(match.group("indent"))
        for line in body.splitlines(keepends=True):
            if line.strip() and _indent_width(line) <= header_indent:
                body = body[:offset]
                break
            offset += len(line)
        yield {"header": match.group(0).strip(), "title": match.group("title"),
               "body": body, "token": match.group("token"),
               "z": int(match.group("z"))}


def _read_rect(text):
    """Read a rectangle at the beginning of a field value, not a later field."""
    for pattern in _RECT_PATTERNS:
        match = pattern.match(text.lstrip())
        if match:
            rect = tuple(int(round(float(v))) for v in match.groups())
            return rect if rect[2] > rect[0] and rect[3] > rect[1] else None
    return None


def _field_rect(text, field):
    match = re.search(r"(?<![\w])" + re.escape(field) + r"\s*=\s*", text)
    return (bool(match), _read_rect(text[match.end():]) if match else None)


def _window_attrs(block):
    """Return only mAttrs, including wrapped fields, never following state."""
    match = re.search(r"\bmAttrs\s*=\s*", block)
    if not match:
        return ""
    attrs = block[match.end():]
    first_line = attrs.split("\n", 1)[0]
    opening = first_line.find("{")
    if opening < 0:
        return first_line
    depth = 0
    for index in range(opening, len(attrs)):
        if attrs[index] == "{":
            depth += 1
        elif attrs[index] == "}":
            depth -= 1
            if depth == 0:
                return attrs[:index + 1]
        elif attrs[index] == "\n":
            # Handle truncated/vendor dumps without accepting another object's
            # type= or flags as this window's LayoutParams.
            following = attrs[index + 1:].split("\n", 1)[0].lstrip()
            if re.match(r"(?:m[A-Z]\w*|is[A-Z]\w*|Frames|Surface|"
                        r"WindowStateAnimator|InsetsState)\b", following):
                return attrs[:index]
    return attrs


def _window_type(block):
    match = re.search(r"\b(?:ty|type)\s*=\s*([A-Za-z_]+|0x[0-9a-fA-F]+|\d+)",
                      _window_attrs(block))
    if not match:
        return None
    value = match.group(1)
    if value.startswith("TYPE_"):
        value = value[5:]
    try:
        return int(value, 16 if value.lower().startswith("0x") else 10)
    except ValueError:
        return _WINDOW_TYPES.get(value, value)


def _owner_fields(block):
    """Read ownership fields at the window's field indentation, not children."""
    lines = [line for line in block.splitlines() if line.strip()]
    if not lines:
        return ""
    indentation = _indent_width(lines[0])
    return "\n".join(line for line in lines if _indent_width(line) == indentation)


def _resolve_window_owner(item, owner_uid_packages=None):
    fields = _owner_fields(item["body"])
    owners = re.findall(r"(?:^|[ \t])package\s*=\s*([^\s},]+)", fields)
    owners = list(dict.fromkeys(owners))
    uid_values = set(re.findall(r"\bmOwnerUid\s*=\s*(\d+)\b", fields))
    uid = int(next(iter(uid_values))) if len(uid_values) == 1 else None
    if owners:
        # Explicit WindowState ownership takes priority even when the title or
        # UID map suggests a selected clone. Malformed/conflicting owners fail
        # closed instead of being reassigned through the UID fallback.
        if len(owners) == 1 and re.fullmatch(_PKG_PATTERN, owners[0]):
            return owners[0], uid, "package", None
        return None, uid, "package", "explicit_owner_ambiguous"
    component = re.search(r"\b(" + _PKG_PATTERN + r")/[^\s]+", item["title"])
    if component:
        return component.group(1), uid, "component", None
    if uid is None:
        return None, None, None, "owner_uid_missing_or_ambiguous"
    if owner_uid_packages is None:
        return None, uid, None, "uid_map_unavailable"
    candidates = set()
    for key in (uid, str(uid)):
        if key not in owner_uid_packages:
            continue
        value = owner_uid_packages[key]
        values = [value] if isinstance(value, str) else value
        if not isinstance(values, (list, tuple, set, frozenset)):
            return None, uid, None, "uid_map_invalid"
        for package in values:
            if not isinstance(package, str) or not re.fullmatch(_PKG_PATTERN, package):
                return None, uid, None, "uid_map_invalid"
            candidates.add(package)
    if len(candidates) == 1:
        return next(iter(candidates)), uid, "owner_uid", None
    return None, uid, None, "uid_shared" if candidates else "uid_unmapped"


def _visible_window(block):
    # Surface existence alone does not mean a window can be seen/touched.
    if re.search(r"\b(?:mHasSurface|isReadyForDisplay\(\)|isOnScreen|isVisible|"
                 r"mPolicyVisibility|mAppOpVisibility)\s*=\s*false\b", block):
        return False
    if re.search(r"\b(?:mRemoved|mDestroying|mAppDied|mAnimatingExit|mAttachedHidden|"
                 r"mPermanentlyHidden|mHidden)\s*=\s*true\b", block):
        return False
    view = re.search(r"\bmViewVisibility\s*=\s*(0x[0-9a-fA-F]+|\d+)", block)
    if view and int(view.group(1), 0) != 0:
        return False
    has_surface = bool(re.search(r"\bmHasSurface\s*=\s*true\b", block))
    ready = bool(re.search(r"\b(?:isReadyForDisplay\(\)|isOnScreen|isVisible)\s*=\s*true\b", block))
    return (has_surface and (bool(view) or ready)) or ready


def _touchable_window(block, kind):
    attrs = _window_attrs(block)
    if kind == 2013 or re.search(r"\b(?:FLAG_)?NOT_TOUCHABLE\b", attrs):
        return False
    flags = re.search(r"\bfl\s*=\s*(?:#|0x)([0-9a-fA-F]+)\b", attrs)
    return not (flags and int(flags.group(1), 16) & 0x10)


def _focusable_window(block):
    attrs = _window_attrs(block)
    if re.search(r"\b(?:FLAG_)?NOT_FOCUSABLE\b", attrs):
        return False
    flags = re.search(r"\bfl\s*=\s*(?:#|0x)([0-9a-fA-F]+)\b", attrs)
    return not (flags and int(flags.group(1), 16) & 0x8)


def _activity_window_token(block):
    # The four floating-window controls and the game surface share this
    # activity identity even though each has a different WindowState token.
    # Only read the window's own fields; nested child/global tokens are not
    # evidence that two surfaces belong to the same activity.
    fields = _owner_fields(block)
    values = set(re.findall(
        r"(?:^|[ \t])(?:mAppToken|mToken)\s*=\s*AppWindowToken\{([^\s{}]+)",
        fields, re.M))
    return next(iter(values)) if len(values) == 1 else None


def _inspect_window(item, selected, owner_uid_packages):
    block = item["body"]
    package, uid, owner_source, owner_error = _resolve_window_owner(item, owner_uid_packages)
    kind = _window_type(block)
    visible = _visible_window(block)
    starting = bool(re.search(r"(?i)\b(?:Starting|Splash Screen|SnapshotStartingWindow)\b",
                              item["title"]))
    present, rect = _field_rect(block, "mFrame")
    source = "mFrame"
    if not present:
        group = re.search(r"\b(?:Frames:|mWindowFrames\b)", block)
        present, rect = _field_rect(block[group.start():], "frame") if group else (False, None)
        source = "frame"
    if not present:
        present, rect = _field_rect(block, "mShownFrame")
        source = "mShownFrame"
    # Empty/malformed actual frames must not fall back to stale shown frames.
    display = re.search(r"\bmDisplayId\s*=\s*(\d+)\b", block)
    rejections = []
    if package is None:
        rejections.append(owner_error or "owner_unknown")
    elif selected is not None and package not in selected:
        rejections.append("not_selected")
    if kind != 1:
        rejections.append("window_type_missing" if kind is None else "not_base_application")
    if starting:
        rejections.append("starting_or_splash")
    if not visible:
        rejections.append("not_visible")
    if rect is None:
        rejections.append("frame_invalid" if present else "frame_missing")
    if display is None:
        rejections.append("display_missing")
    component = re.search(r"\b(" + _PKG_PATTERN + r"/[^\s]+)", item["title"])
    return {"package": package, "token": item["token"], "bounds": rect,
            "display_id": int(display.group(1)) if display else None, "z": item["z"],
            "type": kind, "touchable": _touchable_window(block, kind),
            "focusable": _focusable_window(block), "app_token": _activity_window_token(block),
            "component": component.group(1) if component else None,
            "frame_source": source if present else None, "owner_uid": uid,
            "ownership_source": owner_source, "visible": visible,
            "eligible": not rejections, "rejections": rejections}


def window_diagnostics(text, selected_packages=None, owner_uid_packages=None):
    """Return per-window geometry/ownership and reasons it is not a layout target.

    Includes unknown and nonselected windows so a custom-title/UID failure is
    visible. Header and bounded geometry/ownership field lines are included;
    unrelated global footer text is excluded. ``eligible`` describes main-window
    identification, not a successful resize.
    """
    selected = None if selected_packages is None else set(selected_packages)
    field_pattern = re.compile(
        r"\b(?:mDisplayId|mOwnerUid|mAppToken|mToken|package|mAttrs|mViewVisibility|mHasSurface|"
        r"isReadyForDisplay|isOnScreen|isVisible|mPolicyVisibility|mAppOpVisibility|"
        r"mRemoved|mDestroying|mAnimatingExit|mAttachedHidden|mPermanentlyHidden|"
        r"mHidden|mObscured|Frames|mWindowFrames|mFrame|mShownFrame|frame|ty|fl)\b")
    result = []
    for item in iter_window_blocks(text):
        info = _inspect_window(item, selected, owner_uid_packages)
        fields = [item["header"]]
        fields.extend(line.strip()[:500] for line in item["body"].splitlines()
                      if field_pattern.search(line))
        info.update(header=item["header"], fields=fields[:24],
                    reason="; ".join(info["rejections"]) or "eligible_main_window")
        result.append(info)
    return result


def parse_window_dump(text, selected_packages=None, include_overlays=False,
                      owner_uid_packages=None):
    """Return visible windows front-to-back (lower ``z`` means above).

    Default mode returns only identified BASE_APPLICATION windows, excluding
    starting/splash surfaces. ``include_overlays=True`` additionally retains
    dialogs and system windows for hit-testing; these are never layout targets.
    Optional ``owner_uid_packages`` is a UID-to-package(s) mapping from the full
    installed package list. It is used only without explicit ownership, and a
    shared UID is never guessed. An explicit WindowState package always wins.
    Requested mAttrs sizes are deliberately not used as actual screen bounds.
    """
    selected = None if selected_packages is None else set(selected_packages)
    windows = []
    for item in iter_window_blocks(text):
        info = _inspect_window(item, selected, owner_uid_packages)
        if include_overlays:
            if (not info["visible"] or info["bounds"] is None or info["display_id"] is None
                    or (selected is not None and info["package"] not in selected)):
                continue
        elif not info["eligible"]:
            continue
        windows.append({key: info[key] for key in
                        ("package", "token", "bounds", "display_id", "z", "type",
                         "touchable", "focusable", "app_token", "component",
                         "frame_source", "owner_uid", "ownership_source")})
    return sorted(windows, key=lambda window: window["z"])


def resolve_clone_windows(windows, selected_packages=None, tolerance=1):
    """Resolve physical BASE_APPLICATION surfaces into logical clone windows.

    Call with the base-window output of parse_window_dump; retain the
    ungrouped overlay output separately for hit-testing. The uploaded APK uses
    one focusable body, four nonfocusable input strips, and a nontouchable
    drawing surface for each floating clone. They share package, owner UID,
    display and AppWindowToken. A complete, geometrically consistent frame is
    required before the strips are accepted as controls.

    bounds and body_bounds remain the actual body rectangle.
    chrome contains the physical header, left, right and bottom windows.
    outer_bounds covers every input strip; resize_margin is their observed
    side/bottom thickness. The APK's visible caption height is independent of
    this margin and must be calculated by the controller from display density.

    A single ordinary focusable window remains usable. Incomplete or ambiguous
    multiwindow frames carry group_error and must not receive gestures.
    Two real bodies remain separate entries; no largest-window heuristic is
    used to choose between them. Nontouchable helper surfaces never become
    bodies, but they remain present in the caller's physical overlay list.
    """
    if not isinstance(tolerance, int) or tolerance < 0:
        raise ValueError("Window-group tolerance must be a nonnegative integer")
    selected = None if selected_packages is None else set(selected_packages)
    groups = {}
    for window in windows:
        package = window.get("package")
        if (window.get("type") != 1 or package is None
                or (selected is not None and package not in selected)
                or window.get("bounds") is None or window.get("display_id") is None):
            continue
        key = (package, window["display_id"], window.get("owner_uid"), window.get("app_token"))
        groups.setdefault(key, []).append(window)

    def close(a, b):
        return abs(a - b) <= tolerance

    def make_logical(body, chrome=None, error=None, unresolved=False):
        chrome = chrome or {}
        logical = dict(body)
        members = [body] + [chrome[role] for role in ("header", "left", "right", "bottom")
                            if role in chrome]
        rects = [w["bounds"] for w in members]
        logical.update(
            body_bounds=None if unresolved else body["bounds"],
            outer_bounds=(min(r[0] for r in rects), min(r[1] for r in rects),
                          max(r[2] for r in rects), max(r[3] for r in rects)),
            chrome=chrome, resize_margin=0,
            member_tokens=[w["token"] for w in members],
            composite=False, group_error=error,
            z=min(w["z"] for w in members))
        return logical

    logical_windows = []
    for (_package, _display, _uid, app_token), members in groups.items():
        bodies = [w for w in members if w.get("touchable", True) and w.get("focusable", True)]
        helpers = [w for w in members if w.get("touchable", True) and not w.get("focusable", True)]
        hosts = [w for w in members if not w.get("touchable", True)]
        if not bodies:
            # Preserve unresolved touchable candidates as explicit errors rather
            # than picking one strip and pretending it is a body.
            logical_windows.extend(make_logical(w, error="No focusable body is visible for this window group.",
                                                unresolved=True) for w in helpers)
            continue
        if len(bodies) > 1:
            logical_windows.extend(make_logical(
                w, error="More than one focusable body is visible for this activity.")
                for w in bodies)
            continue
        body = bodies[0]
        if not helpers:
            error = ("Floating-window frame is incomplete: no control strips are visible."
                     if hosts else None)
            logical_windows.append(make_logical(body, error=error))
            continue
        if app_token is None:
            logical_windows.append(make_logical(
                body, error="Cannot link the floating-window controls without an activity token."))
            continue

        left, top, right, bottom = body["bounds"]
        matches = {role: [] for role in ("header", "left", "right", "bottom")}
        unmatched = []
        for helper in helpers:
            hl, ht, hr, hb = helper["bounds"]
            roles = []
            if close(hl, left) and close(hr, right):
                if close(hb, top) and ht < top:
                    roles.append("header")
                if close(ht, bottom) and hb > bottom:
                    roles.append("bottom")
            if close(ht, top) and close(hb, bottom):
                if close(hr, left) and hl < left:
                    roles.append("left")
                if close(hl, right) and hr > right:
                    roles.append("right")
            if len(roles) == 1:
                matches[roles[0]].append(helper)
            else:
                unmatched.append(helper)
        chrome = {role: found[0] for role, found in matches.items() if len(found) == 1}
        if unmatched or any(len(found) != 1 for found in matches.values()):
            problems = []
            missing = [role for role, found in matches.items() if not found]
            repeated = [role for role, found in matches.items() if len(found) > 1]
            if missing:
                problems.append("missing " + ", ".join(missing))
            if repeated:
                problems.append("duplicate " + ", ".join(repeated))
            if unmatched:
                problems.append("unmatched controls")
            logical_windows.append(make_logical(
                body, chrome, "Floating-window frame is incomplete or ambiguous: "
                + "; ".join(problems) + "."))
            continue

        # Verified APK geometry: side/bottom input strips each have margin M,
        # while the top strip is 2*M (upper resize area, lower move/caption area).
        margins = sorted((chrome["left"]["bounds"][2] - chrome["left"]["bounds"][0],
                          chrome["right"]["bounds"][2] - chrome["right"]["bounds"][0],
                          chrome["bottom"]["bounds"][3] - chrome["bottom"]["bounds"][1]))
        margin = margins[1]
        header_height = chrome["header"]["bounds"][3] - chrome["header"]["bounds"][1]
        if (margin <= 0 or margins[-1] - margins[0] > tolerance
                or abs(header_height - 2 * margin) > tolerance):
            logical_windows.append(make_logical(
                body, chrome, "Floating-window control sizes do not match the supported frame geometry."))
            continue
        logical = make_logical(body, chrome)
        logical.update(composite=True, resize_margin=margin)
        logical_windows.append(logical)
    return sorted(logical_windows, key=lambda window: window["z"])


def parse_display_geometry(window_displays, wm_size=""):
    """Read default-display dimensions and usable bounds in Android pixels.

    Current ``cur=`` / DisplayFrames dimensions take precedence over natural
    ``wm size`` dimensions. A reported rotation is applied only to wm size.
    Stable/content/restricted frames are used if available; otherwise bounds
    cover the whole display, marked by bounds_source='full_display'.
    """
    text = window_displays
    starts = list(re.finditer(r"(?m)^\s*Display:\s*mDisplayId=(\d+)\b", text))
    if starts:
        display_zero = next((i for i, m in enumerate(starts) if m.group(1) == "0"), None)
        if display_zero is None:
            text = ""
        else:
            start = starts[display_zero].start()
            end = starts[display_zero + 1].start() if display_zero + 1 < len(starts) else len(text)
            text = text[start:end]
    width = height = None
    dimension_patterns = (
        ("cur", r"\bcur=(\d+)x(\d+)\b"),
        ("DisplayFrames", r"\bDisplayFrames\b[^\n]*\bw=(\d+)\s+h=(\d+)\b"),
        ("logical", r"\blogicalWidth=(\d+)\b[^\n]*\blogicalHeight=(\d+)\b"),
        ("DisplayInfo", r"\bDisplayInfo\b[^\n]*?\breal\s+(\d+)\s*x\s*(\d+)\b"),
    )
    source = None
    for label, pattern in dimension_patterns:
        match = re.search(pattern, text)
        if match:
            width, height = map(int, match.groups())
            source = label
            break
    if width is None:
        size = re.search(r"Override size:\s*(\d+)x(\d+)", wm_size)
        size = size or re.search(r"Physical size:\s*(\d+)x(\d+)", wm_size)
        if size:
            width, height = map(int, size.groups())
            source = "wm_size"
            rotation = re.search(r"\b(?:mRotation|rotation)\s*[=:]?\s*(?:ROTATION_)?(270|180|90|[0-3])\b", text)
            if rotation and int(rotation.group(1)) in (1, 3, 90, 270):
                width, height = height, width
    if not width or not height or width < 1 or height < 1:
        raise ValueError("Cannot determine Android display 0 dimensions")
    bounds, bounds_source = (0, 0, width, height), "full_display"
    for field in ("mStable", "mContent", "mRestricted"):
        present, candidate = _field_rect(text, field)
        if present and candidate:
            clipped = (max(0, candidate[0]), max(0, candidate[1]),
                       min(width, candidate[2]), min(height, candidate[3]))
            if clipped[2] > clipped[0] and clipped[3] > clipped[1]:
                bounds, bounds_source = clipped, field
                break
    geometry = {"width": width, "height": height, "bounds": bounds, "display_id": 0,
                "source": source, "bounds_source": bounds_source}
    # Current logical/base density can differ from the natural display's init
    # density (the uploaded report has init=320dpi, base/current=192dpi).
    # Do not use an arbitrary "...dpi" match from an activity configuration or
    # a physical x/y DPI pair to determine dimensions of the custom controls.
    density_patterns = (
        ("mBaseDisplayDensity", r"(?m)^[ \t]*mBaseDisplayDensity\s*=\s*(\d+)\b"),
        ("DisplayInfo.logicalDensityDpi",
         r"(?m)^[ \t]*(?:mDisplayInfo\s*=\s*)?DisplayInfo\b[^\n]*?\blogicalDensityDpi\s*=\s*(\d+)\b"),
        ("DisplayInfo.density",
         r"(?m)^[ \t]*(?:mDisplayInfo\s*=\s*)?DisplayInfo\b[^\n]*?\bdensity\s+(\d+)\b"),
        ("base", r"\bbase=\d+x\d+[ \t]+(\d+)dpi\b"),
        ("logicalDensityDpi", r"(?m)^[ \t]*logicalDensityDpi\s*=\s*(\d+)\b"),
    )
    for density_source, pattern in density_patterns:
        match = re.search(pattern, text)
        if match and int(match.group(1)) > 0:
            geometry.update(density_dpi=int(match.group(1)), density_source=density_source)
            break
    return geometry


def plan_grid(packages, bounds, min_width=1, min_height=1):
    """Return an automatic grid, preserving package slot order.

    The familiar near-square shape is preserved whenever its cells meet the
    minimum visible dimensions. If it cannot fit, choose a feasible shape with
    the fewest unused cells, then the smallest change from the preferred shape.
    No per-count layouts or user-maintained presets are involved.
    """
    ordered = list(dict.fromkeys(packages))
    if len(bounds) != 4 or any(not isinstance(v, int) for v in bounds):
        raise ValueError("Grid bounds must contain four integer coordinates")
    if any(not isinstance(v, int) or v < 1 for v in (min_width, min_height)):
        raise ValueError("Minimum grid dimensions must be positive integers")
    left, top, right, bottom = bounds
    width, height = right - left, bottom - top
    if width <= 0 or height <= 0:
        raise ValueError("Grid bounds must have positive width and height")
    if not ordered:
        return {"columns": 0, "rows": 0, "slots": {}}
    columns = math.isqrt(len(ordered) - 1) + 1
    rows = (len(ordered) + columns - 1) // columns
    if height > width:
        columns, rows = rows, columns
    if width // columns < min_width or height // rows < min_height:
        preferred_columns, preferred_rows = columns, rows
        feasible = []
        for candidate_columns in range(1, len(ordered) + 1):
            candidate_rows = (len(ordered) + candidate_columns - 1) // candidate_columns
            if (width // candidate_columns >= min_width
                    and height // candidate_rows >= min_height):
                feasible.append((candidate_columns, candidate_rows))
        if not feasible:
            raise ValueError(
                f"{len(ordered)} clone windows cannot fit within {width}x{height} pixels "
                f"at the minimum window size {min_width}x{min_height}.")
        columns, rows = min(feasible, key=lambda shape: (
            shape[0] * shape[1] - len(ordered),
            abs(shape[0] - preferred_columns) + abs(shape[1] - preferred_rows),
            abs(shape[0] - shape[1]), shape[0]))
    slots = {}
    for index, package in enumerate(ordered):
        column, row = index % columns, index // columns
        slots[package] = (left + width * column // columns, top + height * row // rows,
                          left + width * (column + 1) // columns, top + height * (row + 1) // rows)
    return {"columns": columns, "rows": rows, "slots": slots}

_SORT_PREFS_HELPER = '"""Prepare only AppCloner window bounds in a stopped clone\'s preferences.\n\nThis module is embedded in the single-file rejoin script and executed with the\nphone\'s existing Python interpreter under root. Its output never contains XML.\n"""\nimport errno\nfrom contextlib import contextmanager\nimport json\nimport os\nimport re\nimport signal\nimport stat\nimport sys\nimport xml.etree.ElementTree as ET\n\n\nKEYS = tuple("app_cloner_current_window_" + edge\n             for edge in ("left", "top", "right", "bottom"))\nMAX_FILE_BYTES = 4 * 1024 * 1024\nMAX_TOTAL_BYTES = 16 * 1024 * 1024\n_PACKAGE = re.compile(r"[A-Za-z][A-Za-z0-9_]*(?:\\.[A-Za-z0-9_]+)+\\Z")\n_STAGES = frozenset(("request", "root_identity", "app_directory", "process_status",\n                     "process_cmdline", "preference_scan", "xattrs", "chown",\n                     "publish", "verify"))\n_VALUE_REASONS = frozenset(("invalid_body", "unsupported_preference_xml",\n                            "malformed_preference_xml", "missing_or_duplicate_window_key",\n                            "invalid_window_integer", "unsupported_window_key_encoding"))\n_EXCEPTION_TYPES = {kind: kind.__name__ for kind in (\n    Exception, AttributeError, TypeError, NotImplementedError, ImportError,\n    ModuleNotFoundError, RuntimeError, ValueError, OverflowError, UnicodeError,\n    UnicodeDecodeError, UnicodeEncodeError, LookupError, KeyError, IndexError,\n    MemoryError, BufferError, OSError, PermissionError, FileNotFoundError,\n    FileExistsError, NotADirectoryError, IsADirectoryError, InterruptedError,\n    TimeoutError, BlockingIOError, ProcessLookupError)}\n_XATTR_FUNCTIONS = ("listxattr", "getxattr", "setxattr", "removexattr")\n_MAX_XATTR_BYTES = 65536\n_MAX_XATTR_NAME_BYTES = 255\n_XATTR_READ_ATTEMPTS = 3\n\n\ndef _diagnostics(stage=None, errno=None, pid=None, checked=None, exception_type=None):\n    safe = {"stage": stage} if stage in _STAGES else {}\n    for key, value in (("errno", errno), ("pid", pid), ("checked", checked)):\n        if type(value) is int and 0 <= value <= 2147483647:\n            safe[key] = value\n    if exception_type in _EXCEPTION_TYPES.values():\n        safe["exception_type"] = exception_type\n    return safe\n\n\nclass _Skip(ValueError):\n    def __init__(self, reason, **diagnostics):\n        super().__init__(reason)\n        self.diagnostics = _diagnostics(**diagnostics)\n\n\n@contextmanager\ndef _operation(stage):\n    """Attach an operation code and errno, never an exception message/path."""\n    try:\n        yield\n    except _Skip as exc:\n        exc.diagnostics.setdefault("stage", stage)\n        raise\n    except OSError as exc:\n        raise _Skip("preferences_access_unavailable", stage=stage, errno=exc.errno,\n                    exception_type=_EXCEPTION_TYPES.get(type(exc), "Exception")) from None\n    except Exception as exc:\n        reason = str(exc) if isinstance(exc, ValueError) else None\n        raise _Skip(reason if reason in _VALUE_REASONS else "preference_preparation_failed",\n                    stage=stage,\n                    exception_type=_EXCEPTION_TYPES.get(type(exc), "Exception")) from None\n\n\nclass _LibcXattrs:\n    """Android/Linux xattrs on open descriptors, with no path-based fallback."""\n\n    def __init__(self):\n        # Termux intentionally builds Python without its os.*xattr wrappers.\n        # Android\'s libc still exposes the descriptor-based xattr operations.\n        # ctypes is standard-library code; libc enforces the same permissions.\n        import ctypes\n        self.ctypes = ctypes\n        self.libc = ctypes.CDLL(None, use_errno=True)\n        signatures = {\n            "flistxattr": ([ctypes.c_int, ctypes.c_void_p, ctypes.c_size_t], ctypes.c_ssize_t),\n            "fgetxattr": ([ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p,\n                           ctypes.c_size_t], ctypes.c_ssize_t),\n            "fsetxattr": ([ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p,\n                           ctypes.c_size_t, ctypes.c_int], ctypes.c_int),\n            "fremovexattr": ([ctypes.c_int, ctypes.c_char_p], ctypes.c_int),\n        }\n        for name, (arguments, result) in signatures.items():\n            function = getattr(self.libc, name)\n            function.argtypes = arguments\n            function.restype = result\n\n    @staticmethod\n    def _fd(fd):\n        if type(fd) is not int or not 0 <= fd <= 2147483647:\n            raise ValueError("invalid_xattr_descriptor")\n        return fd\n\n    @staticmethod\n    def _name(name):\n        encoded = os.fsencode(name)\n        if not encoded or b"\\0" in encoded or len(encoded) > _MAX_XATTR_NAME_BYTES:\n            raise ValueError("invalid_xattr_name")\n        return encoded\n\n    def _call(self, function, *arguments):\n        self.ctypes.set_errno(0)\n        result = function(*arguments)\n        if result < 0:\n            code = self.ctypes.get_errno() or errno.EIO\n            raise OSError(code, "xattr_system_call_failed")\n        return result\n\n    def _read(self, function, *arguments):\n        for _ in range(_XATTR_READ_ATTEMPTS):\n            try:\n                size = self._call(function, *arguments, None, 0)\n                if size > _MAX_XATTR_BYTES:\n                    raise _Skip("xattr_size_limit", stage="xattrs")\n                # A zero-length value is legal. Use a one-byte read so a value\n                # that grows after the query produces ERANGE and is retried.\n                capacity = max(1, size)\n                buffer = self.ctypes.create_string_buffer(capacity)\n                actual = self._call(function, *arguments, buffer, capacity)\n                if actual > capacity:\n                    raise _Skip("xattr_result_invalid", stage="xattrs")\n                return buffer.raw[:actual]\n            except OSError as exc:\n                if exc.errno != errno.ERANGE:\n                    raise\n        raise OSError(errno.ERANGE, "xattr_changed_during_read")\n\n    def list(self, fd):\n        raw = self._read(self.libc.flistxattr, self._fd(fd))\n        if not raw:\n            return []\n        if not raw.endswith(b"\\0"):\n            raise _Skip("xattr_list_invalid", stage="xattrs")\n        names = raw[:-1].split(b"\\0")\n        if (len(names) != len(set(names))\n                or any(not name or len(name) > _MAX_XATTR_NAME_BYTES for name in names)):\n            raise _Skip("xattr_list_invalid", stage="xattrs")\n        return [os.fsdecode(name) for name in names]\n\n    def get(self, fd, name):\n        return self._read(self.libc.fgetxattr, self._fd(fd), self._name(name))\n\n    def set(self, fd, name, value):\n        if not isinstance(value, bytes) or len(value) > _MAX_XATTR_BYTES:\n            raise _Skip("xattr_size_limit", stage="xattrs")\n        buffer = self.ctypes.create_string_buffer(value, max(1, len(value)))\n        self._call(self.libc.fsetxattr, self._fd(fd), self._name(name),\n                   buffer, len(value), 0)\n\n    def remove(self, fd, name):\n        self._call(self.libc.fremovexattr, self._fd(fd), self._name(name))\n\n\nclass _FdXattrs:\n    """Select one metadata backend per helper invocation; never bypass denials."""\n\n    def __init__(self):\n        self.backend = "unselected"\n        self._libc = None\n\n    def _activate_libc(self):\n        self.backend = "unavailable"\n        self._libc = _LibcXattrs()\n        self.backend = "libc"\n\n    def _call(self, operation, *arguments):\n        if self.backend in ("unselected", "os"):\n            if all(callable(getattr(os, name, None)) for name in _XATTR_FUNCTIONS):\n                self.backend = "os"\n                try:\n                    return getattr(os, operation + "xattr")(*arguments)\n                except (AttributeError, NotImplementedError):\n                    # Only absent/unimplemented wrappers select libc. OSError,\n                    # including permission errors, propagates without retry.\n                    pass\n            self._activate_libc()\n        if self.backend != "libc" or self._libc is None:\n            raise NotImplementedError("xattr_backend_unavailable")\n        return getattr(self._libc, operation)(*arguments)\n\n    def list(self, fd):\n        return self._call("list", fd)\n\n    def get(self, fd, name):\n        return self._call("get", fd, name)\n\n    def set(self, fd, name, value):\n        return self._call("set", fd, name, value)\n\n    def remove(self, fd, name):\n        return self._call("remove", fd, name)\n\n\n_XATTRS = _FdXattrs()\n\n\ndef _runtime_metadata():\n    fd = getattr(os, "supports_fd", ())\n    directory_fd = getattr(os, "supports_dir_fd", ())\n    nofollow = getattr(os, "supports_follow_symlinks", ())\n    capabilities = {"os_" + name: callable(getattr(os, name, None))\n                    for name in _XATTR_FUNCTIONS}\n    capabilities.update(\n        listdir_fd=os.listdir in fd,\n        open_dir_fd=os.open in directory_fd,\n        stat_dir_fd=os.stat in directory_fd,\n        stat_nofollow=os.stat in nofollow,\n        rename_dir_fd=os.rename in directory_fd,\n        unlink_dir_fd=os.unlink in directory_fd)\n    return {"python_version": ".".join(str(part) for part in sys.version_info[:3]),\n            "xattr_backend": _XATTRS.backend, "capabilities": capabilities}\n\n\ndef _validated_body(body):\n    if (not isinstance(body, (list, tuple)) or len(body) != 4\n            or any(type(v) is not int or not 0 <= v <= 2147483647 for v in body)\n            or body[2] <= body[0] or body[3] <= body[1]):\n        raise ValueError("invalid_body")\n    return tuple(body)\n\n\ndef patch_window_preferences(data, body):\n    """Return (patched bytes, old edges), preserving every unrelated byte."""\n    body = _validated_body(body)\n    if (not isinstance(data, bytes) or len(data) > MAX_FILE_BYTES or b"\\0" in data\n            or b"<!DOCTYPE" in data or b"<!ENTITY" in data):\n        raise ValueError("unsupported_preference_xml")\n    try:\n        root = ET.fromstring(data)\n    except ET.ParseError:\n        raise ValueError("malformed_preference_xml") from None\n    if root.tag != "map":\n        raise ValueError("unsupported_preference_xml")\n    entries = {key: [] for key in KEYS}\n    for child in root:\n        if child.get("name") in entries:\n            entries[child.get("name")].append(child)\n    old = []\n    for key in KEYS:\n        matches = entries[key]\n        if len(matches) != 1:\n            raise ValueError("missing_or_duplicate_window_key")\n        node = matches[0]\n        value = node.get("value", "")\n        if (node.tag != "int" or len(node) or (node.text and node.text.strip())\n                or not re.fullmatch(r"[+-]?\\d+", value)\n                or not -2147483648 <= int(value) <= 2147483647):\n            raise ValueError("invalid_window_integer")\n        old.append(int(value))\n    # Mask non-element text while retaining byte offsets into the original.\n    masked = re.sub(rb"<!--.*?-->|<!\\[CDATA\\[.*?\\]\\]>|<\\?.*?\\?>",\n                    lambda match: b" " * len(match.group()), data, flags=re.S)\n    replacements = {}\n    for tag in re.finditer(rb"<int\\b[^<>]*>", masked):\n        name = re.search(rb"(?:^|\\s)name\\s*=\\s*([\'\\"])(.*?)\\1", tag.group(), re.S)\n        if name is None or name.group(2) not in [key.encode() for key in KEYS]:\n            continue\n        key = name.group(2).decode("ascii")\n        value = re.search(rb"(?:^|\\s)value\\s*=\\s*([\'\\"])([+-]?\\d+)\\1", tag.group())\n        if value is None or key in replacements:\n            raise ValueError("unsupported_window_key_encoding")\n        index = KEYS.index(key)\n        if int(value.group(2)) != old[index]:\n            raise ValueError("unsupported_window_key_encoding")\n        replacements[key] = (tag.start() + value.start(2), tag.start() + value.end(2),\n                             str(body[index]).encode("ascii"))\n    if len(replacements) != 4:\n        raise ValueError("unsupported_window_key_encoding")\n    old = tuple(old)\n    if old == body:\n        return data, old\n    for start, end, value in sorted(replacements.values(), reverse=True):\n        data = data[:start] + value + data[end:]\n    return data, old\n\n\ndef _signature(info):\n    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,\n            info.st_ctime_ns, info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode))\n\n\ndef _attributes(fd):\n    with _operation("xattrs"):\n        try:\n            names = _XATTRS.list(fd)\n        except OSError as exc:\n            if exc.errno in (errno.ENOTSUP, errno.EOPNOTSUPP):\n                return {}\n            raise\n        return {name: _XATTRS.get(fd, name) for name in names}\n\n\ndef _file_state(directory, name):\n    try:\n        return _signature(os.stat(name, dir_fd=directory, follow_symlinks=False))\n    except FileNotFoundError:\n        return None\n\n\ndef _read_file(directory, name, uid):\n    before = os.stat(name, dir_fd=directory, follow_symlinks=False)\n    if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1\n            or before.st_uid != uid or before.st_size > MAX_FILE_BYTES):\n        raise _Skip("unsafe_preference_file")\n    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC\n    fd = os.open(name, flags, dir_fd=directory)\n    try:\n        if _signature(os.fstat(fd)) != _signature(before):\n            raise _Skip("preferences_changed")\n        chunks, size = [], 0\n        while True:\n            chunk = os.read(fd, min(65536, MAX_FILE_BYTES + 1 - size))\n            if not chunk:\n                break\n            chunks.append(chunk)\n            size += len(chunk)\n            if size > MAX_FILE_BYTES:\n                raise _Skip("preference_file_too_large")\n        if _signature(os.fstat(fd)) != _signature(before):\n            raise _Skip("preferences_changed")\n        return b"".join(chunks), before, _attributes(fd)\n    finally:\n        os.close(fd)\n\n\ndef _process_state(package, uid, proc_root, diagnostics=None):\n    """None means a complete fresh scan found no matching UID/process."""\n    inspected = 0\n\n    def finish(reason, stage="process_status", pid=None, error=None, checked=None):\n        if diagnostics is not None:\n            diagnostics.clear()\n            diagnostics.update(_diagnostics(\n                stage, errno=error, pid=pid, checked=inspected if checked is None else checked))\n        return reason\n\n    try:\n        names = os.listdir(proc_root)\n        for name in names:\n            if not name.isdecimal():\n                continue\n            folder = os.path.join(proc_root, name)\n            stage = "process_status"\n            try:\n                with open(os.path.join(folder, "status"), "rb") as handle:\n                    status = handle.read(65537)\n                match = re.search(rb"(?m)^Uid:\\s*(\\d+)\\s+(\\d+)\\s+(\\d+)\\s+(\\d+)[ \\t]*$", status)\n                if len(status) > 65536 or match is None:\n                    return finish("process_check_unavailable", stage, int(name))\n                if uid in (int(value) for value in match.groups()):\n                    return finish("already_running", stage, int(name), checked=inspected + 1)\n                stage = "process_cmdline"\n                with open(os.path.join(folder, "cmdline"), "rb") as handle:\n                    command = handle.read(4096).split(b"\\0", 1)[0]\n                encoded = package.encode("ascii")\n                if command == encoded or command.startswith(encoded + b":"):\n                    return finish("already_running", stage, int(name), checked=inspected + 1)\n                inspected += 1\n            except FileNotFoundError:\n                try:\n                    os.stat(folder)\n                except FileNotFoundError:\n                    continue\n                except OSError as exc:\n                    return finish("process_check_unavailable", stage, int(name), exc.errno)\n                return finish("process_check_unavailable", stage, int(name), errno.ENOENT)\n            except OSError as exc:\n                return finish("process_check_unavailable", stage, int(name), exc.errno)\n    except OSError as exc:\n        return finish("process_check_unavailable", error=exc.errno)\n    return finish(None if inspected else "process_check_unavailable")\n\n\ndef _open_app_directory(package, data_roots):\n    found = {}\n    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC\n    try:\n        for parent in data_roots:\n            path = os.path.join(os.path.realpath(os.fspath(parent)), package)\n            try:\n                fd = os.open(path, flags)\n            except FileNotFoundError:\n                continue\n            info = os.fstat(fd)\n            identity = (info.st_dev, info.st_ino)\n            if identity in found:\n                os.close(fd)\n            else:\n                found[identity] = fd\n        if len(found) != 1:\n            raise _Skip("app_data_unavailable" if not found else "app_data_ambiguous")\n        return found.popitem()[1]\n    finally:\n        for fd in found.values():\n            os.close(fd)\n\n\ndef _atomic_replace(directory, name, original, updated, info, attrs, validate):\n    with _operation("publish"):\n        temporary = ".roblox_sort_" + os.urandom(12).hex() + ".tmp"\n        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC\n        fd = os.open(temporary, flags, 0o600, dir_fd=directory)\n        published = False\n        try:\n            remaining = memoryview(updated)\n            while remaining:\n                written = os.write(fd, remaining)\n                if written <= 0:\n                    raise _Skip("preference_write_failed")\n                remaining = remaining[written:]\n            with _operation("chown"):\n                os.fchown(fd, info.st_uid, info.st_gid)\n                os.fchmod(fd, stat.S_IMODE(info.st_mode))\n            with _operation("xattrs"):\n                for key in _attributes(fd):\n                    if key not in attrs:\n                        _XATTRS.remove(fd, key)\n                for key, value in attrs.items():\n                    if _attributes(fd).get(key) != value:\n                        _XATTRS.set(fd, key, value)\n                if _attributes(fd) != attrs:\n                    raise _Skip("preference_metadata_failed")\n            with _operation("chown"):\n                prepared = os.fstat(fd)\n                if (prepared.st_uid, prepared.st_gid, stat.S_IMODE(prepared.st_mode)) != (\n                        info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode)):\n                    raise _Skip("preference_metadata_failed")\n            os.fsync(fd)\n            with _operation("verify"):\n                validate()\n                current, current_info, current_attrs = _read_file(directory, name, info.st_uid)\n                if (current != original or _signature(current_info) != _signature(info)\n                        or current_attrs != attrs\n                        or _file_state(directory, temporary) != _signature(os.fstat(fd))):\n                    raise _Skip("preferences_changed")\n            os.replace(temporary, name, src_dir_fd=directory, dst_dir_fd=directory)\n            published = True\n            try:\n                os.fsync(directory)\n            except OSError:\n                pass  # The data file was synced before its atomic publication.\n            with _operation("verify"):\n                current, current_info, current_attrs = _read_file(directory, name, info.st_uid)\n                if current != updated or current_attrs != attrs:\n                    raise _Skip("preference_write_unverified")\n        finally:\n            os.close(fd)\n            if not published:\n                try:\n                    os.unlink(temporary, dir_fd=directory)\n                except FileNotFoundError:\n                    pass\n\n\ndef prepare_launch_preferences(request, data_roots=("/data/user/0", "/data/data"),\n                               proc_root="/proc"):\n    """Prepare saved body bounds only when the clone is observably stopped."""\n    result = {"status": "skipped", "reason": "invalid_request"}\n    stage = "request"\n    app_fd = prefs_fd = None\n    try:\n        if (not isinstance(request, dict) or not isinstance(request.get("package"), str)\n                or len(request["package"]) > 255 or not _PACKAGE.fullmatch(request["package"])):\n            result["stage"] = stage\n            return result\n        package, body = request["package"], _validated_body(request.get("body"))\n        result.update(package=package, body=list(body))\n        stage = "root_identity"\n        if os.geteuid() != 0:\n            raise _Skip("root_unavailable")\n        stage = "app_directory"\n        with _operation(stage):\n            app_fd = _open_app_directory(package, data_roots)\n            uid = os.fstat(app_fd).st_uid\n\n        def require_stopped():\n            diagnostics = {}\n            state = _process_state(package, uid, proc_root, diagnostics)\n            if state:\n                raise _Skip(state, **diagnostics)\n\n        stage = "process_status"\n        require_stopped()\n        stage = "preference_scan"\n        with _operation(stage):\n            prefs_fd = os.open("shared_prefs", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW\n                               | os.O_CLOEXEC, dir_fd=app_fd)\n            prefs_info = os.fstat(prefs_fd)\n            if prefs_info.st_uid != uid:\n                raise _Skip("unsafe_preferences_directory")\n            names = set(os.listdir(prefs_fd))\n            bases = {name[:-4] if name.endswith(".xml.bak") else name for name in names\n                     if name.endswith((".xml", ".xml.bak"))}\n            if len(names) > 256 or len(bases) > 128:\n                raise _Skip("too_many_preference_files")\n            selected, total = None, 0\n            for base in sorted(bases):\n                name = base + ".bak" if base + ".bak" in names else base\n                states = (_file_state(prefs_fd, base), _file_state(prefs_fd, base + ".bak"))\n                data, info, attrs = _read_file(prefs_fd, name, uid)\n                total += len(data)\n                if total > MAX_TOTAL_BYTES:\n                    raise _Skip("preference_scan_too_large")\n                if not all(key.encode() in data for key in KEYS):\n                    continue\n                updated, old = patch_window_preferences(data, body)\n                if selected is not None:\n                    raise _Skip("window_preferences_ambiguous")\n                selected = (base, name, data, updated, old, info, attrs, states)\n            if selected is None:\n                raise _Skip("window_preferences_missing")\n        base, name, original, updated, old, info, attrs, states = selected\n        result.update(preference_file=name, old_body=list(old))\n\n        def validate():\n            require_stopped()\n            with _operation("verify"):\n                directory = os.stat("shared_prefs", dir_fd=app_fd, follow_symlinks=False)\n                if ((directory.st_dev, directory.st_ino, directory.st_uid) !=\n                        (prefs_info.st_dev, prefs_info.st_ino, uid)):\n                    raise _Skip("preferences_changed")\n                if states != (_file_state(prefs_fd, base), _file_state(prefs_fd, base + ".bak")):\n                    raise _Skip("preferences_changed")\n\n        stage = "verify"\n        validate()\n        if updated == original:\n            result.update(status="unchanged", reason="window_bounds_already_saved")\n        else:\n            stage = "publish"\n            _atomic_replace(prefs_fd, name, original, updated, info, attrs, validate)\n            result.update(status="prepared", reason="window_bounds_saved")\n    except _Skip as exc:\n        result.update(reason=str(exc), stage=stage)\n        result.update(exc.diagnostics)\n    except ValueError as exc:\n        reason = str(exc)\n        result.update(reason=reason if reason in _VALUE_REASONS else\n                      "preference_preparation_failed", stage=stage,\n                      exception_type=_EXCEPTION_TYPES.get(type(exc), "Exception"))\n    except OSError as exc:\n        result.update(reason="preferences_access_unavailable",\n                      **_diagnostics(stage, errno=exc.errno,\n                                     exception_type=_EXCEPTION_TYPES.get(type(exc), "Exception")))\n    except Exception as exc:\n        result.update(reason="preference_preparation_failed", stage=stage,\n                      exception_type=_EXCEPTION_TYPES.get(type(exc), "Exception"))\n    finally:\n        if prefs_fd is not None:\n            os.close(prefs_fd)\n        if app_fd is not None:\n            os.close(app_fd)\n        result["runtime"] = _runtime_metadata()\n    return result\n\n\ndef _deadline(_signum, _frame):\n    raise _Skip("preparation_timeout")\n\n\nif __name__ == "__main__":\n    outcome = {"status": "skipped", "reason": "invalid_request"}\n    try:\n        signal.signal(signal.SIGALRM, _deadline)\n        signal.alarm(5)\n        if len(sys.argv) == 2:\n            outcome = prepare_launch_preferences(json.loads(sys.argv[1]))\n    except Exception:\n        outcome = {"status": "skipped", "reason": "preference_preparation_failed"}\n    finally:\n        signal.alarm(0)\n    print(json.dumps(outcome, separators=(",", ":")))\n'
import shlex
import sys


class _SortBlocked(RuntimeError):
    """A required window or display detail is not yet available."""


class _SortLaunchAbort(RuntimeError):
    """Halt the launch sequence when a clone cannot open in its assigned slot."""


class _SortCommandError(RuntimeError):
    """Keep the actual command result instead of an unrelated output tail."""

    def __init__(self, record):
        self.record = record
        command = ' '.join(str(a) for a in record['argv'])
        errors = record.get('error_lines') or []
        reason = errors[0] if errors else record.get('stderr', '').strip().split('\n')[0]
        if not reason:
            reason = 'Command timed out.' if record.get('timed_out') else 'No error text was returned.'
        code = 'timeout' if record.get('timed_out') else 'exit ' + str(record.get('returncode'))
        super().__init__(f'{command} ({code}): {reason[:240]}')


def _sort_text(value):
    if isinstance(value, bytes):
        return value.decode('utf-8', 'replace')
    return value or ''


def _sort_error_lines(text):
    # Match command diagnostics only at the beginning of a line. Window titles
    # such as "mCurrentFocus=Window{... Application Error: Roblox}" are data.
    pattern = re.compile(
        r'^[ \t]*(?:Permission (?:Denial:|denied\b)|'
        r'(?:java\.lang\.)?SecurityException\b|'
        r'(?:cmd:[ \t]*)?Failure calling service\b|Error:|Unknown command\b|'
        r"Can't find service:|(?:/[^ :]+/)?(?:su|sh|dumpsys|wm|input|pm|cmd):"
        r'[^\n]*(?:Permission denied|not found|inaccessible)|'
        r'Exception occurred while executing\b)', re.I | re.M)
    return [line.strip() for line in text.splitlines() if pattern.match(line)]


def _safe_launch_preparation(result):
    """Keep window metadata only; never report private preference contents."""
    if not isinstance(result, dict) or result.get('status') not in ('prepared', 'unchanged', 'skipped'):
        return {'status': 'skipped', 'reason': 'helper_result_invalid'}
    reason = result.get('reason', 'window_preferences_checked')
    if not isinstance(reason, str) or not re.fullmatch(r'[a-z0-9_]{1,80}', reason):
        return {'status': 'skipped', 'reason': 'helper_result_invalid'}
    safe = {'status': result['status'], 'reason': reason}
    for key in ('old_body', 'body'):
        edges = result.get(key)
        if isinstance(edges, (list, tuple)) and len(edges) == 4 and all(type(v) is int for v in edges):
            safe[key] = list(edges)
    name = result.get('preference_file')
    if (isinstance(name, str) and 0 < len(name) <= 200
            and not any(c in name for c in ('/', '\\', '\n', '\r'))):
        safe['preference_file'] = name
    for key in ('command_returncode', 'wrapper_returncode', 'errno', 'pid', 'checked'):
        value = result.get(key)
        if type(value) is int:
            safe[key] = value
    for key in ('stage', 'diagnostic'):
        value = result.get(key)
        if isinstance(value, str) and re.fullmatch(r'[a-z0-9_]{1,80}', value):
            safe[key] = value
    exception_type = result.get('exception_type')
    if exception_type in (
            'Exception', 'AttributeError', 'NotImplementedError', 'TypeError',
            'ValueError', 'LookupError', 'UnicodeError', 'UnicodeDecodeError',
            'UnicodeEncodeError', 'ImportError', 'ModuleNotFoundError',
            'OverflowError', 'RuntimeError', 'OSError', 'PermissionError',
            'FileNotFoundError', 'TimeoutError', 'MemoryError', 'KeyError',
            'IndexError', 'BufferError', 'FileExistsError', 'NotADirectoryError',
            'IsADirectoryError', 'InterruptedError', 'BlockingIOError', 'ProcessLookupError'):
        safe['exception_type'] = exception_type
    runtime = result.get('runtime')
    if isinstance(runtime, dict):
        details = {}
        version = runtime.get('python_version')
        if isinstance(version, str) and re.fullmatch(r'\d{1,3}\.\d{1,3}\.\d{1,3}', version):
            details['python_version'] = version
        backend = runtime.get('xattr_backend')
        if backend in ('unselected', 'os', 'libc', 'unavailable'):
            details['xattr_backend'] = backend
        capabilities = runtime.get('capabilities')
        if isinstance(capabilities, dict):
            details['capabilities'] = {
                key: capabilities[key] for key in (
                    'os_listxattr', 'os_getxattr', 'os_setxattr', 'os_removexattr',
                    'listdir_fd', 'open_dir_fd', 'stat_dir_fd', 'stat_nofollow',
                    'rename_dir_fd', 'unlink_dir_fd')
                if type(capabilities.get(key)) is bool}
        if details:
            safe['runtime'] = details
    return safe


class _AndroidSortIO:
    def __init__(self):
        if not os.path.exists('/system/bin/am') or not os.path.exists('/system/bin/dumpsys'):
            raise RuntimeError('Auto sort must run inside the cloud phone in Termux.')
        self.direct = os.geteuid() == 0
        self.last_result = None
        self.root_probe = None
        try:
            uid = self.run(['/system/bin/id', '-u']).strip()
        except _SortCommandError as exc:
            record = exc.record
            # The device report printed UID 0 with exit 1 and no error. UID
            # output establishes root for this probe only; it must never make
            # later window reads or launch commands ignore their own failures.
            exact_root = (record['stdout'].strip() == '0'
                          and not record['stderr'].strip()
                          and not record['error_lines']
                          and not record['timed_out']
                          and not record.get('transport_error')
                          and isinstance(record['returncode'], int)
                          and record['returncode'] > 0)
            if not exact_root:
                raise
            uid = '0'
            self.root_probe = dict(record, accepted_nonzero_status=True)
        if self.root_probe is None:
            self.root_probe = dict(self.last_result, accepted_nonzero_status=False)
        self.root_probe['uid_confirmed'] = uid == '0'
        if uid != '0':
            record = dict(self.root_probe)
            record['error_lines'] = record['error_lines'] + [
                'Auto sort needs root; id -u returned ' + repr(uid[:64]) + '.']
            record['permission_denied'] = True
            raise _SortCommandError(record)

    def run(self, argv, timeout=6):
        command = ' '.join(shlex.quote(str(arg)) for arg in argv)
        marker = None
        if self.direct:
            args = list(argv)
        else:
            # Some cloud-phone su wrappers return their own nonzero status
            # even when the Android command succeeds. Capture the command's
            # status inside an explicit shell, before the wrapper can alter it.
            marker = '__ROBLOX_SORT_EXIT_' + os.urandom(16).hex() + '__'
            script = (command + '\n_roblox_sort_status=$?\n'
                      + "printf '\\n" + marker + "=%s\\n' \"$_roblox_sort_status\"\n"
                      + 'exit "$_roblox_sort_status"\n')
            args = ['su', '-c', '/system/bin/sh -c ' + shlex.quote(script)]
        record = {'argv': list(argv), 'returncode': None, 'stdout': '', 'stderr': '',
                  'error_lines': [], 'timed_out': False,
                  'execution_mode': 'direct' if self.direct else 'su_shell',
                  'wrapper_returncode': None, 'inner_returncode': None,
                  'exit_status_source': 'direct' if self.direct else 'unavailable',
                  'transport_error': None,
                  'readonly': os.path.basename(str(argv[0])) in ('id', 'dumpsys', 'wm', 'pm'),
                  'permission_denied': False}
        try:
            result = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True,
                                    text=True, timeout=timeout)
            record.update(returncode=result.returncode, wrapper_returncode=result.returncode,
                          stdout=_sort_text(result.stdout),
                          stderr=_sort_text(result.stderr))
        except subprocess.TimeoutExpired as exc:
            record.update(stdout=_sort_text(exc.stdout), stderr=_sort_text(exc.stderr), timed_out=True)
        except OSError as exc:
            record['stderr'] = str(exc)
            record['error_lines'] = [str(exc)]
        if marker is not None:
            raw = record['stdout']
            match = re.search(r'\n' + re.escape(marker) + r'=([0-9]{1,3})\n\Z', raw)
            if match and raw.count(marker) == 1 and int(match.group(1)) <= 255:
                record['inner_returncode'] = int(match.group(1))
                record['returncode'] = record['inner_returncode']
                record['exit_status_source'] = 'inner_marker'
                # The protocol adds exactly one leading newline. Removing
                # from its start preserves the command's original output.
                record['stdout'] = raw[:match.start()]
            else:
                record['transport_error'] = 'Root command exit marker missing or invalid.'
                if not record['timed_out']:
                    record['error_lines'].append(record['transport_error'])
        record['error_lines'] += _sort_error_lines(record['stderr']) + _sort_error_lines(record['stdout'])
        record['permission_denied'] = any(re.search(
            r'Permission (?:Denial|denied)|SecurityException', line, re.I)
            for line in record['error_lines'])
        self.last_result = record
        if (record['returncode'] != 0 or record['error_lines']
                or record['timed_out'] or record['transport_error']):
            raise _SortCommandError(record)
        return record['stdout']

    def stop_package(self, package):
        if not re.fullmatch(_PKG_PATTERN, package):
            raise RuntimeError('Invalid selected package.')
        self.run(['/system/bin/am', 'force-stop', '--user', '0', package], timeout=10)
        return True

    def launch_package(self, package, place_id):
        if not re.fullmatch(_PKG_PATTERN, package):
            raise RuntimeError('Invalid selected package.')
        base = ['/system/bin/am', 'start', '--user', '0']
        commands = [
            base + ['-n', package + '/com.roblox.client.ActivityProtocolLaunch',
                    '-f', '0x10008000', '-a', 'android.intent.action.VIEW',
                    '-d', 'roblox://placeId=' + str(place_id) + '&launchData=rejoin'],
            base + ['-f', '0x10008000', '-a', 'android.intent.action.VIEW',
                    '-d', 'roblox://placeId=' + str(place_id), '-p', package]]
        self.launch_failures = []
        for argv in commands:
            try:
                output = self.run(argv, timeout=10)
                if re.search(r'(?im)^\s*(?:Error\b|Exception\b|java\.\S*Exception\b)', output):
                    self.launch_failures.append({'reason': 'activity_start_error'})
                    continue
                return True
            except _SortCommandError as exc:
                self.launch_failures.append({
                    'reason': 'activity_start_failed',
                    'returncode': exc.record.get('returncode'),
                    'timed_out': exc.record.get('timed_out', False)})
        return False

    def prepare_window(self, package, body):
        # The helper reads app-local settings itself and returns only geometry.
        # Never pipe private XML through run(), _read(), or diagnostic argv.
        try:
            request = json.dumps({'package': package, 'body': list(body)}, separators=(',', ':'))
            raw = self.run([sys.executable, '-c', _SORT_PREFS_HELPER, request], timeout=10)
            return _safe_launch_preparation(json.loads(raw))
        except _SortCommandError as exc:
            record = exc.record
            stderr = record.get('stderr', '').lower()
            if record.get('timed_out'):
                diagnostic = 'timeout'
            elif record.get('transport_error'):
                diagnostic = 'exit_marker_missing'
            elif 'cannot link executable' in stderr or 'shared librar' in stderr:
                diagnostic = 'linker_failure'
            elif 'modulenotfounderror' in stderr or 'importerror' in stderr:
                diagnostic = 'stdlib_import_failure'
            elif 'permission denied' in stderr:
                diagnostic = 'execution_denied'
            elif 'not found' in stderr or 'no such file' in stderr:
                diagnostic = 'executable_not_found'
            else:
                diagnostic = 'unknown_startup_failure'
            self.last_result = None
            return _safe_launch_preparation({
                'status': 'skipped', 'reason': 'root_helper_failed',
                'stage': 'root_python', 'diagnostic': diagnostic,
                'command_returncode': record.get('returncode'),
                'wrapper_returncode': record.get('wrapper_returncode')})
        except Exception:
            self.last_result = None
            return {'status': 'skipped', 'reason': 'preparation_unavailable'}

    def pause(self, seconds):
        time.sleep(seconds)


class AndroidWindowSorter:
    """Open selected clones at prepared bounds; never inject touch input."""

    TOLERANCE = 4

    def __init__(self, packages, io=None, report_path=None):
        self.packages = list(dict.fromkeys(packages))
        self.io = io
        self.geometry = None
        self.density_dpi = None
        self.plan = None
        self.status = 'Waiting for windows'
        self.detail = ''
        self.disabled = False
        self.pending = set(self.packages)
        self.suspended = {}
        self.last_tokens = {}
        self.observed = {}
        self.verified = set()
        self.gestures = []
        self.window_fields = []
        self.discovery = []
        self.window_groups = []
        self.launch_preparation = {}
        self.launch_verification = {}
        self.started = set()
        self.strict_halted = False
        self.layout_signature = None
        self.raw_dumps = {}
        self.command_failure = None
        self.owner_uid_packages = {}
        self.uid_check_at = 0.0
        self.read_retry_at = 0.0
        self.read_failures = 0
        self.last_attempt = {}
        self.next_poll = 0.0
        self.report_path = report_path or os.path.expanduser('~/roblox_auto_sort_report.json')
        self._last_report = None

    @staticmethod
    def _near(a, b):
        return all(abs(x - y) <= AndroidWindowSorter.TOLERANCE for x, y in zip(a, b))

    @staticmethod
    def _clip_dump(text, limit=262144):
        if len(text) <= limit:
            return text
        return text[:limit - 32768] + '\n[diagnostic output truncated]\n' + text[-32768:]

    def _read(self, label, argv, timeout=6):
        try:
            raw = self.io.run(argv, timeout=timeout)
        except _SortCommandError as exc:
            self.command_failure = exc.record
            self.raw_dumps[label] = {
                k: self._clip_dump(v) if isinstance(v, str) else v
                for k, v in exc.record.items()}
            self.raw_dumps[label].update(complete=False, captured_at=time.time())
            raise
        result = getattr(self.io, 'last_result', None)
        details = result if isinstance(result, dict) and result.get('argv') == list(argv) else {}
        self.raw_dumps[label] = {
            k: self._clip_dump(v) if isinstance(v, str) else v
            for k, v in details.items()}
        self.raw_dumps[label].update(
            argv=list(argv), stdout=self._clip_dump(raw), returncode=details.get('returncode', 0),
            complete=True, captured_at=time.time())
        return raw

    def _failure(self, exc):
        self.detail = str(exc)
        if isinstance(exc, _SortCommandError):
            self.command_failure = exc.record
            if exc.record['readonly'] and not exc.record['permission_denied']:
                self.read_failures += 1
                delay = min(30, 5 * (2 ** min(self.read_failures - 1, 3)))
                self.read_retry_at = time.monotonic() + delay
                self.status = f'Window read failed; retry in {delay}s'
                return
        self.disabled = True
        self.status = 'Unavailable'

    def _ready(self):
        if self.disabled or time.monotonic() < self.read_retry_at:
            return False
        try:
            if self.io is None:
                self.io = _AndroidSortIO()
            displays = self._read('displays', ['/system/bin/dumpsys', 'window', 'displays'])
            try:
                geometry = parse_display_geometry(displays)
            except ValueError:
                size = self._read('size', ['/system/bin/wm', 'size'])
                geometry = parse_display_geometry(displays, size)
            if self.geometry != geometry:
                self.geometry = geometry
                self.density_dpi = geometry.get('density_dpi')
                self.plan = plan_grid(self.packages, geometry['bounds'])
                self.pending.update(self.packages)
                self.suspended.clear()
                self.verified.clear()
            return True
        except Exception as exc:
            self._failure(exc)
            self._save_report()
            return False

    def _floating_profile(self, window=None):
        # Constants verified in the uploaded APK's FloatingWindowManager.
        # Caption size differs from the invisible resize-input margin.
        if self.density_dpi is None:
            raw = self._read('density', ['/system/bin/wm', 'density'])
            values = re.findall(r'(?im)^(?:Physical|Override) density:\s*(\d+)\s*$', raw)
            if not values:
                raise _SortBlocked('Display density is unavailable for the floating controls.')
            self.density_dpi = int(values[-1])
        dpi = self.density_dpi
        px = lambda dp: int(dp * dpi / 160.0 + 0.5)
        margin = px(32)
        if window is not None and abs(window['resize_margin'] - margin) > 1:
            raise _SortBlocked('Floating resize margins do not match the reported display density.')
        caption = px(40)
        return {'name': 'appcloner_floating', 'density_dpi': dpi,
                'caption_height': caption, 'resize_margin': margin,
                'min_body_width': px(160), 'min_body_height': px(120)}

    def _launch_layout(self):
        if not self._ready():
            raise _SortBlocked('Display information is unavailable.')
        profile = self._floating_profile()
        signature = (self.geometry['width'], self.geometry['height'],
                     tuple(self.geometry['bounds']), self.density_dpi)
        if self.layout_signature is not None and signature != self.layout_signature:
            raise _SortBlocked('Display changed; restart rejoin to calculate the new layout.')
        fitted = plan_grid(self.packages, self.geometry['bounds'],
                           min_width=profile['min_body_width'],
                           min_height=profile['min_body_height'] + profile['caption_height'])
        self.plan = fitted
        return profile, signature

    def prepare_launch(self, package):
        """Confirm saved body bounds while the selected clone is stopped."""
        record = {'package': package, 'status': 'blocked',
                  'reason': 'preparation_unavailable', 'captured_at': time.time()}
        self.launch_preparation[package] = record
        try:
            if package not in self.packages:
                record['reason'] = 'package_not_selected'
                return record
            profile, signature = self._launch_layout()
            l, t, r, b = self.plan['slots'][package]
            body = (l, t + profile['caption_height'], r, b)
            record.update(target_visible=(l, t, r, b), target_body=body)
            # A force-stopped process can take a moment to disappear. Each
            # retry repeats the complete helper checks; unknown never means dead.
            deadline = time.monotonic() + 1.0
            while True:
                result = _safe_launch_preparation(self.io.prepare_window(package, body))
                if (result.get('reason') not in ('already_running', 'process_check_unavailable')
                        or time.monotonic() >= deadline):
                    break
                self.io.pause(0.15)
            record.update(result)
            if result['status'] not in ('prepared', 'unchanged'):
                record['status'] = 'blocked'
            elif tuple(result.get('body', ())) != body:
                record.update(status='blocked', reason='prepared_bounds_unverified')
            else:
                self.layout_signature = signature
            return record
        except Exception:
            record.update(status='blocked', reason='preparation_unavailable')
            return record
        finally:
            self._save_report()

    def _abort_launch(self, package, stage, reason):
        self.strict_halted = True
        self.disabled = True
        self.verified.discard(package)
        self.status = 'Launch layout blocked'
        self.detail = package + ': ' + stage + ' (' + reason + ')'
        if stage == 'prepare':
            preparation = self.launch_preparation.get(package, {})
            diagnostics = [preparation[key] for key in ('stage', 'exception_type')
                           if preparation.get(key)]
            if type(preparation.get('errno')) is int:
                diagnostics.append('errno=' + str(preparation['errno']))
            if diagnostics:
                self.detail += ' [' + ', '.join(diagnostics) + ']'
        record = self.launch_verification.setdefault(package, {})
        record.update(phase=stage + '_failed', reason=reason, finished_at=time.time())
        self._save_report()
        raise _SortLaunchAbort(self.detail + '. The next clone was not opened. Report: ' + self.report_path)

    def launch_in_slot(self, package, place_id):
        """Stop, prepare, open, and verify one clone before allowing the next."""
        if self.strict_halted or self.disabled:
            raise _SortLaunchAbort('Auto sort is stopped. Report: ' + self.report_path)
        if package not in self.packages:
            self._abort_launch(package, 'selection', 'package_not_selected')
        stage = 'display'
        self.launch_verification[package] = {'phase': 'starting', 'started_at': time.time(),
                                             'snapshots': 0, 'matches': 0}
        record = self.launch_verification[package]
        try:
            self._launch_layout()  # Check that the full selected grid can fit.
            self.schedule(package)
            self.started.discard(package)
            stage = 'stop'
            record['phase'] = 'stopping'
            self.status = 'Preparing launch layout'
            self.detail = package
            self._save_report()
            if not self.io.stop_package(package):
                self._abort_launch(package, stage, 'stop_not_confirmed')
            stage = 'prepare'
            record['phase'] = 'preparing'
            preparation = self.prepare_launch(package)
            if preparation['status'] not in ('prepared', 'unchanged'):
                self._abort_launch(package, stage, preparation.get('reason', 'preparation_unavailable'))
            expected = tuple(preparation['target_visible'])
            record.update(expected=expected, prepared_body=preparation['target_body'])
            # Re-read display state before opening; a rotation invalidates the
            # prepared coordinates and must not trigger a visible correction.
            self._launch_layout()
            stage = 'launch'
            record['phase'] = 'opening'
            self._save_report()
            if not self.io.launch_package(package, place_id):
                self._abort_launch(package, stage, 'package_launch_failed')
            stage = 'verify'
            record['phase'] = 'waiting_for_window'
            deadline = time.monotonic() + 30.0
            matches = 0
            previous_wrong = None
            previous_match_token = None
            self.io.pause(0.3)
            while time.monotonic() < deadline:
                try:
                    self._launch_layout()
                    window, _ = self._get_window(package)
                    if not window.get('composite'):
                        raise _SortBlocked('Waiting for the complete floating window.')
                    record['snapshots'] += 1
                    record['observed'] = window['bounds']
                    record['body_observed'] = window['body_bounds']
                    record.setdefault('first_observed', window['bounds'])
                    if self._near(window['bounds'], expected):
                        matches = matches + 1 if previous_match_token == window['token'] else 1
                        previous_match_token = window['token']
                        previous_wrong = None
                        record['matches'] = matches
                        if matches >= 2:
                            self.pending.discard(package)
                            self.verified.add(package)
                            self.started.add(package)
                            self.last_tokens[package] = window['token']
                            record.update(phase='verified', finished_at=time.time())
                            self.status = f'{len(self.started)}/{len(self.packages)} opened in place'
                            self.detail = f"{self.plan['columns']} columns x {self.plan['rows']} rows"
                            self._save_report()
                            return True
                    else:
                        matches = 0
                        previous_match_token = None
                        record['matches'] = 0
                        wrong = (window['token'], tuple(window['bounds']))
                        if wrong == previous_wrong:
                            self._abort_launch(package, stage, 'opened_at_wrong_bounds')
                        previous_wrong = wrong
                except _SortLaunchAbort:
                    raise
                except (_SortBlocked, _SortCommandError) as exc:
                    matches = 0
                    previous_match_token = None
                    previous_wrong = None
                    record['matches'] = 0
                    record['waiting_reason'] = ('window_read_failed' if isinstance(exc, _SortCommandError)
                                                else 'window_not_ready')
                    if self.disabled:
                        self._abort_launch(package, stage, 'window_read_unavailable')
                self._save_report()
                self.io.pause(0.25)
            self._abort_launch(package, stage, 'window_verification_timeout')
        except _SortLaunchAbort:
            raise
        except _SortCommandError as exc:
            self.command_failure = exc.record
            self._abort_launch(package, stage, 'android_command_failed')
        except Exception as exc:
            self._abort_launch(package, stage, type(exc).__name__)

    def _snapshot(self):
        raw = self._read('windows', ['/system/bin/dumpsys', 'window', 'windows'])
        all_windows = parse_window_dump(raw, include_overlays=True,
                                        owner_uid_packages=self.owner_uid_packages)
        # Some APKs replace the activity title and omit the package field. Only
        # use a uniquely owned UID; a shared UID never chooses a package by guess.
        unknown_owner = any(w['type'] == 1 and w['package'] is None
                            and w.get('owner_uid') is not None for w in all_windows)
        if unknown_owner and time.monotonic() >= self.uid_check_at:
            self.uid_check_at = time.monotonic() + 60.0
            try:
                listing = self._read('package_uids', ['/system/bin/pm', 'list', 'packages', '-U'])
                mapping = {}
                for match in re.finditer(r'(?m)^package:([^\s]+)\s+uid:(\d+)\s*$', listing):
                    package, uid = match.group(1), int(match.group(2))
                    mapping.setdefault(uid, []).append(package)
                self.owner_uid_packages = mapping
            except _SortCommandError as exc:
                # Explicit package detection can still work without this
                # optional metadata. Keep the failure details for diagnostics.
                self.command_failure = exc.record
        physical = [w for w in parse_window_dump(raw, self.packages,
                    owner_uid_packages=self.owner_uid_packages) if w['display_id'] == 0]
        selected = resolve_clone_windows(physical, self.packages)
        for window in selected:
            if window.get('composite') and not window.get('group_error'):
                try:
                    profile = self._floating_profile(window)
                    l, t, r, b = window['body_bounds']
                    window['bounds'] = (l, t - profile['caption_height'], r, b)
                    window['profile'] = profile
                except _SortBlocked as exc:
                    window['group_error'] = str(exc)
        profiles = [w['profile'] for w in selected if w.get('profile')]
        if profiles:
            minimum_width = max(p['min_body_width'] for p in profiles)
            minimum_height = max(p['min_body_height'] + p['caption_height'] for p in profiles)
            fitted = plan_grid(self.packages, self.geometry['bounds'],
                               min_width=minimum_width, min_height=minimum_height)
            if self.plan != fitted:
                self.plan = fitted
                self.pending.update(self.packages)
                self.suspended.clear()
                self.verified.clear()
        covering = [w for w in parse_window_dump(raw, include_overlays=True,
                    owner_uid_packages=self.owner_uid_packages)
                    if w['display_id'] == 0 and w['touchable']]
        self.window_groups = [
            {'package': w['package'], 'body_token': w['token'],
             'bounds': w['bounds'], 'body_bounds': w.get('body_bounds'),
             'composite': w.get('composite', False), 'group_error': w.get('group_error'),
             'profile': w.get('profile'), 'member_tokens': w.get('member_tokens', [w['token']]),
             'controls': {role: {'token': part['token'], 'bounds': part['bounds']}
                          for role, part in w.get('chrome', {}).items()}}
            for w in selected]
        self.discovery = window_diagnostics(raw, self.packages, self.owner_uid_packages)
        self.window_fields = [line for item in self.discovery
                              if item.get('package') in self.packages
                              for line in item.get('fields', [])][:180]
        self.read_failures = 0
        self.read_retry_at = 0.0
        counts = {p: sum(w['package'] == p for w in selected) for p in self.packages}
        self.observed = {w['package']: w['bounds'] for w in selected
                         if counts[w['package']] == 1 and not w.get('group_error')}
        self.verified = {
            p for p, bounds in self.observed.items()
            if self.plan and self._near(bounds, self.plan['slots'][p])
        }
        return selected, covering

    def _get_window(self, package, snapshot=None):
        selected, covering = snapshot if snapshot is not None else self._snapshot()
        found = [w for w in selected if w['package'] == package]
        if not found:
            raise _SortBlocked(f'No visible main window detected for {package}. See discovery in the report.')
        if len(found) != 1:
            raise _SortBlocked('More than one main window is visible for this clone.')
        if found[0].get('group_error'):
            raise _SortBlocked(found[0]['group_error'])
        return found[0], covering

    def schedule(self, package):
        if package in self.packages:
            self.pending.add(package)
            self.suspended.pop(package, None)
            self.verified.discard(package)

    def try_place(self, package, after_launch=False):
        """Compatibility name for a read-only check; never changes a window."""
        if self.disabled or package not in self.packages or not self._ready():
            return False
        try:
            window, _ = self._get_window(package)
            if not self._near(window['bounds'], self.plan['slots'][package]):
                self.status = 'Window differs from launch slot'
                self.detail = package + ': saved layout will be applied on its next rejoin.'
                return False
            self.pending.discard(package)
            self.verified.add(package)
            self.status = f'{len(self.verified)}/{len(self.packages)} in place'
            self.detail = f"{self.plan['columns']} columns x {self.plan['rows']} rows"
            return True
        except _SortBlocked:
            self.status = 'Waiting for clone windows'
            self.detail = package
            return False
        except Exception as exc:
            self._failure(exc)
            return False
        finally:
            self._save_report()

    def tick(self):
        """Observe only. Missing/rejoining windows never cause corrective input."""
        if self.disabled or time.monotonic() < self.next_poll:
            return
        self.next_poll = time.monotonic() + 5.0
        if not self._ready():
            return
        try:
            selected, _ = self._snapshot()
            present = {w['package'] for w in selected if not w.get('group_error')}
            self.pending = set(self.packages) - self.verified
            changed = (self.started & present) - self.verified
            if changed:
                self.status = 'Window differs from launch slot'
                self.detail = 'Saved layout will be applied on the next rejoin.'
            else:
                self.status = f'{len(self.verified)}/{len(self.packages)} in place'
                self.detail = (f"{self.plan['columns']} columns x {self.plan['rows']} rows"
                               if selected else 'Waiting for clones to open.')
        except Exception as exc:
            self._failure(exc)
        self._save_report()

    def _save_report(self):
        report = {
            'feature': 'ZERO X REJOIN TOOL V1 FREE VERSION - Auto sort', 'status': self.status, 'detail': self.detail,
            'screen': self.geometry, 'layout': self.plan,
            'root_probe': getattr(self.io, 'root_probe', None),
            'layout_method': 'prelaunch_preferences_only', 'gesture_input_allowed': False,
            'instances': [{'package': p, 'observed': self.observed.get(p),
                           'verified': p in self.verified,
                           'error': self.suspended.get(p)} for p in self.packages],
            'recent_gestures': self.gestures,
            'window_dump_fields': self.window_fields,
            'window_discovery': self.discovery,
            'window_groups': self.window_groups,
            'launch_preparation': self.launch_preparation,
            'launch_verification': self.launch_verification,
            'launch_failures': getattr(self.io, 'launch_failures', []),
            'raw_dumps': self.raw_dumps,
            'command_failure': ({k: self._clip_dump(v) if isinstance(v, str) else v
                                 for k, v in self.command_failure.items()}
                                if self.command_failure else None),
            'note': 'Local Android window diagnostics: ownership, geometry and command results.'
        }
        payload = json.dumps(report, indent=2)
        if payload == self._last_report:
            return
        try:
            with open(self.report_path, 'w') as handle:
                handle.write(payload + '\n')
            self._last_report = payload
        except OSError:
            pass


_auto_sorter = None


def run_layout_test(cfg):
    """Read-only check of windows already open; never moves or resizes them."""
    packages = list(dict.fromkeys(p for p in (cfg.get('packages') or [ROBLOX_PKG])
                                  if isinstance(p, str) and _PKG_RE.fullmatch(p))) or [ROBLOX_PKG]
    sorter = AndroidWindowSorter(packages)
    budget = max(60.0, 15.0 * len(packages))
    print('Read-only layout check. Show the selected Roblox windows within 10 seconds.', flush=True)
    print('This check does not launch, move, or resize windows. Use normal rejoin to open them in place.', flush=True)
    print(f'The test will check and retry for up to {int(budget)} seconds after that.', flush=True)
    try:
        time.sleep(10)
        deadline = time.monotonic() + budget
        last_notice = None
        # Drive the normal controller, including read backoff and fresh bounds
        # checks. Keep all selected slots reserved while waiting for a clone.
        while time.monotonic() < deadline:
            sorter.tick()
            notice = sorter.status + (': ' + sorter.detail if sorter.detail else '')
            if notice != last_notice:
                print(notice, flush=True)
                last_notice = notice
            if (len(sorter.verified) == len(packages) or sorter.disabled
                    or all(p in sorter.verified or p in sorter.suspended for p in packages)):
                break
            time.sleep(0.5)
        else:
            sorter.detail = 'Test time limit reached. ' + sorter.detail
    except KeyboardInterrupt:
        sorter.detail = 'Stopped with Ctrl+C.'
    except Exception as exc:
        sorter._failure(exc)
    finally:
        if len(sorter.verified) != len(packages):
            sorter.status = f'Check ended: {len(sorter.verified)}/{len(packages)} in place'
        sorter._save_report()
    print(sorter.status + ': ' + sorter.detail)
    print('Report: ' + sorter.report_path)


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
    if not out:return run
    return {p for p in run if _get_pkg_activity_state(p,out)=='ingame'}

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
        if n_off or ram>=cfg.get("ram_limit",90.0) or get_cpu()>=cfg.get("cpu_limit",85.0):embed_color=0xFF4444
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
        embed_obj={"title":"ZERO X REJOIN TOOL V1 FREE VERSION","description":description,"color":embed_color,"footer":{"text":f"ZERO X REJOIN TOOL V1 FREE VERSION · {reason}"[:200]}}
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

def launch(place_id,pkg=ROBLOX_PKG):
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
    pk=inst["pkg"]
    if _auto_sorter is not None:
        ok=_auto_sorter.launch_in_slot(pk,cfg["place_id"])
    else:
        ok=launch(cfg["place_id"],pkg=pk)
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
    STATUS_DOT={"INGAME":cl("●","92"),"LAUNCHING":cl("◐","93"),"CHECKING":cl("◐","93"),"OFFLINE":cl("○","91"),"LOBBY":cl("◑","93")}
    STATUS_COL={"INGAME":"92","LAUNCHING":"93","CHECKING":"93","OFFLINE":"91","LOBBY":"93"}
    lines=["",cl(f"  ZERO X REJOIN TOOL V1 FREE VERSION  ·  {gname}","1;97"),cl("  "+"─"*W,"2"),
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
    if restart_str:lines.append(cl(restart_str,"93"))
    if _auto_sorter is not None:
        lines.append(cl("  Auto sort: "+_auto_sorter.status,"96"))
        if _auto_sorter.detail and len(_auto_sorter.verified)<len(_auto_sorter.packages):
            lines.append(cl("  "+_auto_sorter.detail[:100],"2"))
        if _auto_sorter.disabled or _auto_sorter.suspended or _auto_sorter.pending:
            lines.append(cl("  Details: ~/roblox_auto_sort_report.json","93"))
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
    global _last_event,_auto_sorter
    cfg=normalize_config(cfg)
    os.system("clear");print(cl("\n  Starting ZERO X REJOIN TOOL V1 FREE VERSION...","96"),flush=True)
    pkgs=list(dict.fromkeys(p for p in (cfg.get("packages") or [ROBLOX_PKG])
                            if isinstance(p,str) and _PKG_RE.fullmatch(p))) or [ROBLOX_PKG]
    cfg["packages"]=pkgs
    _auto_sorter=AndroidWindowSorter(pkgs) if cfg.get("auto_sort") else None
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
    start_time_ref=[start_time];stop_event=threading.Event();_overload_counts=[0]
    if cfg.get("webhook_enabled") and cfg.get("webhook_url"):
        threading.Thread(target=webhook_loop,args=(cfg,stop_event,start_time_ref),daemon=True).start()
    startup_hook_at=start_time+(len(pkgs)-1)*stagger+cfg["rejoin_cooldown"]+5
    game_name=get_game_name(cfg["place_id"]);last_overload=0.0
    try:
        while True:
            now=time.time();uptime=int(now-start_time)
            ram=get_ram();cpu=get_cpu();running=get_running_set(pkgs)
            if single:
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
                            _begin_rejoin(cfg,inst,"disconnected" if disc else "heartbeat lost",_fr,0)
                            continue
                if pk not in running:
                    inst["crashes"]+=1;inst["idle_count"]=0
                    _last_event=f"{pk[-16:]}: not running ({inst['crashes']}/{cfg['crash_confirm']})"
                    if inst["crashes"]>=cfg["crash_confirm"]:
                        _begin_rejoin(cfg,inst,"crash",True,0)
                else:
                    if inst["crashes"]>0:_last_event=f"{pk[-16:]}: running ✓"
                    inst["crashes"]=0
                    # ── Bubble detection (tuned down) ──────────────────
                    # Only trigger if CPU is basically dead (< 0.3%) for a
                    # long time (>120s) — avoids false positives on idle games
                    _,rcpu,_=get_instance_stats(pk)
                    busy_secs=now-inst["busy_until"] if inst["busy_until"] else 999
                    if rcpu<cfg.get("lobby_cpu",4.0) and busy_secs>cfg.get("lobby_idle_wait",30):
                        inst["idle_count"]=inst.get("idle_count",0)+1
                        if inst["idle_count"]>=cfg.get("lobby_idle_count",4):
                            _last_event=f"{pk[-16:]}: stuck on lobby, rejoining"
                            inst["idle_count"]=0
                            _fr=(now-inst.get("last_lobby",0))<300
                            inst["last_lobby"]=now
                            _begin_rejoin(cfg,inst,"lobby",_fr,0)
                    else:
                        inst["idle_count"]=0
            if _auto_sorter is not None:
                # Preparation can take seconds; use fresh overload samples.
                now=time.time();ram=get_ram();cpu=get_cpu()
            _overload_cpu=cpu>=cfg.get("cpu_limit",85.0)
            _overload_ram=ram>=cfg.get("ram_limit",90.0)
            if (_overload_cpu or _overload_ram) and now-last_overload>=max(60,cfg["rejoin_cooldown"]*2):
                _overload_counts[0]=_overload_counts[0]+1
                _overload_reason=("cpu+ram" if (_overload_cpu and _overload_ram) else ("cpu" if _overload_cpu else "ram"))
                if _overload_counts[0]>=cfg.get("overload_confirm",3):
                    _overload_counts[0]=0;last_overload=time.time()
                    _last_event=f"overload({_overload_reason} {cpu:.0f}%/{ram:.0f}%) — killing all & restarting"
                    fire_webhook(cfg,f"overload:{_overload_reason}")
                    for inst in insts:
                        kill_roblox(inst["pkg"])
                        inst["crashes"]=0;inst["reason"]=f"overload({_overload_reason})"
                        inst["next_restart"]=None;inst["launch_at"]=time.time()
            else:
                _overload_counts[0]=0
            if startup_hook_at and now>=startup_hook_at:
                startup_hook_at=None;fire_webhook(cfg,"monitor_started",min_gap=0)
            if _auto_sorter is not None:_auto_sorter.tick()
            draw_dashboard(cfg,ram,cpu,uptime,insts,running,game_name)
            time.sleep(cfg["check_interval"])
    except KeyboardInterrupt:
        os.system("clear");print(cl("\n  Stopped.\n","93"),flush=True)
    except _SortLaunchAbort as exc:
        print(cl("\n  Rejoin stopped: "+str(exc)+"\n","91"),flush=True)
    finally:
        stop_event.set()
        if _auto_sorter is not None:_auto_sorter._save_report()
        _auto_sorter=None

if __name__=="__main__":
    if "--layout-test" in sys.argv:
        run_layout_test(load_config())
    else:
        banner();cfg=load_config()
        cfg=settings_menu(cfg);monitor(cfg)
