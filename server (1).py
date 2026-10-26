from flask import Flask, request, jsonify, redirect
import sqlite3, uuid, datetime, os

app = Flask(__name__)
DB = "keys.db"
LOOTLABS_LINK = "https://lootdest.org/s?hS0NSp0j"
SERVER_URL = "https://YOUR_TUNNEL_URL"  # this gets updated each time you start tunnel

def init_db():
    con = sqlite3.connect(DB); c = con.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS keys(key TEXT PRIMARY KEY, discord_id TEXT, created_at TEXT, expires_at TEXT, redeemed INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS verified_users(discord_id TEXT PRIMARY KEY, verified_at TEXT)")
    con.commit(); con.close()

init_db()

def get_db(): return sqlite3.connect(DB)
def gen_key(): return "ZEROX-" + str(uuid.uuid4()).upper().replace("-","")[:20]

@app.route("/getkey")
def getkey():
    did = request.args.get("id")
    if not did: return "Missing ID", 400
    return redirect(LOOTLABS_LINK)

@app.route("/verify")
def verify():
    did = request.args.get("id")
    if not did:
        return """
        <html><head><title>ZERO X Verify</title></head>
        <body style='background:#111;color:#fff;font-family:sans-serif;text-align:center;padding:50px'>
        <h1 style='color:#7289da'>🔑 ZERO X Key System</h1>
        <h2>✅ Ads Complete!</h2>
        <p>Enter your Discord ID below to claim your key:</p>
        <form method='POST' action='/verify_submit'>
        <input name='discord_id' placeholder='Your Discord ID e.g. 123456789' 
        style='padding:12px;font-size:16px;width:300px;margin:10px;background:#222;color:#fff;border:1px solid #7289da;border-radius:5px'><br>
        <input type='submit' value='🔑 Get My Key' 
        style='padding:12px 30px;background:#7289da;color:#fff;border:none;font-size:16px;cursor:pointer;border-radius:5px;margin-top:10px'>
        </form>
        <p style='color:#888;font-size:12px;margin-top:20px'>
        To find your Discord ID:<br>
        Discord Settings → Advanced → Enable Developer Mode<br>
        Then right click your username → Copy ID
        </p>
        </body></html>
        """
    return verify_user(did)

@app.route("/verify_submit", methods=["POST"])
def verify_submit():
    did = request.form.get("discord_id", "").strip()
    if not did or not did.isdigit():
        return """
        <html><body style='background:#111;color:#fff;text-align:center;padding:50px'>
        <h2>❌ Invalid Discord ID!</h2>
        <p>Please enter a valid Discord ID (numbers only)</p>
        <a href='/verify' style='color:#7289da'>← Try again</a>
        </body></html>
        """
    return verify_user(did)

def verify_user(did):
    con = get_db(); c = con.cursor()
    now = datetime.datetime.utcnow()
    c.execute("SELECT verified_at FROM verified_users WHERE discord_id=?", (did,))
    row = c.fetchone()
    if row:
        last = datetime.datetime.fromisoformat(row[0])
        if (now - last).total_seconds() < 43200:
            con.close()
            return """
            <html><body style='background:#111;color:#fff;font-family:sans-serif;text-align:center;padding:50px'>
            <h1 style='color:#7289da'>🔑 ZERO X Key System</h1>
            <h2>⏳ Already Verified!</h2>
            <p>You already have an active key!</p>
            <p>Go to Discord and use <b style='color:#7289da'>/redeem</b> to get it.</p>
            <p style='color:#888'>Keys expire every 12 hours.</p>
            </body></html>
            """
    key = gen_key()
    exp = (now + datetime.timedelta(hours=12)).isoformat()
    c.execute("DELETE FROM keys WHERE discord_id=?", (did,))
    c.execute("INSERT INTO keys VALUES(?,?,?,?,0)", (key, did, now.isoformat(), exp))
    c.execute("INSERT OR REPLACE INTO verified_users VALUES(?,?)", (did, now.isoformat()))
    con.commit(); con.close()
    return """
    <html><body style='background:#111;color:#fff;font-family:sans-serif;text-align:center;padding:50px'>
    <h1 style='color:#7289da'>🔑 ZERO X Key System</h1>
    <h2>✅ Verified Successfully!</h2>
    <p>Your key has been generated!</p>
    <p>Go to Discord and use <b style='color:#7289da'>/redeem</b> to get your key.</p>
    <p style='color:#888'>Key expires in 12 hours.</p>
    </body></html>
    """

@app.route("/getkey_for_discord")
def getkey_for_discord():
    did = request.args.get("id")
    if not did: return jsonify({"error": "Missing ID"}), 400
    con = get_db(); c = con.cursor()
    now = datetime.datetime.utcnow()
    c.execute("SELECT key, expires_at FROM keys WHERE discord_id=? AND redeemed=0", (did,))
    row = c.fetchone()
    if not row:
        con.close()
        return jsonify({"error": "No key found. Please verify first!"}), 404
    key, exp = row
    if now > datetime.datetime.fromisoformat(exp):
        c.execute("DELETE FROM keys WHERE discord_id=?", (did,))
        con.commit(); con.close()
        return jsonify({"error": "Key expired. Please verify again."}), 410
    c.execute("UPDATE keys SET redeemed=1 WHERE discord_id=?", (did,))
    con.commit(); con.close()
    return jsonify({"key": key, "expires_at": exp})

@app.route("/validate")
def validate():
    key = request.args.get("key")
    if not key: return jsonify({"valid": False, "reason": "No key"}), 400
    con = get_db(); c = con.cursor()
    now = datetime.datetime.utcnow()
    c.execute("SELECT expires_at, discord_id FROM keys WHERE key=?", (key,))
    row = c.fetchone()
    if not row:
        con.close()
        return jsonify({"valid": False, "reason": "Invalid key"})
    exp, did = row
    if now > datetime.datetime.fromisoformat(exp):
        c.execute("DELETE FROM keys WHERE key=?", (key,))
        con.commit(); con.close()
        return jsonify({"valid": False, "reason": "Key expired"})
    con.close()
    return jsonify({"valid": True, "discord_id": did, "expires_at": exp})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
