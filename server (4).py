from flask import Flask, request, jsonify, redirect
import secrets
import string
import time
import os

app = Flask(__name__)

# In-memory stores (resets on Render restart, fine for 12hr keys)
pending_tokens = {}   # token -> {discord_id, created_at}
active_keys = {}      # key -> {discord_id, expires_at}

KEY_EXPIRY = 12 * 60 * 60      # 12 hours in seconds
TOKEN_EXPIRY = 10 * 60         # 10 minutes to complete LootLabs

LOOTLABS_LINK = "https://loot-link.com/s?1BwFRYFI"

def generate_key(length=24):
    chars = string.ascii_uppercase + string.digits
    return "ZEROX-" + "".join(secrets.choice(chars) for _ in range(length))


# ── Step 1: Bot calls this to create a pending session ──────────────────────
@app.route("/start")
def start():
    discord_id = request.args.get("discord_id")
    if not discord_id:
        return jsonify({"error": "Missing discord_id"}), 400

    token = secrets.token_urlsafe(16)
    pending_tokens[token] = {
        "discord_id": discord_id,
        "created_at": time.time()
    }

    # Redirect user to LootLabs; after they finish, LootLabs sends them to /verify
    verify_url = f"{request.host_url}verify?token={token}"
    # Build the full LootLabs URL with destination override if supported,
    # otherwise just redirect — LootLabs destination is pre-set to /verify endpoint
    return redirect(LOOTLABS_LINK)


# ── Step 2: LootLabs redirects here after user completes the ad ─────────────
@app.route("/verify")
def verify():
    token = request.args.get("token")
    if not token:
        return "Missing token.", 400

    now = time.time()

    # Clean up expired pending tokens
    expired = [t for t, v in pending_tokens.items() if now - v["created_at"] > TOKEN_EXPIRY]
    for t in expired:
        del pending_tokens[t]

    session = pending_tokens.pop(token, None)
    if not session:
        return "Token expired or invalid. Please run /getkey again.", 400

    discord_id = session["discord_id"]

    # Revoke any existing key for this user
    to_remove = [k for k, v in active_keys.items() if v["discord_id"] == discord_id]
    for k in to_remove:
        del active_keys[k]

    # Generate new key
    new_key = generate_key()
    active_keys[new_key] = {
        "discord_id": discord_id,
        "expires_at": now + KEY_EXPIRY
    }

    return f"""
    <html>
    <head><title>ZERO X Key System</title></head>
    <body style="background:#111;color:#fff;font-family:monospace;text-align:center;padding:60px">
        <h1>✅ Key Generated!</h1>
        <p>Your key (valid 12 hours):</p>
        <h2 style="color:#00ff88;letter-spacing:2px">{new_key}</h2>
        <p>Use <b>/redeem {new_key}</b> in the Discord bot.</p>
    </body>
    </html>
    """, 200


# ── Step 3: Bot calls this to validate a key ────────────────────────────────
@app.route("/checkkey")
def checkkey():
    key = request.args.get("key")
    if not key:
        return jsonify({"valid": False, "reason": "No key provided"}), 400

    now = time.time()

    # Clean up expired keys
    expired = [k for k, v in active_keys.items() if now > v["expires_at"]]
    for k in expired:
        del active_keys[k]

    entry = active_keys.get(key)
    if not entry:
        return jsonify({"valid": False, "reason": "Key not found or expired"})

    time_left = int(entry["expires_at"] - now)
    hours = time_left // 3600
    minutes = (time_left % 3600) // 60

    return jsonify({
        "valid": True,
        "discord_id": entry["discord_id"],
        "expires_in": f"{hours}h {minutes}m"
    })


# ── Health check ─────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return jsonify({"status": "ZERO X Key Server running"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
