# ================================================================
# app_main.py — AvtoBozor Flask Backend (To'liq versiya)
# ================================================================
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import requests as http_req
import os, sqlite3, base64, random, logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = Flask(__name__, static_folder="static")
CORS(app)

# ── ENV ─────────────────────────────────────────────────────────
BOT_TOKEN      = os.getenv("BOT_TOKEN")
CHANNEL_ID     = os.getenv("CHANNEL_ID")
ADMIN_ID       = os.getenv("ADMIN_ID")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "@AvtoBozori_Admini")
DOMAIN         = os.getenv("DOMAIN", "")
MINI_APP_URL   = os.getenv("MINI_APP_URL", "")
GROUP_LINK     = os.getenv("GROUP_LINK", "")
UPLOAD_FOLDER  = os.getenv("UPLOAD_FOLDER", "static/uploads")
DB_PATH        = os.getenv("DB_PATH", "database.db")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs("static", exist_ok=True)

# ================================================================
# DATABASE
# ================================================================
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def _safe_col(conn, table, col_def):
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
    except Exception:
        pass

def init_db():
    c = get_db()
    c.execute('''CREATE TABLE IF NOT EXISTS ads (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER,
        model       TEXT,
        year        INTEGER,
        price       INTEGER,
        region      TEXT,
        mileage     INTEGER  DEFAULT 0,
        color       TEXT     DEFAULT "—",
        fuel_type   TEXT,
        phone       TEXT,
        description TEXT     DEFAULT "—",
        image_url   TEXT     DEFAULT "",
        tg_file_id  TEXT     DEFAULT "",
        tg_msg_id   INTEGER  DEFAULT 0,
        status      TEXT     DEFAULT "pending",
        is_auto     INTEGER  DEFAULT 0,
        lat         REAL,
        lng         REAL,
        vip_until   TIMESTAMP,
        ad_type     TEXT     DEFAULT "real",
        created_at  TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id           INTEGER PRIMARY KEY,
        first_name   TEXT,
        username     TEXT,
        phone        TEXT,
        invite_count INTEGER DEFAULT 0,
        created_at   TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS invites (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        inviter_id INTEGER,
        invitee_id INTEGER,
        created_at TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS services (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER,
        type        TEXT,
        name        TEXT,
        phone       TEXT,
        lat         REAL,
        lng         REAL,
        description TEXT,
        status      TEXT DEFAULT "pending",
        created_at  TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS parsed_messages (
        source_id TEXT,
        msg_id    INTEGER,
        created_at TEXT,
        PRIMARY KEY (source_id, msg_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS last_processed (
        source_id   TEXT PRIMARY KEY,
        last_msg_id INTEGER
    )''')
    for col in [
        "tg_file_id TEXT DEFAULT ''",
        "tg_msg_id INTEGER DEFAULT 0",
        "is_auto INTEGER DEFAULT 0",
        "lat REAL",
        "lng REAL",
        "vip_until TIMESTAMP",
        "ad_type TEXT DEFAULT 'real'"
    ]:
        _safe_col(c, "ads", col)
    _safe_col(c, "users", "invite_count INTEGER DEFAULT 0")
    c.commit()
    c.close()

init_db()

# ================================================================
# HELPERS
# ================================================================
def row_to_dict(row):
    d = dict(row)
    v = d.get("vip_until")
    try:
        d["vip"] = (datetime.strptime(v, "%Y-%m-%d %H:%M") > datetime.now()) if v else d.get("status") == "vip"
    except Exception:
        d["vip"] = d.get("status") == "vip"

    fid = d.get("tg_file_id", "")
    if fid:
        d["image"] = f"{DOMAIN}/api/tgfile/{fid}"
    else:
        d["image"] = d.get("image_url") or ""

    d["time"]    = d.get("created_at") or ""
    d["desc"]    = d.get("description") or "—"
    d["mileage"] = d.get("mileage") or 0
    d["color"]   = d.get("color") or "—"
    d["price"]   = d.get("price") or 0
    return d

def service_to_dict(row):
    d = dict(row)
    d["icon"] = {
        "shinomontaj": "🛞", "ustahona": "🛠", "zapravka": "⛽️", "zapchast": "⚙️"
    }.get(d["type"], "📍")
    return d

def tg_api(method, **kwargs):
    if not BOT_TOKEN:
        return None
    try:
        r = http_req.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
            timeout=15, **kwargs
        )
        return r.json()
    except Exception as e:
        logging.error(f"TG API {method}: {e}")
        return None

def channel_caption(ad: dict) -> str:
    vip_line = "⭐️ <b>VIP E'LON</b>\n\n" if ad.get("vip") else ""
    app_link = f"\n\n🌐 <a href='{MINI_APP_URL}'>Ilovada ko'rish</a>" if MINI_APP_URL else ""
    return (
        f"{vip_line}"
        f"🚗 <b>Model:</b> {ad.get('model','')} ({ad.get('year','')})\n"
        f"📟 <b>Yurgani:</b> {ad.get('mileage',0):,} km\n"
        f"⛽️ <b>Yoqilg'i:</b> {ad.get('fuel_type','—')}\n"
        f"🎨 <b>Rang:</b> {ad.get('color','—')}\n"
        f"💰 <b>Narxi:</b> <b>{ad.get('price',0):,}$</b>\n"
        f"📝 <b>Ma'lumot:</b> {ad.get('desc', ad.get('description','—'))}\n"
        f"📲 <b>Aloqa:</b> {ad.get('phone','')}\n\n"
        f"📍 <b>Hudud:</b> {ad.get('region','')}"
        f"{app_link}"
    )

def send_to_channel(ad: dict, image_b64: str = None):
    cap    = channel_caption(ad)
    kb     = {"inline_keyboard": [[{"text": "🌐 Ilovada ko'rish", "url": MINI_APP_URL}]]} if MINI_APP_URL else None
    result = {"tg_msg_id": 0, "tg_file_id": ""}

    if not CHANNEL_ID:
        return result

    if image_b64:
        tmp = os.path.join(UPLOAD_FOLDER, f"_tmp_{int(datetime.now().timestamp())}.jpg")
        try:
            raw = image_b64.split(",")[1] if "," in image_b64 else image_b64
            with open(tmp, "wb") as fh:
                fh.write(base64.b64decode(raw))
            with open(tmp, "rb") as ph:
                params = {
                    "chat_id": CHANNEL_ID,
                    "caption": cap[:1024],
                    "parse_mode": "HTML"
                }
                if kb:
                    import json as _json
                    params["reply_markup"] = _json.dumps(kb)
                resp = tg_api("sendPhoto", data=params, files={"photo": ph})
            if resp and resp.get("ok"):
                msg = resp["result"]
                result["tg_msg_id"]  = msg.get("message_id", 0)
                photos = msg.get("photo", [])
                result["tg_file_id"] = photos[-1]["file_id"] if photos else ""
        except Exception as e:
            logging.error(f"send_to_channel rasm: {e}")
        finally:
            try:
                os.remove(tmp)
            except Exception:
                pass
    else:
        import json as _json
        resp = tg_api("sendMessage", json={
            "chat_id": CHANNEL_ID,
            "text": cap[:4000],
            "parse_mode": "HTML",
            "reply_markup": kb,
            "disable_web_page_preview": False
        })
        if resp and resp.get("ok"):
            result["tg_msg_id"] = resp["result"].get("message_id", 0)

    return result

def admin_notify(ad_id, user_id, cap):
    if not (BOT_TOKEN and ADMIN_ID):
        return
    kb = {"inline_keyboard": [
        [{"text": "✅ Tasdiqlash", "callback_data": f"approve_{ad_id}"},
         {"text": "❌ O'chirish",  "callback_data": f"del_{ad_id}"}],
        [{"text": "⭐️ VIP 3 kun", "callback_data": f"vip_{ad_id}"},
         {"text": "⚠️ Xato",      "callback_data": f"fix_{user_id}"}]
    ]}
    tg_api("sendMessage", json={
        "chat_id":     ADMIN_ID,
        "text":        f"🔔 <b>YANGI E'LON (ID:{ad_id})</b>\n\n{cap}",
        "parse_mode":  "HTML",
        "reply_markup": kb
    })

def admin_notify_service(srv_id, user_id, srv_data):
    if not (BOT_TOKEN and ADMIN_ID):
        return
    kb = {"inline_keyboard": [
        [{"text": "✅ Tasdiqlash", "callback_data": f"apprv_srv_{srv_id}"},
         {"text": "❌ O'chirish",  "callback_data": f"del_srv_{srv_id}"}]
    ]}
    tg_api("sendMessage", json={
        "chat_id":     ADMIN_ID,
        "text":        f"🛠 <b>YANGI SERVIS (ID:{srv_id})</b>\n\n<b>Nomi:</b> {srv_data.get('name')}\n<b>Turi:</b> {srv_data.get('type')}\n<b>Tel:</b> {srv_data.get('phone')}\n<b>Izoh:</b> {srv_data.get('desc')}",
        "parse_mode":  "HTML",
        "reply_markup": kb
    })

# ================================================================
# API ENDPOINTS
# ================================================================
@app.route("/api/ads")
def api_ads():
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM ads
        WHERE status != 'rejected'
        ORDER BY
            CASE
                WHEN (status='vip' OR (vip_until IS NOT NULL
                      AND datetime(vip_until) > datetime('now')))
                     AND user_id IS NOT NULL THEN 0
                WHEN (status='vip' OR (vip_until IS NOT NULL
                      AND datetime(vip_until) > datetime('now')))
                     AND user_id IS NULL THEN 1
                ELSE 2
            END,
            id DESC
        LIMIT 500
    """).fetchall()
    conn.close()
    return jsonify([row_to_dict(r) for r in rows])

@app.route("/api/services")
def api_services():
    conn = get_db()
    rows = conn.execute("SELECT * FROM services WHERE status = 'approved' ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([service_to_dict(r) for r in rows])

@app.route("/api/myads")
def api_myads():
    uid = request.args.get("user_id")
    if not uid:
        return jsonify([])
    conn = get_db()
    rows = conn.execute("SELECT * FROM ads WHERE user_id=? ORDER BY id DESC", (uid,)).fetchall()
    conn.close()
    return jsonify([row_to_dict(r) for r in rows])

@app.route("/api/profile")
def api_profile():
    uid = request.args.get("user_id")
    if not uid:
        return jsonify({"error": "user_id kerak"}), 400
    conn  = get_db()
    user  = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    inv_c = conn.execute("SELECT COUNT(*) as c FROM invites WHERE inviter_id=?", (uid,)).fetchone()["c"]
    conn.close()
    if not user:
        return jsonify({"error": "Topilmadi"}), 404
    u = dict(user)
    u["invite_count"] = inv_c
    u["vip_hours"]    = 48 if inv_c >= 20 else (24 if inv_c >= 10 else 0)
    return jsonify(u)

@app.route("/api/submit", methods=["POST"])
def api_submit():
    try:
        data    = request.get_json(force=True)
        ad      = data.get("ad", {})
        user_id = ad.get("user_id") or None
        images  = ad.get("images", [])

        conn  = get_db()
        inv_c = 0
        if user_id:
            inv_c = conn.execute("SELECT COUNT(*) as c FROM invites WHERE inviter_id=?", (user_id,)).fetchone()["c"]
        vip_hours = 48 if inv_c >= 20 else (24 if inv_c >= 10 else 0)
        vip_until = None
        if vip_hours:
            vip_until = (datetime.now() + timedelta(hours=vip_hours)).strftime("%Y-%m-%d %H:%M")

        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ads
                (user_id, model, year, price, region, mileage, color, fuel_type,
                 phone, description, image_url, tg_file_id, tg_msg_id,
                 status, is_auto, lat, lng, vip_until, ad_type, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            user_id,
            ad.get("model", ""),
            int(ad.get("year", 0)),
            int(ad.get("price", 0)),
            ad.get("region", ""),
            int(ad.get("mileage", 0)),
            ad.get("color", "—"),
            ad.get("fuel_type", ""),
            ad.get("phone", ""),
            ad.get("desc", "—"),
            "", "", 0,
            "vip" if vip_hours else "pending",
            0,
            ad.get("lat"),
            ad.get("lng"),
            vip_until,
            "real",
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))
        ad_id = cur.lastrowid
        conn.commit()
        conn.close()

        send_ad = {**ad, "vip": bool(vip_hours), "desc": ad.get("desc", "—"),
                   "mileage": int(ad.get("mileage", 0)), "price": int(ad.get("price", 0))}
        tg_res = send_to_channel(send_ad, images[0] if images else None)

        conn2 = get_db()
        conn2.execute("UPDATE ads SET tg_file_id=?, tg_msg_id=?, image_url=? WHERE id=?",
                      (tg_res["tg_file_id"], tg_res["tg_msg_id"],
                       f"{DOMAIN}/api/tgfile/{tg_res['tg_file_id']}" if tg_res["tg_file_id"] else "", ad_id))
        conn2.commit()
        conn2.close()

        admin_notify(ad_id, user_id or 0, channel_caption(send_ad))

        return jsonify({"status": "success", "ad_id": ad_id, "vip": bool(vip_hours), "vip_hours": vip_hours})
    except Exception as e:
        logging.exception("Submit xato:")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/services/submit", methods=["POST"])
def api_service_submit():
    try:
        data = request.get_json(force=True)
        srv  = data.get("service", {})
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO services (user_id, type, name, phone, lat, lng, description, created_at)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            srv.get("user_id"),
            srv.get("type"),
            srv.get("name"),
            srv.get("phone"),
            srv.get("lat"),
            srv.get("lng"),
            srv.get("desc"),
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))
        srv_id = cur.lastrowid
        conn.commit()
        admin_notify_service(srv_id, srv.get("user_id"), srv)
        conn.close()
        return jsonify({"status": "success", "message": "Xizmat ko'rib chiqish uchun yuborildi"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/admin/vip/<int:ad_id>", methods=["POST"])
def admin_vip(ad_id):
    d  = request.get_json(force=True) or {}
    h  = int(d.get("hours", 72))
    vu = (datetime.now() + timedelta(hours=h)).strftime("%Y-%m-%d %H:%M")
    conn = get_db()
    conn.execute("UPDATE ads SET status='vip', vip_until=? WHERE id=?", (vu, ad_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "vip_until": vu})

@app.route("/api/admin/delete/<int:ad_id>", methods=["POST"])
def admin_del(ad_id):
    conn = get_db()
    conn.execute("UPDATE ads SET status='rejected' WHERE id=?", (ad_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/register_invite", methods=["POST"])
def register_invite():
    d  = request.get_json(force=True) or {}
    er = d.get("inviter_id")
    ee = d.get("invitee_id")
    if not er or not ee or er == ee:
        return jsonify({"status": "skip"})
    conn = get_db()
    if not conn.execute("SELECT 1 FROM invites WHERE inviter_id=? AND invitee_id=?", (er, ee)).fetchone():
        conn.execute("INSERT INTO invites (inviter_id, invitee_id, created_at) VALUES (?,?,?)",
                     (er, ee, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.execute("UPDATE users SET invite_count=invite_count+1 WHERE id=?", (er,))
        conn.commit()
    cnt = conn.execute("SELECT COUNT(*) as c FROM invites WHERE inviter_id=?", (er,)).fetchone()["c"]
    conn.close()
    return jsonify({"status": "ok", "invite_count": cnt})

@app.route("/api/check_vip", methods=["POST"])
def check_vip():
    d   = request.get_json(force=True) or {}
    uid = d.get("user_id")
    if not uid:
        return jsonify({"status": "error"}), 400
    conn  = get_db()
    inv   = conn.execute("SELECT COUNT(*) as c FROM invites WHERE inviter_id=?", (uid,)).fetchone()["c"]
    hours = 48 if inv >= 20 else 24
    vu    = (datetime.now() + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M")
    last  = conn.execute("SELECT id FROM ads WHERE user_id=? AND status!='rejected' ORDER BY id DESC LIMIT 1", (uid,)).fetchone()
    ad_id = None
    if last:
        ad_id = last["id"]
        conn.execute("UPDATE ads SET status='vip', vip_until=? WHERE id=?", (vu, ad_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "ad_id": ad_id, "vip_until": vu, "hours": hours})

@app.route("/api/parser/submit", methods=["POST"])
def parser_submit():
    try:
        d = request.get_json(force=True) or {}
        tg_fid = d.get("tg_file_id", "")
        tg_mid = int(d.get("tg_msg_id", 0))
        model = d.get("model", "Noma'lum")
        region = d.get("region", "")
        price = int(d.get("price", 0) or 0)
        year = int(d.get("year", 0) or 0)
        mileage = int(d.get("mileage", 0) or 0)
        fuel_type = d.get("fuel_type", "")
        phone = d.get("phone", "")
        desc = (d.get("raw_caption", "") or "")[:500]

        conn = get_db()
        p_cnt = conn.execute("SELECT COUNT(*) as c FROM ads WHERE is_auto=1").fetchone()["c"]
        is_vip = p_cnt > 0 and p_cnt % random.randint(20, 30) == 0
        vu = (datetime.now() + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M") if is_vip else None
        stat = "vip" if is_vip else "approved"

        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ads
                (user_id, model, year, price, region, mileage, fuel_type, phone,
                 description, image_url, tg_file_id, tg_msg_id,
                 status, is_auto, vip_until, ad_type, created_at)
            VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,1,?,'parsed',?)
        """, (
            model, year, price, region, mileage, fuel_type, phone, desc,
            f"{DOMAIN}/api/tgfile/{tg_fid}" if tg_fid else "",
            tg_fid, tg_mid, stat, vu,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))
        ad_id = cur.lastrowid
        conn.commit()
        conn.close()
        return jsonify({"status": "ok", "ad_id": ad_id, "vip": is_vip})
    except Exception as e:
        logging.exception("Parser submit xato:")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/tgfile/<file_id>")
def tg_file_proxy(file_id):
    try:
        info = tg_api("getFile", params={"file_id": file_id})
        if not (info and info.get("ok")):
            return "", 404
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{info['result']['file_path']}"
        r = http_req.get(url, timeout=12, stream=True)
        return Response(r.iter_content(chunk_size=8192), content_type=r.headers.get("Content-Type", "image/jpeg"))
    except Exception as e:
        logging.error(f"tg_file_proxy: {e}")
        return "", 500

@app.route("/")
@app.route("/static/<path:filename>")
def static_files(filename="AvtoBozor2.html"):
    return send_from_directory("static", filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)