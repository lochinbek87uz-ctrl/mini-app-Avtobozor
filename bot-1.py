# ================================================================
# bot.py — AvtoBozor Telegram Bot (To'liq versiya)
# ================================================================
import os, logging, json, sqlite3, asyncio
import requests as http_req
from datetime import datetime, timedelta
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    WebAppInfo, ReplyKeyboardMarkup, KeyboardButton,
    CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ── ENV ─────────────────────────────────────────────────────────
BOT_TOKEN      = os.getenv("BOT_TOKEN")
MINI_APP_URL   = os.getenv("MINI_APP_URL", "")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "@AvtoBozori_Admini")
ADMIN_ID       = os.getenv("ADMIN_ID")
CHANNEL_ID     = os.getenv("CHANNEL_ID")
GROUP_LINK     = os.getenv("GROUP_LINK", "")
API_BASE       = os.getenv("DOMAIN", "http://localhost:8080")
DB_PATH        = os.getenv("DB_PATH", "database.db")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi! .env faylini tekshiring.")
if not MINI_APP_URL:
    raise ValueError("MINI_APP_URL topilmadi! .env faylini tekshiring.")

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()


# ================================================================
# DATABASE (bot ham to'g'ridan-to'g'ri o'qiydi)
# ================================================================
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def ensure_tables():
    c = get_db()
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
    c.execute('''CREATE TABLE IF NOT EXISTS ads (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id   INTEGER,
        model     TEXT,
        year      INTEGER,
        price     INTEGER,
        region    TEXT,
        status    TEXT DEFAULT "pending",
        vip_until TIMESTAMP,
        is_auto   INTEGER DEFAULT 0,
        ad_type   TEXT DEFAULT "real",
        created_at TIMESTAMP
    )''')
    c.commit()
    c.close()

ensure_tables()

def api_post(path, data):
    try:
        r = http_req.post(f"{API_BASE}{path}", json=data, timeout=10)
        return r.json()
    except Exception as e:
        logging.error(f"API POST {path}: {e}")
        return {}

def get_invite_count(user_id):
    c   = get_db()
    row = c.execute(
        "SELECT COUNT(*) as cnt FROM invites WHERE inviter_id=?", (user_id,)
    ).fetchone()
    c.close()
    return row["cnt"] if row else 0


# ================================================================
# KLAVIATURALAR
# ================================================================
def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(
                text="🚗 AvtoBozorni ochish",
                web_app=WebAppInfo(url=MINI_APP_URL)
            )],
            [
                KeyboardButton(text="📋 Mening e'lonlarim"),
                KeyboardButton(text="⭐️ VIP olish")
            ],
            [
                KeyboardButton(text="🔗 Do'stlarni taklif qilish"),
                KeyboardButton(text="👨‍💻 Admin")
            ],
        ],
        resize_keyboard=True
    )

def contact_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(
                text="📱 Telefon raqamni ulashish",
                request_contact=True
            )
        ]],
        resize_keyboard=True
    )

def vip_check_kb(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✅ Tekshirish",
            callback_data=f"checkvip_{user_id}"
        )
    ]])


# ================================================================
# HANDLERS — /start
# ================================================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject):
    user = message.from_user

    # ref parametr (taklif havola orqali kelgan)
    inviter_id = None
    if command.args and command.args.startswith("ref_"):
        try:
            inviter_id = int(command.args.split("_")[1])
        except Exception:
            pass

    # Foydalanuvchini bazaga saqlash
    c = get_db()
    existing = c.execute("SELECT phone FROM users WHERE id=?", (user.id,)).fetchone()
    c.execute(
        "INSERT OR REPLACE INTO users (id, first_name, username, phone, created_at) VALUES (?,?,?,?,?)",
        (
            user.id,
            user.first_name,
            user.username,
            existing["phone"] if existing else None,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        )
    )
    c.commit()
    c.close()

    # Taklif ro'yxatga olish
    if inviter_id and inviter_id != user.id:
        res     = api_post("/api/register_invite", {
            "inviter_id": inviter_id,
            "invitee_id": user.id
        })
        inv_cnt = res.get("invite_count", 0)
        try:
            if inv_cnt >= 10:
                hours_txt = "48 soatlik" if inv_cnt >= 20 else "24 soatlik"
                status_line = (
                    f"✅ <b>VIP huquqi olindi!</b> "
                    f"Keyingi e'loningiz <b>{hours_txt} VIP</b> turadi."
                )
            else:
                status_line = (
                    f"🎯 VIP uchun yana <b>{10 - inv_cnt}</b> ta taklif kerak "
                    f"(10 ta = 24 soat VIP)"
                )
            await bot.send_message(
                inviter_id,
                f"🎉 Yangi foydalanuvchi sizning havolangiz orqali qo'shildi!\n"
                f"Jami takliflar: <b>{inv_cnt}</b>\n\n{status_line}"
            )
        except Exception:
            pass

    # Telefon raqam borligini tekshirish
    c2 = get_db()
    u2 = c2.execute("SELECT phone FROM users WHERE id=?", (user.id,)).fetchone()
    c2.close()

    if not u2 or not u2["phone"]:
        await message.answer(
            f"<b>Assalomu alaykum, {user.full_name}!</b>\n\n"
            "Avvalo telefon raqamingizni ulashing 👇",
            reply_markup=contact_kb()
        )
    else:
        await message.answer(
            f"<b>Assalomu alaykum, {user.full_name}!</b>\n\n"
            "O'zbekistondagi eng yirik avtomobillar savdosi Mini App'iga xush kelibsiz 🚗\n\n"
            "Pastdagi tugmani bosib AvtoBozorni oching 👇",
            reply_markup=main_kb()
        )


# ================================================================
# CONTACT — telefon raqam olish
# ================================================================
@dp.message(F.contact)
async def handle_contact(message: types.Message):
    c = get_db()
    c.execute(
        "UPDATE users SET phone=? WHERE id=?",
        (message.contact.phone_number, message.from_user.id)
    )
    c.commit()
    c.close()
    await message.answer(
        "✅ Telefon raqamingiz saqlandi!\nEndi AvtoBozordan foydalanishingiz mumkin 👇",
        reply_markup=main_kb()
    )


# ================================================================
# HANDLERS — MENYU TUGMALARI
# ================================================================
@dp.message(F.text == "📋 Mening e'lonlarim")
async def my_ads(message: types.Message):
    c   = get_db()
    ads = c.execute(
        "SELECT * FROM ads WHERE user_id=? ORDER BY id DESC",
        (message.from_user.id,)
    ).fetchall()
    c.close()

    if not ads:
        await message.answer(
            "📋 Sizda hali e'lon yo'q.\nYangi e'lon berish uchun Mini Appni oching 👇",
            reply_markup=main_kb()
        )
        return

    STATUS = {"pending": "⏳", "approved": "✅", "vip": "⭐️", "rejected": "❌"}
    txt = f"<b>Sizning e'lonlaringiz ({len(ads)} ta):</b>\n\n"
    for ad in ads[:10]:
        s   = STATUS.get(ad["status"], "⏳")
        vip = " ⭐️" if ad["status"] == "vip" else ""
        txt += f"{s} <b>{ad['model']}</b> {ad['year']} — {ad['price']:,}${vip}\n"
    if len(ads) > 10:
        txt += f"\n...va yana {len(ads)-10} ta e'lon"
    await message.answer(txt, reply_markup=main_kb())


@dp.message(F.text == "⭐️ VIP olish")
async def vip_info(message: types.Message):
    uid = message.from_user.id
    inv = get_invite_count(uid)
    bi  = await bot.get_me()
    ref = f"https://t.me/{bi.username}?start=ref_{uid}"

    if inv >= 20:
        txt = (
            "⭐️ <b>VIP huquqingiz maksimal darajada!</b>\n\n"
            "E'lon berganda avtomatik <b>48 soatlik VIP</b> beriladi.\n"
            f"Jami takliflar: <b>{inv}/20</b>"
        )
    elif inv >= 10:
        txt = (
            "⭐️ <b>VIP huquqingiz bor!</b>\n\n"
            "E'lon berganda avtomatik <b>24 soatlik VIP</b> beriladi.\n"
            f"Jami takliflar: <b>{inv}/20</b>\n"
            "20 taga yetganda <b>48 soatlik VIP</b> olasiz!"
        )
    else:
        needed_10  = 10 - inv
        needed_20  = 20 - inv
        group_line = f"\n\n📢 Guruhga qo'shish uchun:\n{GROUP_LINK}" if GROUP_LINK else ""
        txt = (
            "⭐️ <b>VIP qanday olinadi?</b>\n\n"
            "👥 Do'stlarni guruhga taklif qiling:\n"
            "• <b>10 ta</b> taklif → 24 soat VIP\n"
            "• <b>20 ta</b> taklif → 48 soat VIP\n\n"
            f"📊 Sizning holat: <b>{inv}</b> ta taklif\n"
            f"🎯 24 soat VIP uchun yana <b>{needed_10}</b> ta kerak\n"
            f"🏆 48 soat VIP uchun yana <b>{needed_20}</b> ta kerak"
            f"{group_line}\n\n"
            f"🔗 Sizning taklif havolangiz:\n<code>{ref}</code>"
        )
    await message.answer(txt, reply_markup=main_kb())


@dp.message(F.text == "🔗 Do'stlarni taklif qilish")
async def invite_friends(message: types.Message):
    uid        = message.from_user.id
    inv        = get_invite_count(uid)
    bi         = await bot.get_me()
    ref        = f"https://t.me/{bi.username}?start=ref_{uid}"
    group_line = f"\n\n📢 Guruh havolasi: {GROUP_LINK}" if GROUP_LINK else ""

    hours      = 48 if inv >= 20 else (24 if inv >= 10 else 0)
    vip_status = (
        f"✅ <b>{hours} soatlik VIP</b> aktivlashtirilgan!"
        if hours else
        f"🎯 <b>{10 - inv}</b> ta taklif qoldi (10 ta = 24 soat VIP)"
    )

    await message.answer(
        f"🔗 <b>Sizning taklif havolangiz:</b>\n\n"
        f"<code>{ref}</code>\n\n"
        f"📊 Jami takliflar: <b>{inv}/20</b>\n"
        f"{vip_status}"
        f"{group_line}\n\n"
        "💡 Do'stlaringiz bu havola orqali kirganida hisoblanadi.\n"
        "E'lon bergandan keyin <b>\"✅ Tekshirish\"</b> tugmasini bosing!",
        reply_markup=main_kb()
    )


@dp.message(F.text == "👨‍💻 Admin")
async def contact_admin(message: types.Message):
    await message.answer(
        f"📞 Savol va takliflar uchun: {ADMIN_USERNAME}",
        reply_markup=main_kb()
    )


# ================================================================
# VIP TEKSHIRISH
# ================================================================
@dp.message(F.text.startswith("✅ Tekshirish") | F.text.startswith("Tekshirish"))
async def check_vip_message(message: types.Message):
    await process_check_vip(message.from_user.id, message)

@dp.callback_query(F.data.startswith("checkvip_"))
async def cb_check_vip(cb: CallbackQuery):
    uid = int(cb.data.split("_")[1])
    await cb.answer()
    await process_check_vip(uid, cb.message, edit=True)

async def process_check_vip(user_id: int, message_obj, edit=False):
    res   = api_post("/api/check_vip", {"user_id": user_id})
    hours = res.get("hours", 24)
    ad_id = res.get("ad_id")

    if ad_id:
        text = (
            "🎉 <b>Tabriklaymiz!</b>\n\n"
            f"E'loningiz tekshirildi va <b>{hours} soatlik VIP</b> statusiga o'tkazildi!\n\n"
            "⭐️ E'loningiz boshqa e'lonlar ustida ko'rinadi.\n"
            f"E'lon ID: <b>#{ad_id}</b>"
        )
    else:
        text = (
            "ℹ️ Sizda aktiv e'lon topilmadi.\n"
            "Avval Mini App orqali e'lon bering, keyin tekshiring."
        )

    try:
        if edit:
            await message_obj.edit_text(text)
        else:
            await message_obj.answer(text, reply_markup=main_kb())
    except Exception:
        await bot.send_message(user_id, text, reply_markup=main_kb())


# ================================================================
# ADMIN CALLBACKLAR
# ================================================================
@dp.callback_query(F.data.startswith("approve_"))
async def cb_approve(cb: CallbackQuery):
    ad_id = int(cb.data.split("_")[1])
    c = get_db()
    ad = c.execute("SELECT user_id, model FROM ads WHERE id=?", (ad_id,)).fetchone()
    c.execute("UPDATE ads SET status='approved' WHERE id=?", (ad_id,))
    c.commit()
    c.close()
    await cb.message.edit_text(cb.message.text + "\n\n✅ Tasdiqlandi.")
    await cb.answer("Tasdiqlandi ✅")
    if ad and ad["user_id"]:
        try:
            await bot.send_message(
                ad["user_id"],
                f"✅ <b>{ad['model']}</b> e'loningiz tasdiqlandi!"
            )
        except Exception:
            pass


@dp.callback_query(F.data.startswith("del_"))
async def cb_delete(cb: CallbackQuery):
    ad_id = int(cb.data.split("_")[1])
    c = get_db()
    ad = c.execute("SELECT user_id, model FROM ads WHERE id=?", (ad_id,)).fetchone()
    c.execute("UPDATE ads SET status='rejected' WHERE id=?", (ad_id,))
    c.commit()
    c.close()
    await cb.message.edit_text(cb.message.text + "\n\n🗑 O'chirildi.")
    await cb.answer("O'chirildi 🗑")
    if ad and ad["user_id"]:
        try:
            await bot.send_message(
                ad["user_id"],
                f"ℹ️ <b>{ad['model']}</b> e'loningiz admin tomonidan o'chirildi."
            )
        except Exception:
            pass


@dp.callback_query(F.data.startswith("vip_"))
async def cb_vip(cb: CallbackQuery):
    ad_id = int(cb.data.split("_")[1])
    res   = api_post(f"/api/admin/vip/{ad_id}", {"hours": 72})
    vu    = res.get("vip_until", "")
    c     = get_db()
    ad    = c.execute("SELECT user_id, model FROM ads WHERE id=?", (ad_id,)).fetchone()
    c.close()
    await cb.message.edit_text(cb.message.text + f"\n\n⭐️ VIP qilindi ({vu} gacha).")
    await cb.answer("VIP berildi ⭐️")
    if ad and ad["user_id"]:
        try:
            await bot.send_message(
                ad["user_id"],
                f"⭐️ <b>{ad['model']}</b> e'loningiz 3 kunlik VIP ga ko'tarildi!"
            )
        except Exception:
            pass


@dp.callback_query(F.data.startswith("fix_"))
async def cb_fix(cb: CallbackQuery):
    uid = int(cb.data.split("_")[1])
    try:
        await bot.send_message(
            uid,
            "⚠️ E'loningizda xatolik aniqlandi. "
            "Iltimos qaytadan yuboring yoki adminga murojaat qiling."
        )
        await cb.answer("Xabar yuborildi ✅")
    except Exception:
        await cb.answer(
            "Xabar yuborib bo'lmadi (bloklangan bo'lishi mumkin)",
            show_alert=True
        )


# ================================================================
# WEB APP DATA — Mini App dan kelgan ma'lumotlar
# ================================================================
@dp.message(F.web_app_data)
async def webapp_data(message: types.Message):
    try:
        d = json.loads(message.web_app_data.data)
        if d.get("action") == "contact":
            uid = message.from_user.id
            inv = get_invite_count(uid)

            # VIP taklifi
            if inv < 10 and GROUP_LINK:
                kb = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="👥 Guruhga qo'shish",
                        url=GROUP_LINK
                    ),
                    InlineKeyboardButton(
                        text="✅ Tekshirish",
                        callback_data=f"checkvip_{uid}"
                    )
                ]])
                await message.answer(
                    f"📞 Aloqa: <b>{d.get('phone', '—')}</b>\n\n"
                    "💡 <b>E'loningizni VIP qiling!</b>\n"
                    "Guruhga do'stlaringizni qo'shing:\n"
                    "• 10 ta → 24 soat VIP\n"
                    "• 20 ta → 48 soat VIP\n\n"
                    "Do'stlarni qo'shgandan so'ng <b>Tekshirish ✅</b> ni bosing:",
                    reply_markup=kb
                )
            else:
                await message.answer(
                    f"📞 E'lon egasining raqami: <b>{d.get('phone', '—')}</b>",
                    reply_markup=main_kb()
                )
    except Exception as e:
        logging.error(f"WebApp data xato: {e}")


# ================================================================
# MAIN
# ================================================================
async def main():
    print("🤖 AvtoBozor boti ishga tushdi!")
    print(f"🔗 Mini App: {MINI_APP_URL}")
    print(f"🌐 API: {API_BASE}")
    print(f"👥 Guruh: {GROUP_LINK}")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
