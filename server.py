from flask import Flask, request, jsonify, redirect
import sqlite3
import uuid
import datetime
import os

app = Flask(__name__)
DB = "keys.db"
LOOTLABS_LINK = "https://lootdest.org/s?xe29pTXR"
SERVER_URL = "http://YOUR_CLOUD_PHONE_IP:5000"  # Change this to your cloud phone IP

# ── Database setup ──────────────────────────────────────────
def init_db():
    con = sqlite3.connect(DB)
    c = con.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS keys (
            key TEXT PRIMARY KEY,
            discord_id TEXT,
            created_at TEXT,
            expires_at TEXT,
            redeemed INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS verified_users (
            discord_id TEXT PRIMARY KEY,
            verified_at TEXT
        )
    """)
    con.commit()
    con.close()

init_db()

# ── Helper ───────────────────────────────────────────────────
def get_db():
    return sqlite3.connect(DB)

def generate_key():
    return "ZEROX-" + str(uuid.uuid4()).upper().replace("-", "")[:20]

# ── Routes ───────────────────────────────────────────────────

# Step 1: User visits this to start verification
@app.route("/getkey")
def getkey():
    discord_id = request.args.get("id")
    if not discord_id:
        return "Missing Discord ID", 400
    # Send them to LootLabs, after they finish it redirects back to /verify
    callback = f"{SERVER_URL}/verify?id={discord_id}"
    return redirect(f"{LOOTLABS_LINK}&r={callback}")

# Step 2: LootLabs redirects here after ads are watched
@app.route("/verify")
def verify():
    discord_id = request.args.get("id")
    if not discord_id:
        return "Missing Discord ID", 400

    con = get_db()
    c = con.cursor()

    # Check if already verified recently (prevent spam)
    c.execute("SELECT verified_at FROM verified_users WHERE discord_id=?", (discord_id,))
    row = c.fetchone()

    now = datetime.datetime.utcnow()

    if row:
        last = datetime.datetime.fromisoformat(row[0])
        diff = now - last
        if diff.total_seconds() < 43200:  # 12 hours
            con.close()
            return f"""
            <html><body style='background:#111;color:#fff;font-family:sans-serif;text-align:center;padding:50px'>
            <h2>⏳ Already Verified!</h2>
            <p>You already got a key recently. Keys expire every 12 hours.</p>
            <p>Use <b>/redeem</b> in Discord to get your key.</p>
            </body></html>
            """, 200

    # Generate new key
    key = generate_key()
    expires_at = (now + datetime.timedelta(hours=12)).isoformat()

    # Delete old keys for this user
    c.execute("DELETE FROM keys WHERE discord_id=?", (discord_id,))

    # Insert new key
    c.execute("INSERT INTO keys VALUES (?,?,?,?,0)",
              (key, discord_id, now.isoformat(), expires_at))

    # Update verified_users
    c.execute("INSERT OR REPLACE INTO verified_users VALUES (?,?)",
              (discord_id, now.isoformat()))

    con.commit()
    con.close()

    return f"""
    <html><body style='background:#111;color:#fff;font-family:sans-serif;text-align:center;padding:50px'>
    <h2>✅ Verified Successfully!</h2>
    <p>Your key has been generated! Go to Discord and use:</p>
    <h3 style='color:#7289da'>/redeem</h3>
    <p>Your key will be sent to you privately.</p>
    <p style='color:#888'>Key expires in 12 hours.</p>
    </body></html>
    """

# Step 3: Discord bot calls this to get the key for a user
@app.route("/getkey_for_discord")
def getkey_for_discord():
    discord_id = request.args.get("id")
    if not discord_id:
        return jsonify({"error": "Missing ID"}), 400

    con = get_db()
    c = con.cursor()
    now = datetime.datetime.utcnow()

    c.execute("SELECT key, expires_at FROM keys WHERE discord_id=? AND redeemed=0", (discord_id,))
    row = c.fetchone()

    if not row:
        con.close()
        return jsonify({"error": "No key found. Please verify first at: " + SERVER_URL + "/getkey?id=" + discord_id}), 404

    key, expires_at = row
    expires = datetime.datetime.fromisoformat(expires_at)

    if now > expires:
        c.execute("DELETE FROM keys WHERE discord_id=?", (discord_id,))
        con.commit()
        con.close()
        return jsonify({"error": "Key expired. Please verify again."}), 410

    # Mark as redeemed
    c.execute("UPDATE keys SET redeemed=1 WHERE discord_id=?", (discord_id,))
    con.commit()
    con.close()

    return jsonify({"key": key, "expires_at": expires_at})

# Step 4: Rejoiner tool calls this to validate a key
@app.route("/validate")
def validate():
    key = request.args.get("key")
    if not key:
        return jsonify({"valid": False, "reason": "No key provided"}), 400

    con = get_db()
    c = con.cursor()
    now = datetime.datetime.utcnow()

    c.execute("SELECT expires_at, discord_id FROM keys WHERE key=?", (key,))
    row = c.fetchone()

    if not row:
        con.close()
        return jsonify({"valid": False, "reason": "Invalid key"})

    expires_at, discord_id = row
    expires = datetime.datetime.fromisoformat(expires_at)

    if now > expires:
        c.execute("DELETE FROM keys WHERE key=?", (key,))
        con.commit()
        con.close()
        return jsonify({"valid": False, "reason": "Key expired"})

    con.close()
    return jsonify({"valid": True, "discord_id": discord_id, "expires_at": expires_at})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
