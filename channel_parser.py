# ================================================================
# channel_parser.py — Kanal Parser (app_main.py bilan integratsiya)
# ================================================================
import os, asyncio, logging, sqlite3, re, random, warnings
warnings.filterwarnings("ignore", category=UserWarning, module='pydantic')

from datetime import datetime, timezone, timedelta, time
from dotenv import load_dotenv
import requests as http_req
from telethon import TelegramClient
from aiogram import Bot
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ── ENV ─────────────────────────────────────────────────────────
BOT_TOKEN            = os.getenv("BOT_TOKEN")
API_ID               = int(os.getenv("API_ID", 0))
API_HASH             = os.getenv("API_HASH", "")
MANBA_CHANNELS       = [x.strip() for x in os.getenv("MANBA_CHANNELS", "").split(",") if x.strip()]
AVTOBOZOR_CHANNEL    = int(os.getenv("CHANNEL_ID", 0))
MINI_APP_URL         = os.getenv("MINI_APP_URL", "")
API_BASE             = os.getenv("DOMAIN", "http://localhost:8080")
DB_PATH              = os.getenv("DB_PATH", "database.db")
MODELS_POST_LINK     = os.getenv("MODELS_POST_LINK", "")
VILOYATLAR_POST_LINK = os.getenv("VILOYATLAR_POST_LINK", "")
ELON_POST_LINK       = os.getenv("ELON_POST_LINK", "")
UPLOAD_FOLDER        = os.getenv("UPLOAD_FOLDER", "static/uploads")

PROGRAM_START = datetime.now()
DB_LOCK       = asyncio.Lock()
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def is_working_time():
    if (datetime.now() - PROGRAM_START).total_seconds() < 45 * 60:
        return True
    now = datetime.now(timezone(timedelta(hours=5)))
    return time(6, 0) <= now.time() <= time(22, 0)


# ================================================================
# LUG'ATLAR — Modellar va Viloyatlar
# ================================================================
MODELS_LIST = {
    # GM — O'zbek modellari
    "Damas":        ["damas", "дамас"],
    "Labo":         ["labo", "лабо"],
    "Matiz":        ["matiz", "матиз"],
    "Spark":        ["spark", "спарк"],
    "Cobalt":       ["cobalt", "кобальт", "кобалт"],
    "Nexia":        ["nexia", "нексия", "nexia 1", "nexia 2", "nexia 3"],
    "Gentra":       ["gentra", "жентра", "lacetti", "ласетти"],
    "Onix":         ["onix", "оникс"],
    "Tracker":      ["tracker", "трекер"],
    "Orlando":      ["orlando", "орландо"],
    "Malibu":       ["malibu", "малибу"],
    "Captiva":      ["captiva", "каптива"],
    "Equinox":      ["equinox", "эквинокс"],
    "Tahoe":        ["tahoe", "тахо"],
    "Trailblazer":  ["trailblazer", "трейлблейзер"],
    "Tico":         ["tico", "тико"],
    "Monza":        ["monza", "монза"],
    # Inomarka
    "Hyundai":      ["hyundai", "elantra", "sonata", "tucson", "santa fe", "creta"],
    "Kia":          ["kia", "k5", "sportage", "carnival", "sorento"],
    "Toyota":       ["toyota", "camry", "prado", "corolla", "rav4", "fortuner"],
    "BYD":          ["byd", "song plus", "han", "atto", "seal", "qin"],
    "Chery":        ["chery", "tiggo", "arrizo"],
    "Haval":        ["haval", "jolion", "m6", "h6", "dargo"],
    "Geely":        ["geely", "monjaro", "coolray", "atlas"],
    "Mercedes-Benz":["mercedes", "mers", "benz", "mersedes"],
    "BMW":          ["bmw", "бмв"],
    "Audi":         ["audi", "ауди"],
    "Volkswagen":   ["volkswagen", "vw", "id.4", "id.6", "polo", "golf"],
    "Tesla":        ["tesla", "model 3", "model y", "model s"],
    "Lada":         ["vaz", "lada", "niva", "vesta", "priora", "granta"],
    # Yuk / Maxsus
    "Fura":         ["fura", "yuk", "грузовой", "isuzu", "man", "kamaz", "gazel",
                     "howo", "maz", "foton", "shacman", "bongo", "porter"],
}

INOMARKA = {
    "Hyundai", "Kia", "Toyota", "BYD", "Chery", "Haval", "Geely",
    "Mercedes-Benz", "BMW", "Audi", "Volkswagen", "Tesla"
}

TRUCK_KW = [
    "isuzu", "man", "howo", "kamaz", "maz", "gazel", "foton", "shacman",
    "fura", "evakuator", "bongo", "porter", "самосвал"
]

VILOYATLAR = {
    "Toshkent":          ["toshkent", "ташкент", "тошкент"],
    "Andijon":           ["andijon", "андижон"],
    "Farg'ona":          ["farg'ona", "fargona", "фаргона", "фергана"],
    "Namangan":          ["namangan", "наманган"],
    "Samarqand":         ["samarqand", "самарканд"],
    "Buxoro":            ["buxoro", "бухоро"],
    "Navoiy":            ["navoiy", "навоий"],
    "Qashqadaryo":       ["qashqadaryo", "кашкадарё", "kashkadarya"],
    "Surxondaryo":       ["surxondaryo", "сурхондарё"],
    "Jizzax":            ["jizzax", "жиззах"],
    "Sirdaryo":          ["sirdaryo", "сирдарё"],
    "Xorazm":            ["xorazm", "хоразм"],
    "Qoraqalpog'iston":  ["qoraqalpog'iston", "каракалпакстан", "nukus", "нукус"],
}

CYRILLIC = {
    'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'j','з':'z',
    'и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r',
    'с':'s','т':'t','у':'u','ф':'f','х':'x','ц':'ts','ч':'ch','ш':'sh',
    'щ':'sh','ъ':"'",'ы':'i','ь':'',"э":'e','ю':'yu','я':'ya',
    'ў':"o'",'қ':'q','ғ':"g'",'ҳ':'h',
}
CYRILLIC.update({k.upper(): v.capitalize() for k, v in CYRILLIC.items()})


# ================================================================
# DATABASE
# ================================================================
def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db_extra():
    c = db()
    c.execute("""CREATE TABLE IF NOT EXISTS last_processed (
        source_id TEXT PRIMARY KEY,
        last_msg_id INTEGER
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS parsed_messages (
        source_id TEXT,
        msg_id    INTEGER,
        created_at TEXT,
        PRIMARY KEY (source_id, msg_id)
    )""")
    c.commit()
    c.close()

def is_parsed(source, msg_id):
    c = db()
    r = c.execute(
        "SELECT 1 FROM parsed_messages WHERE source_id=? AND msg_id=?",
        (str(source), msg_id)
    ).fetchone()
    c.close()
    return bool(r)

def mark_parsed(source, msg_id):
    c = db()
    c.execute(
        "INSERT OR REPLACE INTO parsed_messages (source_id, msg_id, created_at) VALUES (?,?,?)",
        (str(source), msg_id, datetime.now(timezone.utc).isoformat())
    )
    c.commit()
    c.close()

def get_last(source):
    c = db()
    r = c.execute(
        "SELECT last_msg_id FROM last_processed WHERE source_id=?", (str(source),)
    ).fetchone()
    c.close()
    return r["last_msg_id"] if r else 0

def set_last(source, mid):
    c = db()
    c.execute(
        "INSERT OR REPLACE INTO last_processed (source_id, last_msg_id) VALUES (?,?)",
        (str(source), mid)
    )
    c.commit()
    c.close()


# ================================================================
# MATN TOZALASH
# ================================================================
def remove_links(text):
    if not text:
        return ""
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'(?<!\w)(t\.me|telegram\.me)/\S+', '', text)
    text = re.sub(r'www\.\S+', '', text)
    text = re.sub(r'(?m)^\s*@\w+\s*$', '', text)
    return re.sub(r'[*_`]+', '', text).strip()

def to_latin(text):
    return "".join(CYRILLIC.get(ch, ch) for ch in text)

def detect_model(text):
    tl = text.lower()
    for model, variants in MODELS_LIST.items():
        for v in variants:
            if re.search(r'\b' + re.escape(v) + r'\b', tl):
                return model
    return None

def detect_region(text):
    tl = text.lower()
    for region, variants in VILOYATLAR.items():
        for v in variants:
            if re.search(r'\b' + re.escape(v) + r'\b', tl):
                return region
    return None

def detect_price(text):
    m = re.search(r'(\d[\d\s,]*)\s*(?:[$доллар]|usd|доллар)', text, re.IGNORECASE)
    if m:
        try:
            return int(re.sub(r'[\s,]', '', m.group(1)))
        except Exception:
            pass
    return 0

def detect_year(text):
    m = re.search(r'\b(19[89]\d|20[012]\d)\b', text)
    return int(m.group(1)) if m else 0

def detect_phone(text):
    m = re.search(
        r'(\+?998[\s\-]?\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2})', text
    )
    if not m:
        m = re.search(
            r'(\+?[78][\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2})', text
        )
    return m.group(1).strip() if m else ""

def detect_mileage(text):
    m = re.search(
        r'(\d[\d\s,]*)\s*(?:km|км|ming km|мин км)', text, re.IGNORECASE
    )
    if m:
        try:
            v = int(re.sub(r'[\s,]', '', m.group(1)))
            return v * 1000 if v < 1000 else v
        except Exception:
            pass
    return 0

def has_model_and_region(text):
    return bool(detect_model(text)) and bool(detect_region(text))


# ================================================================
# KANALGA YUBORISH FORMATI
# ================================================================
def format_caption(text, vip=False):
    clean    = remove_links(text)
    vip_line = "⭐️ <b>VIP E'LON</b>\n\n" if vip else ""
    app_line = f"\n\n🌐 <a href='{MINI_APP_URL}'>Ilovada ko'rish</a>" if MINI_APP_URL else ""
    return f"{vip_line}{clean}{app_line}"

def channel_kb():
    btns = []
    if MODELS_POST_LINK:
        btns.append([InlineKeyboardButton(
            text="🚘 Modellar bo'yicha qidirish",
            url=MODELS_POST_LINK
        )])
    if VILOYATLAR_POST_LINK:
        btns.append([InlineKeyboardButton(
            text="📍 Viloyatlar bo'yicha qidirish",
            url=VILOYATLAR_POST_LINK
        )])
    if ELON_POST_LINK:
        btns.append([InlineKeyboardButton(
            text="➕ E'LON BERISH",
            url=ELON_POST_LINK
        )])
    if MINI_APP_URL:
        btns.append([InlineKeyboardButton(
            text="🌐 Ilovada ko'rish",
            url=MINI_APP_URL
        )])
    return InlineKeyboardMarkup(inline_keyboard=btns) if btns else None


# ================================================================
# ASOSIY YUBORISH LOGIKASI
# ================================================================
bot_instance = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)

async def post_to_channel(source, message):
    """Xabarni tozalab kanalga yuboradi, tg_file_id oladi, app_main.py ga yuboradi."""
    async with DB_LOCK:
        try:
            raw_text = message.text or message.caption or ""
            if not has_model_and_region(raw_text):
                return False

            model   = detect_model(raw_text)  or "Noma'lum"
            region  = detect_region(raw_text) or ""
            price   = detect_price(raw_text)
            year    = detect_year(raw_text)
            mileage = detect_mileage(raw_text)
            phone   = detect_phone(raw_text)

            cap = format_caption(raw_text)
            kb  = channel_kb()

            tg_file_id = ""
            tg_msg_id  = 0

            if message.photo:
                tmp = os.path.join(UPLOAD_FOLDER, f"_parser_{source}_{message.id}.jpg")
                await message.download_media(tmp)
                try:
                    sent = await bot_instance.send_photo(
                        chat_id=AVTOBOZOR_CHANNEL,
                        photo=FSInputFile(tmp),
                        caption=cap[:1024],
                        reply_markup=kb
                    )
                    tg_msg_id  = sent.message_id
                    photos     = sent.photo
                    tg_file_id = photos[-1].file_id if photos else ""
                finally:
                    try:
                        os.remove(tmp)
                    except Exception:
                        pass
            else:
                sent = await bot_instance.send_message(
                    chat_id=AVTOBOZOR_CHANNEL,
                    text=cap[:4000],
                    reply_markup=kb
                )
                tg_msg_id = sent.message_id

            # app_main.py ga yuborish
            try:
                http_req.post(
                    f"{API_BASE}/api/parser/submit",
                    json={
                        "tg_file_id":  tg_file_id,
                        "tg_msg_id":   tg_msg_id,
                        "model":       model,
                        "region":      region,
                        "price":       price,
                        "year":        year,
                        "mileage":     mileage,
                        "fuel_type":   "",
                        "phone":       phone,
                        "raw_caption": cap[:500],
                    },
                    timeout=8
                )
            except Exception as ae:
                logging.error(f"API submit xato: {ae}")

            mark_parsed(source, message.id)
            logging.info(
                f"✅ Post: {source} → msgID {message.id} | {model} | {region}"
            )
            return True

        except Exception as e:
            logging.error(f"❌ post_to_channel ({source}/{message.id}): {e}")
            return False


# ================================================================
# PARSER WORKER
# ================================================================
client = TelegramClient("avtobozor_parser_session", API_ID, API_HASH)

async def parser_worker():
    await client.start()
    logging.info("📡 Parser worker ishga tushdi.")

    # Ilk sinxronizatsiya (har manbadan oxirgi 2 ta mos xabar)
    for source in MANBA_CHANNELS:
        try:
            synced = 0
            async for msg in client.iter_messages(source, limit=30):
                if not (msg.text or msg.caption):
                    continue
                if has_model_and_region(msg.text or msg.caption or ""):
                    if await post_to_channel(source, msg):
                        synced += 1
                        await asyncio.sleep(10)
                    if synced >= 2:
                        break
            async for m in client.iter_messages(source, limit=1):
                set_last(source, m.id)
        except Exception as e:
            logging.error(f"Initial sync ({source}): {e}")

    logging.info("✅ Initial sync yakunlandi.")

    while True:
        wait = random.randint(9, 15)
        logging.info(f"⏳ Keyingi tekshiruv {wait} daqiqadan so'ng...")
        await asyncio.sleep(wait * 60)

        if not is_working_time():
            logging.info("🌙 Tungi vaqt (22:00–06:00). Parser to'xtatildi.")
            continue

        for source in MANBA_CHANNELS:
            try:
                last_id = get_last(source)
                found   = []
                async for msg in client.iter_messages(source, min_id=last_id, limit=50):
                    if not (msg.text or msg.caption):
                        continue
                    if is_parsed(source, msg.id):
                        continue
                    if has_model_and_region(msg.text or msg.caption or ""):
                        found.append(msg)
                    if len(found) >= 2:
                        break
                for msg in found:
                    if await post_to_channel(source, msg):
                        await asyncio.sleep(10)
                async for m in client.iter_messages(source, limit=1):
                    set_last(source, m.id)
            except Exception as e:
                logging.error(f"Worker loop ({source}): {e}")


# ================================================================
# MAIN
# ================================================================
async def main():
    init_db_extra()
    asyncio.create_task(parser_worker())
    logging.info(
        "🔄 Parser ishga tushdi. "
        "bot.py va app_main.py alohida jarayonlarda yuritilishi kerak."
    )
    # Doimiy ishlash
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Parser to'xtatildi.")
