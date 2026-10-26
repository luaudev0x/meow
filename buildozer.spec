[app]

# ── Identity ──────────────────────────────────────────────────────────────────
title        = Roblox Auto-Rejoin
package.name = robloxrejoin
package.domain = com.yourname           # change this

source.dir  = .
source.include_exts = py,png,jpg,kv,atlas,json

version = 1.0.0

# ── Entry point ───────────────────────────────────────────────────────────────
# Buildozer looks for main.py automatically
# If your file is elsewhere: source.main = path/to/main.py

# ── Requirements ──────────────────────────────────────────────────────────────
# Buildozer fetches and compiles these inside its own build env.
# Local Kivy install is NOT required.
requirements = python3,kivy==2.3.0

# ── Orientation & display ─────────────────────────────────────────────────────
orientation  = portrait
fullscreen   = 0

# ── Android permissions ───────────────────────────────────────────────────────
# These go into the APK manifest.
# INTERNET         — Discord webhook via curl
# READ_EXTERNAL_STORAGE / WRITE_EXTERNAL_STORAGE — config + log on /sdcard
# FOREGROUND_SERVICE — keep the monitor alive in background
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,FOREGROUND_SERVICE,RECEIVE_BOOT_COMPLETED

# ── Android settings ──────────────────────────────────────────────────────────
android.minapi  = 26          # Android 8.0+ (am start deep-link works well here)
android.api     = 33
android.ndk     = 25b
android.sdk     = 33
android.ndk_api = 26

# Build in debug mode by default; use 'buildozer android release' for signed APK
android.debug   = 1

# Architecture — arm64-v8a covers virtually all modern Android phones
android.archs   = arm64-v8a

# ── python-for-android bootstrap ──────────────────────────────────────────────
# 'sdl2' is the standard Kivy bootstrap
p4a.bootstrap = sdl2

# ── Build dirs ────────────────────────────────────────────────────────────────
# Already redirected by your env export, but you can also pin it here:
# buildozer.home = /storage/emulated/0/buildozer_home

# ── Logging ───────────────────────────────────────────────────────────────────
log_level = 2      # 0=error 1=info 2=debug

# ── Icon & presplash (optional) ───────────────────────────────────────────────
# Drop a 512×512 icon.png in your project dir and uncomment:
# icon.filename     = %(source.dir)s/icon.png
# presplash.filename = %(source.dir)s/presplash.png

# ── Whitelist / blacklist extra modules ───────────────────────────────────────
# We only use stdlib + kivy; no extras needed.

[buildozer]

# Buildozer working directory (override with env var BUILDOZER_HOME too)
# Uncomment if you want it hardcoded instead of via export:
# home_dir = /storage/emulated/0/buildozer_home

# Warn if Android SDK/NDK not installed — buildozer will auto-download
android.accept_sdk_license = True
