"""
Roblox Auto-Rejoin — Kivy APK
Faithful port of the Termux v5.5 script.
All core engine logic is preserved; only the UI layer is replaced with Kivy.
"""

# ─────────────────────────────────────────────────────────────────────────────
#  stdlib / psutil bootstrap (same as original)
# ─────────────────────────────────────────────────────────────────────────────
import os, sys, re, time, signal, json, threading, subprocess, traceback
from datetime import datetime, timedelta

try:
    import psutil
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "psutil"], check=True)
    import psutil

try:
    import urllib.request, urllib.parse, urllib.error
except ImportError:
    pass

# ─────────────────────────────────────────────────────────────────────────────
#  Kivy imports
# ─────────────────────────────────────────────────────────────────────────────
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.switch import Switch
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.graphics import Color, Rectangle, RoundedRectangle

# ─────────────────────────────────────────────────────────────────────────────
#  COLOURS
# ─────────────────────────────────────────────────────────────────────────────
C_BG      = (0.07, 0.07, 0.09, 1)
C_PANEL   = (0.12, 0.12, 0.15, 1)
C_PANEL2  = (0.16, 0.16, 0.20, 1)
C_ACCENT  = (0.18, 0.52, 1.00, 1)
C_GREEN   = (0.18, 0.78, 0.44, 1)
C_RED     = (0.90, 0.25, 0.25, 1)
C_YELLOW  = (0.98, 0.78, 0.14, 1)
C_ORANGE  = (0.95, 0.55, 0.10, 1)
C_TEXT    = (0.93, 0.93, 0.96, 1)
C_SUBTEXT = (0.52, 0.52, 0.60, 1)
C_START   = (0.12, 0.68, 0.36, 1)
C_STOP    = (0.82, 0.20, 0.20, 1)

# ─────────────────────────────────────────────────────────────────────────────
#  FILES & CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
ROBLOX_PKG    = "com.roblox.client"
FLAG_FILENAME = "disconnect.flag"
GAMES_FILE    = os.path.expanduser("~/roblox_games.json")
CONFIG_FILE   = os.path.expanduser("~/roblox_config.json")
LOG_PATH      = "/sdcard/roblox_rejoin.log"
SCREENSHOT_PATH = "/sdcard/roblox_status.png"

EXECUTOR_PATHS = [
    "/sdcard/Fluxus/workspace/", "/sdcard/Delta/workspace/",
    "/sdcard/AceusX/workspace/", "/sdcard/ArceusX/workspace/",
    "/sdcard/Hydrogen/workspace/", "/sdcard/Codex/workspace/",
    "/sdcard/Trigon/workspace/", "/sdcard/Xeno/workspace/",
    os.path.expanduser("~/"), "/sdcard/",
]

DEFAULT_CFG = {
    "place_id": "", "check_interval": 5, "rejoin_cooldown": 25,
    "crash_delay": 30, "crash_confirm": 3, "ram_limit": 90.0,
    "auto_restart": True, "restart_seconds": 7200,
    "watch_flag": True, "webhook_url": "", "webhook_interval": 60,
    "webhook_enabled": False, "server_mode": "off", "roblosecurity": "",
    "packages": [ROBLOX_PKG], "launch_stagger": 15, "lobby_cpu": 4.0,
    "seq_join": True, "seq_gap": 5, "seq_timeout": 150,
    "heartbeat": False, "hb_timeout": 45, "hb_grace": 30, "hb_ids": [],
    "lobby_idle_count": 4, "lobby_idle_wait": 30,
}

_PKG_RE = re.compile(r'^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+$')

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIG & GAMES
# ─────────────────────────────────────────────────────────────────────────────
def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE) as f:
                return {**DEFAULT_CFG, **json.load(f)}
    except Exception:
        pass
    return dict(DEFAULT_CFG)

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        log(f"Config save error: {e}", "WARN")

def load_games():
    try:
        if os.path.exists(GAMES_FILE):
            with open(GAMES_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return []

def save_games(games):
    try:
        with open(GAMES_FILE, "w") as f:
            json.dump(games, f, indent=2)
    except Exception:
        pass

# ─────────────────────────────────────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────────────────────────────────────
_log_listeners = []   # callables registered by the UI

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_PATH, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass
    for cb in list(_log_listeners):
        try:
            Clock.schedule_once(lambda dt, m=line: cb(m), 0)
        except Exception:
            pass

# ─────────────────────────────────────────────────────────────────────────────
#  SHELL HELPERS  (verbatim from original)
# ─────────────────────────────────────────────────────────────────────────────
_orig_run = subprocess.run
def _run(*a, **k):
    k.setdefault("stdin", subprocess.DEVNULL)
    return _orig_run(*a, **k)
subprocess.run = _run

def _sh_out(cmd, timeout=25):
    for argv in (["su", "-c", cmd], ["sh", "-c", cmd]):
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
            if r.stdout.strip():
                return r.stdout
        except Exception:
            pass
    return ""

# ─────────────────────────────────────────────────────────────────────────────
#  CPU SAMPLER  (verbatim from original)
# ─────────────────────────────────────────────────────────────────────────────
_cpu_value = 0.0
_cpu_lock  = threading.Lock()

def _sample_cpu_once():
    try:
        def _read_stat():
            for argv in (["su", "-c", "cat /proc/stat"], ["cat", "/proc/stat"]):
                try:
                    r = subprocess.run(argv, capture_output=True, text=True, timeout=3)
                    first = r.stdout.splitlines()[0] if r.stdout else ""
                    if first.startswith("cpu"):
                        vals = list(map(int, first.split()[1:8]))
                        idle = vals[3] + vals[4]
                        return idle, sum(vals)
                except Exception:
                    pass
            return None, None
        i1, t1 = _read_stat()
        if t1 is not None:
            time.sleep(1.0)
            i2, t2 = _read_stat()
            if t2 is not None:
                dt = t2 - t1
                if dt > 0:
                    return round((1 - (i2 - i1) / dt) * 100, 1)
    except Exception:
        pass
    try:
        r = subprocess.run(["su", "-c", "top -bn1"], capture_output=True, text=True, timeout=6)
        for line in r.stdout.splitlines():
            mc = re.search(r'(\d+(?:\.\d+)?)%cpu', line, re.I)
            mi = re.search(r'(\d+(?:\.\d+)?)%idle', line, re.I)
            if mc and mi:
                total = float(mc.group(1)); idle = float(mi.group(1))
                if total > 0:
                    return round((total - idle) / total * 100, 1)
            mu = re.search(r'(\d+\.?\d*)\s*%?\s*us', line, re.I)
            if mu:
                return round(float(mu.group(1)), 1)
    except Exception:
        pass
    try:
        return round(psutil.cpu_percent(interval=1.0), 1)
    except Exception:
        pass
    return 0.0

def _cpu_sampler():
    global _cpu_value
    while True:
        try:
            v = _sample_cpu_once()
            with _cpu_lock:
                _cpu_value = v
        except Exception:
            pass
        time.sleep(3)

def _warmup_cpu():
    global _cpu_value
    try:
        psutil.cpu_percent(interval=None)
    except Exception:
        pass
    t = threading.Thread(target=_cpu_sampler, daemon=True)
    t.start()
    for _ in range(20):
        time.sleep(0.5)
        with _cpu_lock:
            if _cpu_value > 0.0:
                return
    try:
        v = round(psutil.cpu_percent(interval=1.5), 1)
        if v > 0.0:
            with _cpu_lock:
                _cpu_value = v
    except Exception:
        pass

def get_cpu():
    with _cpu_lock:
        return _cpu_value

def get_ram():
    try:
        return psutil.virtual_memory().percent
    except Exception:
        return 0.0

def get_ram_free_mb():
    try:
        return int(psutil.virtual_memory().available // (1024 * 1024))
    except Exception:
        return 0

# ─────────────────────────────────────────────────────────────────────────────
#  INSTANCE SAMPLER  (verbatim from original)
# ─────────────────────────────────────────────────────────────────────────────
_inst_pkgs    = []
_inst_stats   = {}
_inst_state   = {}
_inst_lock    = threading.Lock()
_inst_started = False
_proc_visible = False
INSTANCES     = []

def set_sampler_packages(pkgs):
    global _inst_pkgs
    with _inst_lock:
        _inst_pkgs = [p for p in pkgs if _PKG_RE.match(p)]

_LIST_CMD = (
    '[ -r /proc/1/stat ] && echo VISIBLE=1; '
    'for pk in @@LIST@@; do p=$(pidof $pk | cut -d" " -f1); '
    '[ -n "$p" ] && { echo "PKG=$pk PID=$p"; cat /proc/$p/stat; grep VmRSS /proc/$p/status; }; done'
)

def _inst_sh(cmd, timeout=8):
    for argv in (["su", "-c", cmd], ["sh", "-c", cmd]):
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
            if "VISIBLE=" in r.stdout or "PKG=" in r.stdout:
                return r.stdout
        except Exception:
            pass
    return ""

def _sample_instances():
    global _proc_visible
    with _inst_lock:
        pkgs = list(_inst_pkgs)
    if not pkgs:
        return {}
    out = _inst_sh(_LIST_CMD.replace("@@LIST@@", " ".join(pkgs)))
    _proc_visible = "VISIBLE=" in out
    found = {}; cur = None
    for ln in out.splitlines():
        ln = ln.rstrip()
        if ln.startswith("PKG="):
            try:
                parts = ln.split(); pk = parts[0][4:]; pid = int(parts[1][4:])
                cur = found.setdefault(pk, {"pid": pid, "ticks": None, "start": None, "ram": 0})
            except Exception:
                cur = None
        elif cur is not None and ln.startswith(f"{cur['pid']} ("):
            try:
                rest = ln.rpartition(")")[2].split()
                cur["ticks"] = int(rest[11]) + int(rest[12])
                cur["start"] = rest[19]
            except Exception:
                pass
        elif cur is not None and ln.startswith("VmRSS"):
            try:
                cur["ram"] = int(ln.split()[1]) // 1024
            except Exception:
                pass
    now = time.time()
    try:
        clk = os.sysconf("SC_CLK_TCK")
    except Exception:
        clk = 100
    ncpu = os.cpu_count() or 1
    res = {}
    for pk in pkgs:
        d = found.get(pk)
        if not d:
            _inst_state.pop(pk, None); res[pk] = (0, 0.0, None); continue
        cpu = 0.0; st = _inst_state.get(pk)
        if d["ticks"] is not None:
            if st and st["pid"] == d["pid"] and st["start"] == d["start"] and st["t"]:
                el = now - st["t"]
                if el > 0:
                    cpu = max(0.0, min(100.0, round((d["ticks"] - st["ticks"]) / clk / el * 100 / ncpu, 1)))
            _inst_state[pk] = {"pid": d["pid"], "start": d["start"], "ticks": d["ticks"], "t": now}
        res[pk] = (d["ram"], cpu, d["pid"])
    return res

def _inst_loop():
    global _inst_stats
    while True:
        try:
            v = _sample_instances()
            with _inst_lock:
                _inst_stats = v
        except Exception:
            pass
        time.sleep(2)

def _ensure_sampler():
    global _inst_started, _inst_stats
    if _inst_started:
        return
    _inst_started = True
    try:
        v = _sample_instances()
        with _inst_lock:
            _inst_stats = v
    except Exception:
        pass
    threading.Thread(target=_inst_loop, daemon=True).start()

def get_instance_stats(pkg):
    _ensure_sampler()
    with _inst_lock:
        return _inst_stats.get(pkg, (0, 0.0, None))

# ─────────────────────────────────────────────────────────────────────────────
#  DUMPSYS ACTIVITY STATE  (verbatim from original)
# ─────────────────────────────────────────────────────────────────────────────
_dumpsys_cache = {"out": "", "t": 0}
_dumpsys_lock  = threading.Lock()
_home_pkg_cache = {"pkg": None, "t": 0}

def _get_dumpsys_activities():
    now = time.time()
    with _dumpsys_lock:
        if now - _dumpsys_cache["t"] < 3.0 and _dumpsys_cache["out"]:
            return _dumpsys_cache["out"]
    out = ""
    for argv in (["su", "-c", "dumpsys activity activities"], ["dumpsys", "activity", "activities"]):
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=8)
            if r.stdout.strip():
                out = r.stdout; break
        except Exception:
            pass
    with _dumpsys_lock:
        _dumpsys_cache["out"] = out
        _dumpsys_cache["t"]   = time.time()
    return out

def _get_home_pkg():
    if _home_pkg_cache["pkg"] and time.time() - _home_pkg_cache["t"] < 300:
        return _home_pkg_cache["pkg"]
    pkg = None
    out = _sh_out("pm resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME", timeout=8)
    for ln in reversed(out.splitlines()):
        m = re.match(r'^\s*([A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+)/', ln)
        if m:
            pkg = m.group(1); break
    _home_pkg_cache["pkg"] = pkg; _home_pkg_cache["t"] = time.time()
    return pkg

def _resumed_pkgs(out):
    res = set()
    for m in re.finditer(r'[Rr]esumedActivity[^\n]*?ActivityRecord\{[0-9a-f]+ u\d+ ([^/\s]+)/', out):
        res.add(m.group(1))
    return res

def _get_pkg_activity_state(pkg, out):
    if not out or pkg not in out:
        return 'offline'
    home = _get_home_pkg(); resumed = _resumed_pkgs(out)
    if home and home in resumed and pkg not in resumed:
        return 'minimized'
    recs = list(re.finditer(rf'ActivityRecord\{{[0-9a-f]+ u\d+ {re.escape(pkg)}/(\S+)', out))
    if not recs:
        return 'minimized'
    dead_ev = False; alive_ev = False
    for m in recs:
        nxt = out.find("ActivityRecord{", m.end())
        end = min(len(out), m.end() + 3000) if nxt == -1 else min(nxt, m.end() + 3000)
        blk = out[m.end():end]
        if ("finishing=true" in blk) or re.search(r'state=(DESTROYED|DESTROYING|FINISHING)', blk):
            dead_ev = True
        elif "finishing=false" in blk:
            alive_ev = True
    if dead_ev and not alive_ev:
        return 'minimized'
    return 'ingame'

# ─────────────────────────────────────────────────────────────────────────────
#  ROBLOX PRESENCE API  (verbatim from original)
# ─────────────────────────────────────────────────────────────────────────────
_acct = {}
_presence = {"t": 0, "data": {}, "neg": {}}
_presence_lock = threading.Lock()
_presence_err  = [""]

def _read_cookie(pkg):
    import sqlite3, tempfile
    try:
        out = _sh_out(f"find /data/data/{pkg} /data/user/0/{pkg} -name Cookies 2>/dev/null", timeout=15)
        paths = [p.strip() for p in out.splitlines() if p.strip().endswith("Cookies")]
        for p in paths:
            try:
                r = subprocess.run(["su", "-c", f"cat '{p}'"], capture_output=True, timeout=15)
                if not r.stdout:
                    continue
                tmp = os.path.join(tempfile.gettempdir(), f".ck_{abs(hash(pkg))}.db")
                with open(tmp, "wb") as f:
                    f.write(r.stdout)
                try:
                    con = sqlite3.connect(tmp)
                    rows = con.execute(
                        "SELECT value,encrypted_value FROM cookies "
                        "WHERE name='.ROBLOSECURITY' AND host_key LIKE '%roblox.com'"
                    ).fetchall()
                    con.close()
                finally:
                    try: os.remove(tmp)
                    except: pass
                for v, ev in rows:
                    if v: return v
            except Exception:
                pass
    except Exception:
        pass
    return ""

def _rbx_req(url, cookie, data=None, csrf=None):
    h = {"User-Agent": "RobloxRejoin/5.5", "Cookie": f".ROBLOSECURITY={cookie}", "Accept": "application/json"}
    if data is not None:
        h["Content-Type"] = "application/json"
    if csrf:
        h["X-CSRF-TOKEN"] = csrf
    req = urllib.request.Request(
        url, data=json.dumps(data).encode() if data is not None else None,
        headers=h, method="POST" if data is not None else "GET"
    )
    return urllib.request.urlopen(req, timeout=10)

def _get_uid(pkg):
    a = _acct.get(pkg)
    if a and a.get("uid") and time.time() - a["t"] < 1800:
        return a
    ck = _read_cookie(pkg)
    if not ck:
        _acct[pkg] = {"cookie": "", "uid": None, "t": time.time() - 1500}
        return _acct[pkg]
    uid = None
    try:
        with _rbx_req("https://users.roblox.com/v1/users/authenticated", ck) as r:
            uid = json.loads(r.read()).get("id")
    except Exception as e:
        _presence_err[0] = f"uid: {e}"
    _acct[pkg] = {"cookie": ck, "uid": uid, "t": time.time()}
    return _acct[pkg]

def _fetch_presence(pkgs):
    accts = {p: _get_uid(p) for p in pkgs}
    ids   = {p: a["uid"] for p, a in accts.items() if a.get("uid")}
    if not ids:
        return {}
    ck   = next(a["cookie"] for a in accts.values() if a.get("uid"))
    body = {"userIds": list(ids.values())}
    csrf = None; data = None
    for _ in range(2):
        try:
            with _rbx_req("https://presence.roblox.com/v1/presence/users", ck, data=body, csrf=csrf) as r:
                data = json.loads(r.read()); break
        except urllib.error.HTTPError as e:
            if e.code == 403 and e.headers.get("x-csrf-token") and not csrf:
                csrf = e.headers["x-csrf-token"]; continue
            _presence_err[0] = f"presence HTTP {e.code}"; return {}
        except Exception as e:
            _presence_err[0] = f"presence: {e}"; return {}
    if not data:
        return {}
    by = {u.get("userId"): u.get("userPresenceType") for u in data.get("userPresences", [])}
    return {p: by.get(uid) for p, uid in ids.items()}

def _presence_ingame(pkgs):
    now = time.time()
    with _presence_lock:
        if now - _presence["t"] >= 20:
            _presence["t"] = now
            try:
                res = _fetch_presence(pkgs)
            except Exception as e:
                _presence_err[0] = str(e); res = {}
            _presence["data"] = res
            for p, t in res.items():
                if t is None: continue
                _presence["neg"][p] = 0 if t == 2 else _presence["neg"].get(p, 0) + 1
        return {p for p in pkgs
                if _presence["neg"].get(p, 0) >= 2
                and _presence["data"].get(p) is not None
                and _presence["data"].get(p) != 2}

def _apply_presence(res):
    if not res:
        return res
    now = time.time(); check = []
    for p in res:
        inst = next((i for i in INSTANCES if i["pkg"] == p), None)
        if inst and now < (inst.get("busy_until") or 0) + 60:
            continue
        check.append(p)
    if not check:
        return res
    try:
        bad = _presence_ingame(check)
    except Exception:
        bad = set()
    return {p for p in res if p not in bad}

def get_running_set(pkgs):
    _ensure_sampler()
    with _inst_lock:
        st = dict(_inst_stats)
    run = {p for p in pkgs if st.get(p, (0, 0.0, None))[2] is not None}
    if not run:
        missing = [p for p in pkgs if p not in run]
        if missing:
            try:
                for proc in psutil.process_iter(["name"]):
                    n = (proc.info["name"] or "")
                    if n in missing: run.add(n)
            except Exception:
                pass
        missing = [p for p in pkgs if p not in run]
        if missing:
            try:
                r = subprocess.run(["am", "stack", "list"], capture_output=True, text=True, timeout=5)
                for p in missing:
                    if p in r.stdout: run.add(p)
            except Exception:
                pass
    out = _get_dumpsys_activities()
    if not out:
        return run
    res = {p for p in run if _get_pkg_activity_state(p, out) == 'ingame'}
    return _apply_presence(res)

# ─────────────────────────────────────────────────────────────────────────────
#  DISCONNECT FLAG  (verbatim from original)
# ─────────────────────────────────────────────────────────────────────────────
def check_flag():
    for folder in EXECUTOR_PATHS:
        p = os.path.join(folder, FLAG_FILENAME)
        try:
            if os.path.exists(p):
                content = open(p).read().strip()
                if content:
                    reason = content.split("|")[1] if "|" in content else "unknown"
                    return True, reason, p
        except Exception:
            pass
    return False, None, None

def clear_flags():
    for folder in EXECUTOR_PATHS:
        p = os.path.join(folder, FLAG_FILENAME)
        try:
            if os.path.exists(p):
                open(p, "w").write("")
        except Exception:
            pass

# ─────────────────────────────────────────────────────────────────────────────
#  GAME NAME / SERVER LOOKUP  (verbatim from original)
# ─────────────────────────────────────────────────────────────────────────────
_game_name_cache   = {}
_universe_id_cache = {}

def get_universe_id(place_id):
    if place_id in _universe_id_cache:
        return _universe_id_cache[place_id]
    try:
        req = urllib.request.Request(
            f"https://apis.roblox.com/universes/v1/places/{place_id}/universe",
            headers={"User-Agent": "RobloxRejoin/5.5"}
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            uid = json.loads(r.read())["universeId"]
            _universe_id_cache[place_id] = uid
            return uid
    except Exception:
        pass
    return None

def get_game_name(place_id):
    if place_id in _game_name_cache:
        return _game_name_cache[place_id]
    try:
        uid = get_universe_id(place_id)
        if uid is None: return None
        req2 = urllib.request.Request(
            f"https://games.roblox.com/v1/games?universeIds={uid}",
            headers={"User-Agent": "RobloxRejoin/5.5"}
        )
        with urllib.request.urlopen(req2, timeout=5) as r2:
            name = json.loads(r2.read())["data"][0]["name"]
            _game_name_cache[place_id] = name
            return name
    except Exception:
        pass
    return None

def get_servers(place_id, cookie, mode="highest"):
    uid = get_universe_id(place_id)
    if uid is None or not cookie:
        return None, None
    sort_order = "Asc" if mode == "lowest" else "Desc"
    all_servers = []; cursor = ""
    for page in range(2):
        url = (f"https://games.roblox.com/v1/games/{uid}/servers/Public"
               f"?limit=100&sortOrder={sort_order}"
               + (f"&cursor={urllib.parse.quote(cursor)}" if cursor else ""))
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "RobloxRejoin/5.5",
                "Cookie": f".ROBLOSECURITY={cookie}",
                "Accept": "application/json"
            })
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
            servers = data.get("data", []); all_servers.extend(servers)
            usable_so_far = [s for s in all_servers
                             if s.get("accessCode") and s.get("playing") is not None
                             and s.get("maxPlayers", 0) > 0 and s["playing"] < s["maxPlayers"]]
            if usable_so_far and page == 0: break
            cursor = data.get("nextPageCursor") or ""
            if not cursor: break
        except Exception as e:
            log(f"get_servers error: {e}", "WARN"); break
    usable = [s for s in all_servers
              if s.get("accessCode") and s.get("playing") is not None
              and s.get("maxPlayers", 0) > 0 and s["playing"] < s["maxPlayers"]]
    if not usable:
        return None, None
    picked = (max(usable, key=lambda s: s["playing"]) if mode == "highest"
              else min(usable, key=lambda s: s["playing"]))
    return picked["accessCode"], picked["playing"]

# ─────────────────────────────────────────────────────────────────────────────
#  HEARTBEAT  (verbatim from original)
# ─────────────────────────────────────────────────────────────────────────────
_hb_cache = {"path": {}, "read": {}, "miss": {}}
_hb_auto  = {}

def _hb_id(cfg, pk):
    pkgs = cfg.get("packages") or [ROBLOX_PKG]
    ids  = cfg.get("hb_ids") or []
    try:
        i = pkgs.index(pk)
    except ValueError:
        i = -1
    return ids[i] if 0 <= i < len(ids) and ids[i] else None

def _hb_scan_all(pk):
    for d in EXECUTOR_PATHS:
        try:
            if not os.path.isdir(d): continue
            for fn in os.listdir(d):
                if fn.startswith("hb_") and fn.endswith(".txt"):
                    return os.path.join(d, fn), fn[3:-4]
        except Exception:
            pass
    try:
        out = _sh_out(f"find /sdcard/Android/data/{pk} -maxdepth 7 -name 'hb_*.txt' 2>/dev/null", timeout=20)
        for l in out.splitlines():
            l = l.strip()
            if l:
                fn = os.path.basename(l)
                return l, fn[3:-4]
    except Exception:
        pass
    return None

def _hb_state(cfg, pk):
    hid = _hb_id(cfg, pk); now = time.time()
    c = _hb_cache["read"].get(pk)
    if c and now - c[0] < 3:
        return c[1]
    cands = []; p = _hb_cache["path"].get(pk)
    if p:
        cands = [p]
    else:
        if hid:
            name = f"hb_{hid}.txt"
            if now - _hb_cache["miss"].get(pk, 0) > 45:
                cands = [os.path.join(d, name) for d in EXECUTOR_PATHS]
                out = _sh_out(f"find /sdcard/Android/data/{pk} -maxdepth 7 -name '{name}' 2>/dev/null", timeout=20)
                cands += [l.strip() for l in out.splitlines() if l.strip()]
        else:
            cached = _hb_auto.get(pk)
            if cached:
                cands = [cached[0]]
            elif now - _hb_cache["miss"].get(pk, 0) > 45:
                found = _hb_scan_all(pk)
                if found:
                    _hb_auto[pk] = found; cands = [found[0]]
    res = None
    for p in cands:
        try:
            txt = open(p).read() if os.path.exists(p) else _sh_out(f"cat '{p}'", timeout=5)
        except Exception:
            txt = ""
        txt = (txt or "").strip()
        if not txt: continue
        parts = txt.split("|")
        try:
            ts = float(parts[0])
        except Exception:
            continue
        res = (ts, parts[2].strip().lower() if len(parts) > 2 else "alive")
        _hb_cache["path"][pk] = p; break
    if res is None:
        _hb_cache["path"].pop(pk, None); _hb_auto.pop(pk, None); _hb_cache["miss"][pk] = now
    _hb_cache["read"][pk] = (now, res)
    return res

# ─────────────────────────────────────────────────────────────────────────────
#  LAUNCH & REJOIN  (verbatim from original)
# ─────────────────────────────────────────────────────────────────────────────
_last_event  = ""
_session_start = [time.time()]

def kill_roblox(pkg=ROBLOX_PKG):
    try:
        for proc in psutil.process_iter(["name", "pid"]):
            try:
                n = proc.info["name"] or ""
                if n == pkg or n.startswith(pkg + ":"):
                    os.kill(proc.pid, signal.SIGKILL)
            except Exception:
                pass
    except Exception:
        pass
    for argv in (["am", "force-stop", pkg], ["su", "-c", f"am force-stop {pkg}"]):
        try:
            subprocess.run(argv, timeout=8, capture_output=True)
        except Exception:
            pass
    time.sleep(2)

def launch(place_id, access_code=None, pkg=ROBLOX_PKG):
    if access_code:
        url = (f"roblox://experiences/start?accessCode={urllib.parse.quote(access_code)}&launchData=rejoin")
        for argv in (
            ["am", "start", "-n", f"{pkg}/com.roblox.client.ActivityProtocolLaunch",
             "-f", "0x10008000", "-a", "android.intent.action.VIEW", "-d", url],
            ["am", "start", "-f", "0x10008000", "-a", "android.intent.action.VIEW", "-d", url, "-p", pkg],
        ):
            try:
                r = subprocess.run(argv, capture_output=True, text=True, timeout=10)
                if r.returncode == 0: return True
            except Exception:
                pass
        try:
            subprocess.run(["termux-open-url", url], capture_output=True, timeout=10)
            return True
        except Exception:
            pass
        log("Access-code launch failed — falling back to default matchmaking", "WARN")
    for argv in (
        ["am", "start", "-n", f"{pkg}/com.roblox.client.ActivityProtocolLaunch",
         "-f", "0x10008000", "-a", "android.intent.action.VIEW",
         "-d", f"roblox://placeId={place_id}&launchData=rejoin"],
        ["am", "start", "-f", "0x10008000", "-a", "android.intent.action.VIEW",
         "-d", f"roblox://placeId={place_id}", "-p", pkg],
    ):
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=10)
            if r.returncode == 0: return True
        except Exception:
            pass
    try:
        subprocess.run(["termux-open-url", f"roblox://placeId={place_id}"], capture_output=True, timeout=10)
        return True
    except Exception:
        pass
    return False

# ─────────────────────────────────────────────────────────────────────────────
#  SEQUENTIAL JOIN
# ─────────────────────────────────────────────────────────────────────────────
def _seq_can_launch(cfg, inst, insts, running, now):
    if not cfg.get("seq_join", True) or len(insts) < 2:
        return True
    gap = cfg.get("seq_gap", 5); tmo = cfg.get("seq_timeout", 150)
    for o in insts:
        if o is inst or o["launch_at"] is not None or not o.get("start"):
            continue
        if now >= o["start"] + tmo:
            continue
        up = (o["pkg"] in running and now >= o["busy_until"]
              and get_instance_stats(o["pkg"])[1] >= cfg.get("lobby_cpu", 4.0))
        if up:
            if o.get("seq_confirm") is None:
                o["seq_confirm"] = now
            if now < o["seq_confirm"] + gap:
                return False
            continue
        return False
    return True

# ─────────────────────────────────────────────────────────────────────────────
#  DISCORD WEBHOOK  (verbatim from original, thread-safe)
# ─────────────────────────────────────────────────────────────────────────────
_last_hook = 0.0

def send_webhook(cfg, ram, cpu, reason="status", uptime_secs=0):
    global _last_hook
    if not cfg.get("webhook_enabled") or not cfg.get("webhook_url"):
        return
    url = cfg["webhook_url"].strip()
    if not url.startswith("https://discord.com/api/webhooks/"):
        log("Webhook URL invalid", "WARN"); return
    try:
        import uuid
        _last_hook = time.time()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ram_free = get_ram_free_mb()
        insts = list(INSTANCES); pkgs = [i["pkg"] for i in insts]
        running = get_running_set(pkgs) if pkgs else set()
        rows = []
        for inst in insts:
            ram_mb, rcpu, _pid = get_instance_stats(inst["pkg"])
            rows.append((inst, inst_status(inst, running), ram_mb, rcpu))
        n_ing  = sum(1 for r in rows if r[1] == "INGAME")
        n_off  = sum(1 for r in rows if r[1] == "OFFLINE")
        n_wait = sum(1 for r in rows if r[1] in ("LAUNCHING", "CHECKING"))
        if n_off or ram >= cfg["ram_limit"]:   embed_color = 0xFF4444
        elif n_wait:                           embed_color = 0xFFAA00
        else:                                  embed_color = 0x57F287
        try:
            total_ram_mb = int(psutil.virtual_memory().total // (1024 * 1024))
            used_ram_mb  = total_ram_mb - ram_free
        except Exception:
            total_ram_mb = 0; used_ram_mb = 0
        def pbar(pct, total=20):
            filled = int(round(pct / 100 * total))
            return "█" * filled + "░" * (total - filled)
        dots = {"INGAME": "🟢", "LAUNCHING": "🟡", "CHECKING": "🟡", "OFFLINE": "🔴", "LOBBY": "🟠"}
        desc_lines = [
            f"**Last Updated:** {ts}", "",
            f"⚙️ **CPU:** `{pbar(cpu)}` {cpu:.1f}%",
            f"💾 **RAM:** `{pbar(ram)}` {used_ram_mb} MB / {total_ram_mb} MB", "",
            f"**Instances ({n_ing}/{len(rows)} in-game):**"
        ]
        now = time.time()
        for i, (inst, status, ram_mb, rcpu) in enumerate(rows, 1):
            up = _seconds_to_str(now - inst["start"]) if inst["start"] and status != "OFFLINE" else "-"
            desc_lines.append(f"{i}. {dots.get(status,'⚪')} **{inst['pkg']}** : {status}")
            desc_lines.append(f"└ ⏱ `{up}` | 💾 `{ram_mb} MB` | ⚡ `{rcpu:.1f}%`")
        desc_lines += [
            "", "**Session**",
            f"🎯 Place ID: `{cfg['place_id']}`",
            f"⏱️ Uptime: `{_seconds_to_str(uptime_secs)}`",
        ]
        embed_obj = {
            "title": "📊 0x Rejoin Update",
            "description": "\n".join(desc_lines)[:4000],
            "color": embed_color,
            "footer": {"text": f"Roblox Auto-Rejoin v5.5 · {reason}"[:200]}
        }
        payload = json.dumps({"embeds": [embed_obj]}).encode("utf-8")
        req = urllib.request.Request(url, data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "RobloxRejoin/5.5"},
            method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            if resp.status in (200, 204):
                log("Webhook sent ✓", "WEBHOOK")
            else:
                log(f"Webhook failed: {resp.status}", "WARN")
    except Exception as e:
        log(f"Webhook error: {e}", "WARN")

def fire_webhook(cfg, reason, min_gap=20):
    global _last_hook
    if not (cfg.get("webhook_enabled") and cfg.get("webhook_url")):
        return
    if time.time() - _last_hook < min_gap:
        return
    _last_hook = time.time()
    up = int(time.time() - _session_start[0])
    threading.Thread(target=send_webhook, args=(cfg, get_ram(), get_cpu(), reason, up), daemon=True).start()

def _webhook_loop(cfg, stop_event, start_time_ref):
    while not stop_event.is_set():
        time.sleep(cfg["webhook_interval"])
        if stop_event.is_set(): break
        uptime = int(time.time() - start_time_ref[0])
        send_webhook(cfg, get_ram(), get_cpu(), "scheduled", uptime_secs=uptime)

# ─────────────────────────────────────────────────────────────────────────────
#  INSTANCE STATUS HELPER
# ─────────────────────────────────────────────────────────────────────────────
def inst_status(inst, running):
    if inst["launch_at"] is not None:     return "OFFLINE"
    if time.time() < inst["busy_until"]:  return "LAUNCHING"
    if inst["pkg"] in running:            return "INGAME"
    _, _, pid = get_instance_stats(inst["pkg"])
    if pid is not None:                   return "LOBBY"
    return "CHECKING" if inst["crashes"] > 0 else "OFFLINE"

def _seconds_to_str(s):
    s = int(s)
    if s < 60:   return f"{s}s"
    elif s < 3600: return f"{s//60}m {s%60}s"
    else:          return f"{s//3600}h {(s%3600)//60}m"

# ─────────────────────────────────────────────────────────────────────────────
#  MONITOR THREAD  (faithful port of the original monitor() loop)
# ─────────────────────────────────────────────────────────────────────────────
class MonitorThread(threading.Thread):
    def __init__(self, cfg):
        super().__init__(daemon=True)
        self.cfg        = cfg
        self.running    = True
        self.stop_event = threading.Event()
        # Callbacks registered by the UI (called on Kivy thread via Clock)
        self.on_stats   = None   # (cpu, ram)
        self.on_insts   = None   # (list[dict],)
        self.game_name  = None
        self._last_event= ""

    def stop(self):
        self.running = False
        self.stop_event.set()

    def _begin_rejoin(self, inst, reason, fresh, delay):
        self._last_event = f"{inst['pkg'][-18:]}: {reason} — rejoining"
        log(self._last_event, "WARN")
        fire_webhook(self.cfg, f"{reason}:{inst['pkg']}")
        if fresh:
            kill_roblox(inst["pkg"])
        inst["crashes"] = 0; inst["reason"] = reason; inst["next_restart"] = None
        inst["launch_at"] = time.time() + max(0, delay)

    def _do_launch(self, inst):
        pk = inst["pkg"]; access = None; sm = self.cfg.get("server_mode", "off")
        if sm in ("highest", "lowest"):
            cookie = self.cfg.get("roblosecurity", "").strip()
            if cookie:
                self._last_event = f"{pk[-18:]}: fetching {sm} server..."
                code, count = get_servers(self.cfg["place_id"], cookie, mode=sm)
                if code: access = code
        ok = launch(self.cfg["place_id"], access_code=access, pkg=pk)
        now = time.time()
        inst["launch_at"] = None; inst["start"] = now; inst["crashes"] = 0
        inst["busy_until"] = now + self.cfg["rejoin_cooldown"]
        inst["next_restart"] = (now + self.cfg["restart_seconds"]
                                if self.cfg.get("auto_restart") else None)
        inst["reason"] = None; inst["seq_confirm"] = None
        self._last_event = f"{pk[-18:]}: launched" + ("" if ok else " (FAILED)")
        log(self._last_event, "OK" if ok else "ERROR")

    def _notify(self, insts, running):
        if self.on_insts:
            now = time.time()
            data = []
            for inst in insts:
                ram_mb, rcpu, pid = get_instance_stats(inst["pkg"])
                status = inst_status(inst, running)
                up = _seconds_to_str(now - inst["start"]) if inst["start"] and status != "OFFLINE" else "—"
                data.append({
                    "pkg": inst["pkg"], "status": status,
                    "ram_mb": ram_mb, "cpu": rcpu, "uptime": up,
                    "crashes": inst["crashes"], "event": self._last_event,
                })
            Clock.schedule_once(lambda dt: self.on_insts(data), 0)

    def run(self):
        cfg = self.cfg
        pkgs = [p for p in (cfg.get("packages") or [ROBLOX_PKG]) if _PKG_RE.match(p)] or [ROBLOX_PKG]
        set_sampler_packages(pkgs)
        self._last_event = "seeding cpu…"; log("Monitor starting, warming CPU...", "INFO")
        _warmup_cpu()
        single = len(pkgs) == 1
        if single: clear_flags()
        start_time = time.time(); _session_start[0] = start_time
        stagger = max(0, int(cfg.get("launch_stagger", 15)))
        insts = []
        for i, pk in enumerate(pkgs):
            insts.append({
                "pkg": pk,
                "launch_at": start_time + (0 if cfg.get("seq_join", True) else i * stagger),
                "busy_until": 0, "crashes": 0, "start": None,
                "next_restart": None, "reason": None, "hook_at": None,
                "idle_count": 0,
            })
        INSTANCES[:] = insts
        threading.Thread(target=lambda: setattr(self, "game_name", get_game_name(cfg["place_id"])),
                         daemon=True).start()
        start_time_ref = [start_time]
        if cfg.get("webhook_enabled") and cfg.get("webhook_url"):
            threading.Thread(target=_webhook_loop,
                             args=(cfg, self.stop_event, start_time_ref), daemon=True).start()
        last_overload = 0.0
        log(f"Monitoring {len(pkgs)} instance(s) for place {cfg['place_id']}", "OK")
        while self.running:
            try:
                now = time.time()
                ram = get_ram(); cpu = get_cpu()
                if self.on_stats:
                    Clock.schedule_once(lambda dt: self.on_stats(cpu, ram), 0)
                running = get_running_set(pkgs)
                # disconnect flag
                if single and cfg["watch_flag"]:
                    found, reason, _ = check_flag()
                    if found and insts[0]["launch_at"] is None and now >= insts[0]["busy_until"]:
                        clear_flags(); self._begin_rejoin(insts[0], f"flag:{reason}", False, 0)
                for inst in insts:
                    pk = inst["pkg"]
                    if inst["launch_at"] is not None:
                        if now >= inst["launch_at"] and _seq_can_launch(cfg, inst, insts, running, now):
                            self._do_launch(inst)
                        continue
                    if inst.get("hook_at") and now >= inst["hook_at"]:
                        inst["hook_at"] = None; fire_webhook(cfg, f"rejoined:{pk}")
                    if now < inst["busy_until"]: continue
                    if inst["next_restart"] and now >= inst["next_restart"]:
                        self._begin_rejoin(inst, "auto_restart", True, 0); continue
                    if (cfg.get("heartbeat") and pk in running
                            and now >= inst["busy_until"] + cfg.get("hb_grace", 30)):
                        hb = _hb_state(cfg, pk)
                        if hb is not None:
                            lost = (now - hb[0]) > cfg.get("hb_timeout", 45)
                            disc = hb[1] == "disconnect"
                            if lost or disc:
                                _fr = (now - inst.get("last_lobby", 0)) < 300
                                inst["last_lobby"] = now
                                self._begin_rejoin(inst, "disconnected" if disc else "heartbeat lost",
                                                   _fr, cfg["crash_delay"] if _fr else 0)
                                continue
                    if pk not in running:
                        inst["crashes"] += 1; inst["idle_count"] = 0
                        self._last_event = (f"{pk[-18:]}: not running "
                                            f"({inst['crashes']}/{cfg['crash_confirm']})")
                        if inst["crashes"] >= cfg["crash_confirm"]:
                            self._begin_rejoin(inst, "crash", True, cfg["crash_delay"])
                    else:
                        if inst["crashes"] > 0:
                            self._last_event = f"{pk[-18:]}: running ✓"
                        inst["crashes"] = 0
                        _, rcpu, _ = get_instance_stats(pk)
                        busy_secs = now - inst["busy_until"] if inst["busy_until"] else 999
                        if rcpu < cfg.get("lobby_cpu", 4.0) and busy_secs > cfg.get("lobby_idle_wait", 30):
                            inst["idle_count"] = inst.get("idle_count", 0) + 1
                            if inst["idle_count"] >= cfg.get("lobby_idle_count", 4):
                                self._last_event = f"{pk[-18:]}: stuck on lobby"
                                inst["idle_count"] = 0
                                _fr = (now - inst.get("last_lobby", 0)) < 300
                                inst["last_lobby"] = now
                                self._begin_rejoin(inst, "lobby", _fr, cfg["crash_delay"] if _fr else 0)
                        else:
                            inst["idle_count"] = 0
                # RAM overload — kill worst offender only (same as original)
                if (ram >= cfg["ram_limit"]
                        and now - last_overload >= max(60, cfg["rejoin_cooldown"] * 2)):
                    cands = [i for i in insts
                             if i["launch_at"] is None and now >= i["busy_until"] and i["pkg"] in running]
                    if cands:
                        worst = max(cands, key=lambda i: get_instance_stats(i["pkg"])[0])
                        self._begin_rejoin(worst, f"ram({ram:.0f}%)", True, 0)
                        last_overload = time.time()
                self._notify(insts, running)
            except Exception:
                log(traceback.format_exc(), "ERROR")
            time.sleep(cfg["check_interval"])
        log("Monitor stopped.", "INFO")

# ─────────────────────────────────────────────────────────────────────────────
#  UI HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def lbl(text="", size=13, color=C_TEXT, bold=False, halign="left", **kw):
    l = Label(text=text, font_size=dp(size), color=color, bold=bold,
              halign=halign, valign="middle", **kw)
    l.bind(size=l.setter("text_size"))
    return l

def btn(text, bg=C_ACCENT, fg=C_TEXT, size=13, **kw):
    return Button(text=text, font_size=dp(size), color=fg,
                  background_normal="", background_color=bg, **kw)

class Panel(BoxLayout):
    def __init__(self, bg=C_PANEL, radius=6, **kw):
        super().__init__(**kw)
        self._bg = bg; self._r = radius
        self.bind(pos=self._draw, size=self._draw)
    def _draw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self._bg)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[self._r])

STATUS_COL = {
    "INGAME":    C_GREEN,
    "LAUNCHING": C_YELLOW,
    "LOBBY":     C_ORANGE,
    "CHECKING":  C_YELLOW,
    "OFFLINE":   C_RED,
}

# ─────────────────────────────────────────────────────────────────────────────
#  INSTANCE CARD
# ─────────────────────────────────────────────────────────────────────────────
class InstCard(Panel):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", size_hint_y=None, height=dp(80),
                         padding=dp(8), spacing=dp(4), **kw)
        row1 = BoxLayout(spacing=dp(6))
        self._dot    = Label(text="●", font_size=dp(16), color=C_SUBTEXT,
                             size_hint=(None, 1), width=dp(20))
        self._name   = lbl("—", size=12, bold=True)
        self._status = lbl("—", size=11, color=C_SUBTEXT, halign="right")
        row1.add_widget(self._dot); row1.add_widget(self._name); row1.add_widget(self._status)
        row2 = BoxLayout(spacing=dp(10))
        self._ram  = lbl("RAM —", size=11, color=C_SUBTEXT)
        self._cpu  = lbl("CPU —", size=11, color=C_SUBTEXT)
        self._up   = lbl("UP —",  size=11, color=C_SUBTEXT)
        row2.add_widget(self._ram); row2.add_widget(self._cpu); row2.add_widget(self._up)
        self.add_widget(row1); self.add_widget(row2)

    def update(self, d):
        col = STATUS_COL.get(d["status"], C_SUBTEXT)
        self._dot.color    = col
        self._name.text    = d["pkg"][-26:]
        self._status.text  = d["status"]
        self._status.color = col
        self._ram.text     = f"RAM {d['ram_mb']} MB"
        self._cpu.text     = f"CPU {d['cpu']:.1f}%"
        self._up.text      = f"UP {d['uptime']}"

# ─────────────────────────────────────────────────────────────────────────────
#  DASHBOARD SCREEN
# ─────────────────────────────────────────────────────────────────────────────
class DashboardScreen(Screen):
    def __init__(self, app_ref, **kw):
        super().__init__(name="dashboard", **kw)
        self.app = app_ref
        root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        with root.canvas.before:
            Color(*C_BG); self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda o,v: setattr(self._bg,"pos",v),
                  size=lambda o,v: setattr(self._bg,"size",v))

        # ── header ──────────────────────────────────────────────────────────
        hdr = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self._title = lbl("🎮 Roblox Auto-Rejoin v5.5", size=15, bold=True)
        b_set = btn("⚙", bg=C_PANEL, size=15, size_hint=(None,1), width=dp(40))
        b_set.bind(on_press=lambda _: self._goto("settings"))
        b_log = btn("📋", bg=C_PANEL, size=15, size_hint=(None,1), width=dp(40))
        b_log.bind(on_press=lambda _: self._goto("logview"))
        hdr.add_widget(self._title); hdr.add_widget(b_set); hdr.add_widget(b_log)
        root.add_widget(hdr)

        # ── system stats ────────────────────────────────────────────────────
        stats = Panel(orientation="horizontal", size_hint_y=None,
                      height=dp(68), padding=dp(10), spacing=dp(14))
        self._cpu_lbl = lbl("CPU\n—%", size=13, halign="center", color=C_GREEN)
        self._ram_lbl = lbl("RAM\n—%", size=13, halign="center", color=C_ACCENT)
        self._cpu_bar = ProgressBar(max=100, value=0, size_hint=(1,None), height=dp(6))
        self._ram_bar = ProgressBar(max=100, value=0, size_hint=(1,None), height=dp(6))
        for (lbl_w, bar_w) in ((self._cpu_lbl, self._cpu_bar),
                               (self._ram_lbl, self._ram_bar)):
            col = BoxLayout(orientation="vertical", spacing=dp(4))
            col.add_widget(lbl_w); col.add_widget(bar_w)
            stats.add_widget(col)
        root.add_widget(stats)

        # ── game name + place id ─────────────────────────────────────────
        self._game_lbl = lbl("—", size=12, color=C_SUBTEXT,
                              size_hint_y=None, height=dp(20))
        root.add_widget(self._game_lbl)

        # ── start / stop ─────────────────────────────────────────────────
        ctrl = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        self.b_start = btn("▶  START", bg=C_START, size=14)
        self.b_stop  = btn("■  STOP",  bg=C_STOP,  size=14)
        self.b_start.bind(on_press=lambda _: self.app.engine_start())
        self.b_stop.bind( on_press=lambda _: self.app.engine_stop())
        ctrl.add_widget(self.b_start); ctrl.add_widget(self.b_stop)
        root.add_widget(ctrl)

        # ── instance cards ───────────────────────────────────────────────
        root.add_widget(lbl("Instances", size=11, bold=True, color=C_SUBTEXT,
                             size_hint_y=None, height=dp(20)))
        self._cards_box = BoxLayout(orientation="vertical", spacing=dp(6),
                                    size_hint_y=None)
        self._cards_box.bind(minimum_height=self._cards_box.setter("height"))
        sv_inst = ScrollView(size_hint=(1, 0.45))
        sv_inst.add_widget(self._cards_box)
        root.add_widget(sv_inst)
        self._cards = []

        # ── log strip ────────────────────────────────────────────────────
        root.add_widget(lbl("Last event", size=11, bold=True, color=C_SUBTEXT,
                             size_hint_y=None, height=dp(18)))
        self._event_lbl = lbl("—", size=11, color=C_SUBTEXT)
        log_panel = Panel(size_hint_y=None, height=dp(50), padding=(dp(6), dp(4)))
        log_panel.add_widget(self._event_lbl)
        root.add_widget(log_panel)

        self.add_widget(root)

    def _goto(self, name):
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current    = name

    def update_stats(self, cpu, ram):
        cc = C_GREEN if cpu < 70 else (C_YELLOW if cpu < 85 else C_RED)
        rc = C_GREEN if ram < 70 else (C_YELLOW if ram < 80 else C_RED)
        self._cpu_lbl.text  = f"CPU\n{cpu}%"; self._cpu_lbl.color = cc
        self._ram_lbl.text  = f"RAM\n{ram}%"; self._ram_lbl.color = rc
        self._cpu_bar.value = cpu; self._ram_bar.value = ram

    def update_instances(self, data_list):
        # Rebuild cards when count changes
        if len(data_list) != len(self._cards):
            self._cards_box.clear_widgets(); self._cards.clear()
            for _ in data_list:
                c = InstCard(); self._cards.append(c); self._cards_box.add_widget(c)
        for card, d in zip(self._cards, data_list):
            card.update(d)
        if data_list:
            ev = data_list[-1].get("event", "—")
            self._event_lbl.text = ev[-100:]

    def update_game_name(self, name, place_id):
        self._game_lbl.text = f"{name or 'Roblox'}  ·  Place {place_id}"

# ─────────────────────────────────────────────────────────────────────────────
#  LOG VIEW SCREEN
# ─────────────────────────────────────────────────────────────────────────────
class LogViewScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name="logview", **kw)
        root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        with root.canvas.before:
            Color(*C_BG); self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda o,v: setattr(self._bg,"pos",v),
                  size=lambda o,v: setattr(self._bg,"size",v))
        hdr = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        b_back = btn("← Back", bg=C_PANEL, size=12, size_hint=(None,1), width=dp(80))
        b_back.bind(on_press=lambda _: self._back())
        b_clear = btn("Clear", bg=C_PANEL2, size=12, size_hint=(None,1), width=dp(70))
        b_clear.bind(on_press=lambda _: self.clear())
        hdr.add_widget(b_back); hdr.add_widget(lbl("Log", size=15, bold=True))
        hdr.add_widget(b_clear)
        root.add_widget(hdr)
        sv = ScrollView(size_hint=(1,1))
        self._log_lbl = Label(text="", font_size=dp(10), color=C_SUBTEXT,
                               halign="left", valign="top", size_hint_y=None,
                               markup=False)
        self._log_lbl.bind(texture_size=self._log_lbl.setter("size"))
        sv.add_widget(self._log_lbl)
        root.add_widget(sv)
        self._sv = sv
        self.add_widget(root)
        self._lines = []

    def _back(self):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current    = "dashboard"

    def append(self, line):
        self._lines.append(line)
        if len(self._lines) > 400:
            self._lines = self._lines[-300:]
        self._log_lbl.text = "\n".join(self._lines)
        Clock.schedule_once(lambda dt: setattr(self._sv, "scroll_y", 0), 0.05)

    def clear(self):
        self._lines.clear(); self._log_lbl.text = ""

# ─────────────────────────────────────────────────────────────────────────────
#  SETTINGS SCREEN
# ─────────────────────────────────────────────────────────────────────────────
class SettingsScreen(Screen):
    def __init__(self, app_ref, **kw):
        super().__init__(name="settings", **kw)
        self.app = app_ref
        root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        with root.canvas.before:
            Color(*C_BG); self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda o,v: setattr(self._bg,"pos",v),
                  size=lambda o,v: setattr(self._bg,"size",v))
        hdr = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        b_back = btn("← Back", bg=C_PANEL, size=12, size_hint=(None,1), width=dp(80))
        b_back.bind(on_press=lambda _: self._back())
        hdr.add_widget(b_back); hdr.add_widget(lbl("Settings", size=15, bold=True))
        root.add_widget(hdr)
        sv = ScrollView(size_hint=(1,1))
        form = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None, padding=(0,dp(4)))
        form.bind(minimum_height=form.setter("height"))
        self._fields = {}
        cfg = self.app.config

        def field(label, key, hint="", num=False):
            row = Panel(orientation="vertical", size_hint_y=None, height=dp(70),
                        padding=dp(8), spacing=dp(4))
            row.add_widget(lbl(label, size=11, color=C_SUBTEXT, size_hint_y=None, height=dp(18)))
            ti = TextInput(text=str(cfg.get(key, "")), hint_text=hint, multiline=False,
                           font_size=dp(12), background_color=C_BG, foreground_color=C_TEXT,
                           cursor_color=C_ACCENT,
                           input_type="number" if num else "text",
                           size_hint_y=None, height=dp(36))
            self._fields[key] = ti; row.add_widget(ti); form.add_widget(row)

        def switch_row(label, key):
            row = Panel(orientation="horizontal", size_hint_y=None, height=dp(50),
                        padding=dp(8), spacing=dp(8))
            row.add_widget(lbl(label, size=12))
            sw = Switch(active=bool(cfg.get(key, False)), size_hint=(None,1), width=dp(60))
            self._fields[key] = sw; row.add_widget(sw); form.add_widget(row)

        field("Place ID",              "place_id",      hint="e.g. 1234567890")
        field("Packages (comma-sep.)", "packages_str",  hint="com.roblox.client,free.nokaA")
        field("Check interval (s)",    "check_interval",hint="5",  num=True)
        field("Rejoin cooldown (s)",   "rejoin_cooldown",hint="25", num=True)
        field("Crash delay (s)",       "crash_delay",   hint="30", num=True)
        field("Crash confirm checks",  "crash_confirm", hint="3",  num=True)
        field("RAM limit (%)",         "ram_limit",     hint="90", num=True)
        field("Auto restart (s, 0=off)","restart_seconds",hint="7200", num=True)
        field("Launch stagger (s)",    "launch_stagger",hint="15", num=True)
        field("Lobby CPU limit (%)",   "lobby_cpu",     hint="4.0")
        field("Lobby idle checks",     "lobby_idle_count",hint="4",num=True)
        field("Lobby idle wait (s)",   "lobby_idle_wait",hint="30",num=True)
        field("Seq join gap (s)",      "seq_gap",       hint="5",  num=True)
        field("Seq join timeout (s)",  "seq_timeout",   hint="150",num=True)
        field("HB timeout (s)",        "hb_timeout",    hint="45", num=True)
        field("HB grace (s)",          "hb_grace",      hint="30", num=True)
        field("HB account names",      "hb_ids_str",    hint="acc1,acc2")
        field("Discord Webhook URL",   "webhook_url",   hint="https://discord.com/api/webhooks/…")
        field("Webhook interval (s)",  "webhook_interval",hint="60",num=True)
        field("Server mode",           "server_mode",   hint="off / highest / lowest")
        field(".ROBLOSECURITY cookie", "roblosecurity",  hint="paste cookie value")
        switch_row("Auto restart",     "auto_restart")
        switch_row("Watch disconnect flag","watch_flag")
        switch_row("Sequential join",  "seq_join")
        switch_row("Heartbeat (executor)","heartbeat")
        switch_row("Webhook enabled",  "webhook_enabled")

        # populate package/hb_ids str fields
        self._fields["packages_str"].text = ",".join(cfg.get("packages") or [ROBLOX_PKG])
        self._fields["hb_ids_str"].text   = ",".join(cfg.get("hb_ids") or [])

        form.add_widget(BoxLayout(size_hint_y=None, height=dp(6)))
        b_save = btn("💾  Save & Apply", bg=C_START, size=14, size_hint_y=None, height=dp(50))
        b_save.bind(on_press=lambda _: self._save())
        form.add_widget(b_save)
        sv.add_widget(form); root.add_widget(sv)
        self.add_widget(root)

    def _back(self):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current    = "dashboard"

    def refresh(self):
        """Pull current config values into fields (call before showing screen)."""
        cfg = self.app.config
        int_keys = {"check_interval","rejoin_cooldown","crash_delay","crash_confirm",
                    "restart_seconds","launch_stagger","lobby_idle_count","lobby_idle_wait",
                    "seq_gap","seq_timeout","hb_timeout","hb_grace","webhook_interval"}
        float_keys = {"ram_limit","lobby_cpu"}
        bool_keys  = {"auto_restart","watch_flag","seq_join","heartbeat","webhook_enabled"}
        for key, widget in self._fields.items():
            if key == "packages_str":
                widget.text = ",".join(cfg.get("packages") or [ROBLOX_PKG])
            elif key == "hb_ids_str":
                widget.text = ",".join(cfg.get("hb_ids") or [])
            elif isinstance(widget, Switch):
                widget.active = bool(cfg.get(key, False))
            else:
                widget.text = str(cfg.get(key, ""))

    def _save(self):
        cfg = self.app.config
        int_keys   = {"check_interval","rejoin_cooldown","crash_delay","crash_confirm",
                      "restart_seconds","launch_stagger","lobby_idle_count","lobby_idle_wait",
                      "seq_gap","seq_timeout","hb_timeout","hb_grace","webhook_interval"}
        float_keys = {"ram_limit","lobby_cpu"}
        for key, widget in self._fields.items():
            if key in ("packages_str", "hb_ids_str"):
                continue
            if isinstance(widget, Switch):
                cfg[key] = widget.active
            else:
                val = widget.text.strip()
                if key in int_keys:
                    try: cfg[key] = int(float(val))
                    except: pass
                elif key in float_keys:
                    try: cfg[key] = float(val)
                    except: pass
                else:
                    cfg[key] = val
        # packages & hb_ids
        raw_pkgs = self._fields["packages_str"].text.strip()
        cfg["packages"] = [p.strip() for p in raw_pkgs.split(",") if _PKG_RE.match(p.strip())] or [ROBLOX_PKG]
        raw_hb = self._fields["hb_ids_str"].text.strip()
        cfg["hb_ids"] = [x.strip() for x in raw_hb.split(",") if x.strip()]
        save_config(cfg)
        if self.app.monitor_thread and self.app.monitor_thread.running:
            self.app.monitor_thread.cfg = cfg
        p = Popup(title="Saved", content=Label(text="Settings saved.", color=C_TEXT),
                  size_hint=(0.55, 0.22), background_color=C_PANEL)
        p.open(); Clock.schedule_once(lambda dt: p.dismiss(), 1.4)
        self._back()

# ─────────────────────────────────────────────────────────────────────────────
#  MAIN APP
# ─────────────────────────────────────────────────────────────────────────────
class RobloxRejoinApp(App):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.config         = load_config()
        self.monitor_thread = None

    def build(self):
        Window.clearcolor = C_BG
        self.sm = ScreenManager()
        self.dash     = DashboardScreen(app_ref=self)
        self.settings = SettingsScreen(app_ref=self)
        self.logview  = LogViewScreen()
        for s in (self.dash, self.settings, self.logview):
            self.sm.add_widget(s)
        self.sm.current = "dashboard"
        # route log lines to logview
        _log_listeners.append(self.logview.append)
        return self.sm

    def engine_start(self):
        if self.monitor_thread and self.monitor_thread.running:
            return
        cfg = self.config
        if not cfg.get("place_id", "").strip():
            p = Popup(title="No Place ID",
                      content=Label(text="Set a Place ID in Settings first.", color=C_TEXT),
                      size_hint=(0.7, 0.25), background_color=C_PANEL)
            p.open(); Clock.schedule_once(lambda dt: p.dismiss(), 2.5)
            return
        self.monitor_thread = MonitorThread(cfg)
        self.monitor_thread.on_stats = self.dash.update_stats
        self.monitor_thread.on_insts = self._on_insts
        self.monitor_thread.start()
        self.dash.b_start.background_color = C_SUBTEXT
        self.dash.b_stop.background_color  = C_STOP
        # kick off game name lookup
        threading.Thread(target=self._fetch_game_name, daemon=True).start()

    def _fetch_game_name(self):
        name = get_game_name(self.config.get("place_id", ""))
        Clock.schedule_once(
            lambda dt: self.dash.update_game_name(name, self.config.get("place_id", "")), 0
        )

    def _on_insts(self, data):
        self.dash.update_instances(data)

    def engine_stop(self):
        if self.monitor_thread:
            self.monitor_thread.stop()
            self.monitor_thread = None
        self.dash.b_start.background_color = C_START
        self.dash.b_stop.background_color  = C_SUBTEXT

    def on_stop(self):
        self.engine_stop()


if __name__ == "__main__":
    RobloxRejoinApp().run()
