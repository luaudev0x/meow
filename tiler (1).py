#!/usr/bin/env python3
"""
Roblox window tiler for Termux (root, Android 10 freeform).
Standalone: does not touch your rejoiner.

  python tiler.py              menu
  python tiler.py arrange      arrange once (saved layout if you have one, else auto grid)
  python tiler.py grid         arrange once using the auto grid, ignoring the saved layout
  python tiler.py save         save current window positions as your layout
  python tiler.py diag         test every resize method and print what works
  python tiler.py diag2        inspect how this ROM's floating windows work
  python tiler.py loop         re-arrange every <interval> seconds
Add  --delay N  to wait N seconds first (time to open the clones / switch away).
"""
import os, sys, re, json, math, time, subprocess
from datetime import datetime

CFG_FILE = os.path.expanduser("~/tiler_config.json")
RJ_FILE = os.path.expanduser("~/roblox_config.json")   # rejoiner config (used for package list)
LOG_FILE = os.path.expanduser("~/tiler_log.txt")

DEF = {
    "packages": [],        # empty = take from rejoiner config, else auto-detect
    "cols": 0,             # 0 = auto
    "gap": 0,              # px between windows
    "top": 0,              # px margin top offset
    "drag_ms": 450,        # swipe duration (fallback method)
    "min_w": 0,            # minimum cell width (auto grid)
    "min_h": 0,            # minimum cell height (auto grid)
    "interval": 30,        # seconds, loop mode
    "orient": "auto",      # auto / landscape / portrait
    "layout": {},          # saved positions {pkg:[l,t,r,b]}
}


def c(t, code): return f"\033[{code}m{t}\033[0m"


def log(msg, show=True):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    if show: print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as f: f.write(line + "\n")
    except Exception: pass


def su(cmd, timeout=15):
    try:
        r = subprocess.run(["su", "-c", cmd], capture_output=True, text=True,
                           timeout=timeout, stdin=subprocess.DEVNULL)
        return (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return f"<error: {e}>"


def load_cfg():
    cfg = dict(DEF)
    try:
        with open(CFG_FILE) as f: cfg.update(json.load(f))
    except Exception: pass
    return cfg


def save_cfg(cfg):
    try:
        with open(CFG_FILE, "w") as f: json.dump(cfg, f, indent=2)
    except Exception as e:
        print("could not save config:", e)


# ───────────── packages ─────────────
PKG_RE = re.compile(r'^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+$')


def natural(s): return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]


def detect_packages():
    found = []
    out = su("pm list packages")
    for ln in out.splitlines():
        if ln.startswith("package:") and "roblox" in ln.lower():
            p = ln.split(":", 1)[1].strip()
            if PKG_RE.match(p) and p not in found: found.append(p)
    return sorted(found, key=natural)


def get_packages(cfg):
    if cfg["packages"]: return cfg["packages"]
    try:
        with open(RJ_FILE) as f:
            p = [x for x in json.load(f).get("packages", []) if PKG_RE.match(x)]
            if p: return p
    except Exception: pass
    return detect_packages()


# ───────────── screen / grid ─────────────
def screen_rect(orient="auto"):
    dw = su("dumpsys window displays")
    w = h = 0
    m = re.search(r'cur=(\d+)x(\d+)', dw)
    if m: w, h = int(m.group(1)), int(m.group(2))
    else:
        m = re.findall(r'(\d+)x(\d+)', su("wm size"))
        if m: w, h = int(m[-1][0]), int(m[-1][1])
    if not w or not h: w, h = 1080, 1920
    if (orient == "landscape" and w < h) or (orient == "portrait" and w > h):
        return (0, 0, h, w)
    rect = (0, 0, w, h)
    m = re.search(r'mStable=\[(\d+),(\d+)\]\[(\d+),(\d+)\]', dw)
    if m:
        l, t, r, b = map(int, m.groups())
        if 0 <= l < r <= w and 0 <= t < b <= h and (r - l) * (b - t) > 0.5 * w * h:
            rect = (l, t, r, b)
    return rect


def best_grid(n, W, H, cols_fixed=0, gap=0, min_w=0, min_h=0):
    opts = []
    for cols in ([min(max(1, cols_fixed), n)] if cols_fixed > 0 else range(1, n + 1)):
        rows = math.ceil(n / cols); waste = cols * rows - n
        cw = (W - gap * (cols - 1)) / cols; ch = (H - gap * (rows - 1)) / rows
        if cw <= 0 or ch <= 0: continue
        score = abs(math.log((cw / ch) / 1.78)) + 0.6 * waste / n
        opts.append((cw >= min_w and ch >= min_h, score, cols, rows, cw * ch))
    if not opts: return 1, n
    good = [o for o in opts if o[0]]
    best = min(good, key=lambda o: o[1]) if good else max(opts, key=lambda o: o[4])
    return best[2], best[3]


def grid_targets(pkgs, cfg):
    n = len(pkgs)
    L, T, R, B = screen_rect(cfg["orient"])
    T += cfg["top"]; W = R - L; H = B - T
    gap = cfg["gap"]
    cols, rows = best_grid(n, W, H, cfg["cols"], gap, cfg["min_w"], cfg["min_h"])
    res = {}
    for i, pk in enumerate(pkgs):
        r, col = divmod(i, cols)
        ncols = cols
        if r == rows - 1:                      # last row fills the full width
            ncols = n - (rows - 1) * cols; col = i - (rows - 1) * cols
        cw = (W - gap * (ncols - 1)) // ncols; ch = (H - gap * (rows - 1)) // rows
        l = L + col * (cw + gap); t = T + r * (ch + gap)
        res[pk] = [l, t, l + cw, t + ch]
    return res, (cols, rows, (L, T, R, B))


# ───────────── tasks / bounds ─────────────
def find_tasks(pkgs):
    out = su("dumpsys activity activities", timeout=25)
    res = {}
    for pk in pkgs:
        m = re.search(rf'ActivityRecord\{{[0-9a-f]+ u\d+ {re.escape(pk)}/\S+ t(\d+)', out)
        if m: res[pk] = m.group(1)
    return res


def read_bounds(pkgs, raw=None):
    out = raw if raw is not None else su("am stack list")
    res = {}
    for pk in pkgs:
        m = re.search(rf'taskId=\d+: {re.escape(pk)}/\S+ bounds=\[(\d+),(\d+)\]\[(\d+),(\d+)\]', out)
        if m: res[pk] = [int(x) for x in m.groups()]
    return res


def close(a, b, tol=40):
    return a is not None and all(abs(x - y) <= tol for x, y in zip(a, b))


def density_scale():
    m = re.findall(r'(\d+)', su("wm density"))
    try: return int(m[-1]) / 160.0
    except Exception: return 2.5


def swipe_place(cur, target, ms):
    dp = density_scale(); cl_, ct, cr, cb = cur; l, t, r, b = target
    gx = cl_ + (cr - cl_) // 2; gy = ct + int(14 * dp)
    su(f"input swipe {gx} {gy} {gx + (l - cl_)} {gy + (t - ct)} {ms}"); time.sleep(0.8)
    ex = l + (cr - cl_) - 4; ey = t + (cb - ct) - 4
    su(f"input swipe {ex} {ey} {r - 4} {b - 4} {ms}"); time.sleep(0.8)


def resize_task(pk, tid, target, ms, verbose=False):
    """Try every method; verify by re-reading bounds. Returns (method, ok)."""
    l, t, r, b = target
    su(f"am task resizeable {tid} 2")
    methods = [("am task resize", f"am task resize {tid} {l} {t} {r} {b}"),
               ("am task resize (csv)", f"am task resize {tid} {l},{t},{r},{b}"),
               ("cmd activity task resize", f"cmd activity task resize {tid} {l} {t} {r} {b}")]
    cur = read_bounds([pk]).get(pk)
    if close(cur, target): return "already placed", True
    for name, cmd in methods:
        o = su(cmd).strip(); time.sleep(0.7)
        cur = read_bounds([pk]).get(pk)
        log(f"    {name}: out={o[:120]!r} now={cur}", show=verbose)
        if close(cur, target): return name, True
    if cur is None: return "unverifiable (cannot read window bounds)", False
    swipe_place(cur, target, ms)
    cur = read_bounds([pk]).get(pk)
    log(f"    swipe drag: now={cur}", show=verbose)
    return "swipe drag", close(cur, target)


def setup_freeform():
    su("settings put global enable_freeform_support 1")
    su("settings put global force_resizable_activities 1")


# ───────────── actions ─────────────
def arrange(cfg, use_layout=True, verbose=True):
    pkgs = get_packages(cfg)
    if not pkgs:
        log(c("No Roblox packages found. Open menu > Packages.", "91")); return 0
    setup_freeform()
    targets, info = grid_targets(pkgs, cfg)
    if use_layout and cfg["layout"]:
        for pk in pkgs:
            if pk in cfg["layout"]: targets[pk] = cfg["layout"][pk]
    tasks = find_tasks(pkgs)
    log(f"screen usable {info[2]}  grid {info[0]}x{info[1]}  windows {len(tasks)}/{len(pkgs)}", show=verbose)
    ok_n = 0
    for pk in pkgs:
        if pk not in tasks:
            log(f"  {pk}: {c('no window found (is it open?)', '93')}", show=verbose); continue
        how, ok = resize_task(pk, tasks[pk], targets[pk], cfg["drag_ms"])
        log(f"  {pk}: {c(how, '92' if ok else '91')} {'OK' if ok else 'FAILED'}  -> {targets[pk]}", show=verbose)
        ok_n += ok
    return ok_n


def save_layout(cfg):
    pkgs = get_packages(cfg)
    b = read_bounds(pkgs)
    if not b:
        log(c("Could not read any window position. Run Diagnose and send me the output.", "91")); return
    cfg["layout"] = b; save_cfg(cfg)
    log(c(f"Saved layout for {len(b)}/{len(pkgs)} window(s):", "92"))
    for k, v in b.items(): print(f"   {k}: {v}")


def diag(cfg):
    pkgs = get_packages(cfg)
    log(c("── DIAGNOSE ─────────────────────────", "96"))
    log(f"android: {su('getprop ro.build.version.release').strip()}  sdk {su('getprop ro.build.version.sdk').strip()}")
    log(f"root (id): {su('id').strip()[:80]}")
    log(f"freeform setting: {su('settings get global enable_freeform_support').strip()}  "
        f"force_resizable: {su('settings get global force_resizable_activities').strip()}")
    log(f"packages: {pkgs}")
    L, T, R, B = screen_rect(cfg["orient"])
    log(f"usable screen: {(L, T, R, B)}   (wm size: {su('wm size').strip()!r})")
    log("'am task' subcommands on this phone:")
    for ln in su("am help").splitlines():
        if "task" in ln.lower(): log("    " + ln.strip()[:110])
    tasks = find_tasks(pkgs)
    log(f"task ids found: {tasks}")
    raw = su("am stack list")
    bounds = read_bounds(pkgs, raw)
    log(f"window bounds read: {bounds}")
    if not bounds:
        log(c("could not parse 'am stack list' for your packages. Raw lines mentioning roblox:", "93"))
        for ln in raw.splitlines():
            if "roblox" in ln.lower(): log("    " + ln.strip()[:200])
    if not tasks:
        log(c("No windows found. Open your clones first, then run diag again.", "91")); return
    targets, info = grid_targets(pkgs, cfg)
    log(f"test: moving each window to its grid cell (grid {info[0]}x{info[1]})")
    for pk, tid in tasks.items():
        log(f"  {pk} (task {tid}) -> {targets[pk]}")
        how, ok = resize_task(pk, tid, targets[pk], cfg["drag_ms"], verbose=True)
        log(f"  RESULT: {c(how, '92' if ok else '91')}  {'OK' if ok else 'FAILED'}")
    log(c(f"Done. Full log: {LOG_FILE}", "96"))


def grep_lines(text, pats, limit=25):
    rx = re.compile("|".join(pats), re.I)
    return [l.rstrip()[:150] for l in text.splitlines() if rx.search(l)][:limit]


def diag2(cfg):
    """Look at how this ROM does its floating windows. Run it while the clones are floating."""
    pkgs = get_packages(cfg)
    log(c("── DIAGNOSE 2: floating windows ─────", "96"))
    pk_rx = "|".join(re.escape(p) for p in pkgs) or "roblox"
    dw = su("dumpsys window windows", timeout=40)
    log("Roblox window frames (from the window manager):")
    shown = 0
    for b in re.split(r'\n(?=\s*Window #)', dw):
        head = b.split("\n", 1)[0]
        if re.search(pk_rx, head):
            log("  " + head.strip()[:120])
            for ln in grep_lines(b, [r"mFrame=", r"mWindowingMode", r"mBounds", r"mHScale", r"mGlobalScale"], 6):
                log("      " + ln.strip())
            shown += 1
    if not shown: log("  (no Roblox window found, were the clones open?)")
    ac = su("dumpsys activity activities", timeout=40)
    log("Roblox tasks (activity manager):")
    for pk, tid in find_tasks(pkgs).items():
        i = ac.find(f"#{tid} ")
        log(f"  {pk} task {tid}")
        for ln in grep_lines(ac[i:i + 3000] if i >= 0 else "", [r"mBounds", r"mWindowingMode", r"Stack"], 5):
            log("      " + ln.strip())
    allset = "\n".join(su(f"settings list {n}") for n in ("global", "system", "secure"))
    log("Settings that look window-related:")
    for ln in grep_lines(allset, [r"float", r"freeform", r"multi.?window", r"mini", r"bubble", r"free.?win"], 25): log("  " + ln)
    log("Packages that look window-related:")
    for ln in grep_lines(su("pm list packages"), [r"float", r"window", r"multi", r"vsphone", r"vmos", r"bubble", r"cloud"], 25): log("  " + ln)
    log("System services that look window-related:")
    for ln in grep_lines(su("cmd -l"), [r"float", r"window", r"multi", r"vs", r"vmos", r"bubble", r"free"], 25): log("  " + ln)
    log("Properties:")
    for ln in grep_lines(su("getprop"), [r"vsphone", r"vmos", r"float", r"freeform", r"multi", r"cloud"], 15): log("  " + ln)
    log(c(f"Done. Full log: {LOG_FILE}", "96"))


def loop(cfg):
    log(c(f"Loop mode: arranging every {cfg['interval']}s. Ctrl-C to stop.", "96"))
    try:
        while True:
            arrange(cfg, verbose=True)
            time.sleep(max(3, cfg["interval"]))
    except KeyboardInterrupt:
        print()


# ───────────── menu ─────────────
SETTINGS = [("cols", "Columns (0 = auto)", 0),
            ("gap", "Gap between windows, px", 0),
            ("top", "Margin top offset, px", 0),
            ("drag_ms", "Drag duration, ms (swipe fallback)", 100),
            ("min_w", "Minimum cell width, px (0 = none)", 0),
            ("min_h", "Minimum cell height, px (0 = none)", 0),
            ("interval", "Sort interval, seconds (loop mode)", 3)]


def ask(prompt, default=""):
    try:
        v = input(f"  {c('→', '96')} {prompt} [{c(str(default), '93')}]: ").strip()
        return v if v else str(default)
    except (EOFError, KeyboardInterrupt):
        print(); sys.exit(0)


def settings_menu(cfg):
    while True:
        os.system("clear")
        print(c("  ── Layout settings ──────────────────", "96"), "\n")
        for i, (k, label, mn) in enumerate(SETTINGS, 1):
            print(f"  {c(str(i), '95')}. {label:<40}{c(str(cfg[k]), '93')}")
        print(f"  {c('8', '95')}. {'Orientation (auto/landscape/portrait)':<40}{c(cfg['orient'], '93')}")
        print(f"  {c('0', '96')}. Back\n")
        ch = ask("Edit number", "0")
        if ch == "0": break
        if ch == "8":
            o = ask("Orientation", cfg["orient"]).lower()
            cfg["orient"] = o if o in ("auto", "landscape", "portrait") else "auto"
        else:
            try:
                k, label, mn = SETTINGS[int(ch) - 1]
                cfg[k] = max(mn, int(float(ask(label, cfg[k]))))
            except Exception: pass
        save_cfg(cfg)


def packages_menu(cfg):
    while True:
        os.system("clear")
        pk = get_packages(cfg)
        src = "your list" if cfg["packages"] else "rejoiner config / auto-detect"
        print(c(f"  ── Packages ({src}) ──", "96"), "\n")
        for i, p in enumerate(pk, 1): print(f"  {c(str(i), '95')}. {p}")
        print(f"\n  {c('A', '92')}. Auto-detect and use all Roblox packages")
        print(f"  {c('M', '92')}. Add manually")
        print(f"  {c('C', '93')}. Clear (back to rejoiner config / auto)")
        print(f"  {c('0', '96')}. Back\n")
        ch = ask("Option", "0").upper()
        if ch == "0": break
        elif ch == "A": cfg["packages"] = detect_packages()
        elif ch == "M":
            v = ask("Package name", "")
            if PKG_RE.match(v) and v not in cfg["packages"]:
                cfg["packages"] = (cfg["packages"] or list(pk)) + [v]
        elif ch == "C": cfg["packages"] = []
        save_cfg(cfg)


def menu(cfg):
    while True:
        os.system("clear")
        lay = f"{len(cfg['layout'])} saved" if cfg["layout"] else "none"
        print(c("\n  Roblox window tiler\n", "1;97"))
        print(f"  {c('1', '92')}. Arrange now            (saved layout: {lay})")
        print(f"  {c('2', '92')}. Arrange now with auto grid")
        print(f"  {c('3', '92')}. Save current positions as my layout")
        print(f"  {c('4', '93')}. Clear saved layout")
        print(f"  {c('5', '95')}. Layout settings")
        print(f"  {c('6', '95')}. Packages")
        print(f"  {c('7', '96')}. Diagnose (tests every method)")
        print(f"  {c('8', '96')}. Loop (re-arrange every {cfg['interval']}s)")
        print(f"  {c('9', '96')}. Diagnose 2 (how floating windows work)")
        print(f"  {c('0', '91')}. Exit\n")
        ch = ask("Option", "0")
        if ch == "0": break
        elif ch == "1": arrange(cfg); ask("Enter to continue", "")
        elif ch == "2": arrange(cfg, use_layout=False); ask("Enter to continue", "")
        elif ch == "3": save_layout(cfg); ask("Enter to continue", "")
        elif ch == "4": cfg["layout"] = {}; save_cfg(cfg)
        elif ch == "5": settings_menu(cfg)
        elif ch == "6": packages_menu(cfg)
        elif ch == "7": diag(cfg); ask("Enter to continue", "")
        elif ch == "8": loop(cfg)
        elif ch == "9": diag2(cfg); ask("Enter to continue", "")


def main():
    args = sys.argv[1:]
    delay = 0
    if "--delay" in args:
        i = args.index("--delay")
        try: delay = int(args[i + 1])
        except Exception: pass
        del args[i:i + 2]
    cfg = load_cfg()
    if delay:
        for s in range(delay, 0, -1):
            print(f"\r  starting in {s}s ", end="", flush=True); time.sleep(1)
        print()
    cmd = args[0] if args else "menu"
    if cmd == "arrange": arrange(cfg)
    elif cmd == "grid": arrange(cfg, use_layout=False)
    elif cmd == "save": save_layout(cfg)
    elif cmd == "diag": diag(cfg)
    elif cmd == "diag2": diag2(cfg)
    elif cmd == "loop": loop(cfg)
    else: menu(cfg)


if __name__ == "__main__":
    main()
