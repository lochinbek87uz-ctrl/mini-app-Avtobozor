import os
import asyncio
import logging
import json
import re
import warnings

# Pydantic ogohlantirishlarini o'chirish
warnings.filterwarnings("ignore", category=UserWarning, module='pydantic')

from aiogram import Bot, Dispatcher, F, types
from aiogram.types import InputMediaPhoto
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from dotenv import load_dotenv


from aiogram.client.default import DefaultBotProperties


# --- KONFIGURATSIYA ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

AIN_BOT_TOKEN = os.getenv("AIN_BOT_TOKEN")
AVTOBOZOR_CHANNEL = int(os.getenv("AVTOBOZOR_CHANNEL", 0))
STORAGE_FILE = "sent_messages.json"
RELATIONS_FILE = "relations.json"


# VILOYATLAR (Lotin va Kril - Barcha variantlar)
REGION_MAP = {
    # Toshkent
    "TOSHKENT": -1003228589769, "ТОШКЕНТ": -1003228589769,

    # Sirdaryo
    "SIRDARYO": -1003509557565, "СИРДАРЁ": -1003509557565,

    # Jizzax
    "JIZZAX": -1003520187909, "ЖИЗЗАХ": -1003520187909,

    # Samarqand
    "SAMARQAND": -1003336552139, "САМАРКАНД": -1003336552139, "САМАРҚАНД": -1003336552139,

    # Farg'ona
    "FARGONA": -1003263126693, "ФАРГОНА": -1003263126693, "FARG'ONA": -1003263126693, "ФАРҒОНА": -1003263126693,

    # Namangan
    "NAMANGAN": -1003510562859, "НАМАНГАН": -1003510562859,

    # Andijon
    "ANDIJON": -1003662789230, "АНДИЖОН": -1003662789230,

    # Qashqadaryo
    "QASHQADARYO": -1003556656003, "КАШКАДАРЁ": -1003556656003, "ҚАШҚАДАРЁ": -1003556656003,

    # Surxondaryo
    "SURXONDARYO": -1003509726784, "СУРХОНДАРЁ": -1003509726784, "СУРХАНДАРЁ": -1003509726784, "SURXANDARYO": -1003509726784,

    # Buxoro
    "BUXORO": -1003653032311, "БУХОРО": -1003653032311,

    # Navoiy
    "NAVOIY": -1003383284056, "НАВОИЙ": -1003383284056,

    # Xorazm
    "XORAZM": -1003657187614, "ХОРАЗМ": -1003657187614,

    # Qoraqalpog'iston
    "QORAQALPOGISTON": -1003670499634, "QORAQALPOG‘ISTON": -1003670499634, # Qiyshiq tutuq belgisi
    "QORAQALPOG'ISTON": -1003670499634, # To'g'ri tutuq belgisi
    "QORAQALPOQ": -1003670499634, "КОРАКОЛПОГИСТОН": -1003670499634,
    "ҚОРАҚАЛПОҒИСТОН": -1003670499634,
    }

# MODELLAR (Lotin va Kril - Birlashtirilgan)
MODEL_MAP = {
    # Damas va Labo
    "DAMAS": -1003259727663, "ДАМАС": -1003259727663,
    "LABO": -1003259727663, "ЛАБО": -1003259727663,
    "DAMAS-LABO": -1003259727663, "ДАМАС-ЛАБО": -1003259727663,

    # Matiz
    "MATIZ": -1003522323696, "МАТИЗ": -1003522323696,

    # Spark
    "SPARK": -1003595581577, "СПАРК": -1003595581577,

    # Cobalt
    "COBALT": -1003433070787, "КОБАЛЬТ": -1003433070787, "КОБАЛТ": -1003433070787,

    # Nexia
    "NEXIA": -1003698176457, "НЕКСИЯ": -1003698176457,

    # Onix
    "ONIX": -1003486271636, "ОНИКС": -1003486271636,

    # Gentra va Lacetti (Bitta kanal)
    "GENTRA": -1003577671426, "ЖЕНТРА": -1003577671426,
    "LACETTI": -1003577671426, "ЛАСЕТТИ": -1003577671426,

    # Captiva
    "CAPTIVA": -1003492563801, "КАПТИВА": -1003492563801,

    # Malibu
    "MALIBU": -1003418107363, "МАЛИБУ": -1003418107363,

    "MONZA": -1003676902508, "МОНЗА": -1003676902508,

    # Tracker
    "TRACKER": -1003406693374, "ТРЕКЕР": -1003406693374,

    # Orlando
    "ORLANDO": -1003614294919, "ОРЛАНДО": -1003614294919,

    # Equinox
    "EQUINOX": -1003567477290, "ЭКВИНОКС": -1003567477290,

    # Trailblazer
    "TRAILBLAZER": -1003695994485, "ТРЕЙЛБЛЕЙЗЕР": -1003695994485,

    # Tahoe
    "TAHOE": -1003555474252, "ТАХОЕ": -1003555474252,

    # Tico
    "TICO": -1003647542448, "ТИКО": -1003647542448,

    # Fura
    "FURA": -1003538024901, "ФУРА": -1003538024901,


    # Elektromobil
    "ELEKTROMOBIL": -1003467177176, "ЭЛЕКТРОМОБИЛ": -1003467177176,

    # --- INOMARKALAR (Barcha xorijiy brendlar uchun bitta ID: -1003597414206) ---
    "INOMARKA": -1003597414206, "ИНОМАРКА": -1003597414206,

    # Yevropa va Amerika
    "VOLKSWAGEN": -1003597414206, "ФОЛЬКСВАГЕН": -1003597414206, "VW": -1003597414206,
    "RENAULT": -1003597414206, "РЕНО": -1003597414206, "ARKANA": -1003597414206, "АРКАНА": -1003597414206, "АРКАНО": -1003597414206,
    "TESLA": -1003597414206, "ТЕСЛА": -1003597414206,
    "MERCEDES": -1003597414206, "МЕРСЕДЕС": -1003597414206, "MERS": -1003597414206, "МЕРС": -1003597414206,
    "BMW": -1003597414206, "БМВ": -1003597414206,
    "AUDI": -1003597414206, "АУДИ": -1003597414206,
    "PORSCHE": -1003597414206, "ПОРШЕ": -1003597414206,
    "LAND ROVER": -1003597414206, "ЛЕНД РОВЕР": -1003597414206, "RANGE ROVER": -1003597414206, "РЕНДЖ РОВЕР": -1003597414206,
    "FORD": -1003597414206, "ФОРД": -1003597414206,
    "SKODA": -1003597414206, "ШКОДА": -1003597414206,
    "BMW": -1003597414206, "БМВ": -1003597414206,

    # Koreya va Yaponiya
    "KIA": -1003597414206, "КИА": -1003597414206,
    "HYUNDAI": -1003597414206, "ХУНДАЙ": -1003597414206, "ХЮНДАЙ": -1003597414206,
    "TOYOTA": -1003597414206, "ТОЙОТА": -1003597414206,

    # Xitoy
    "BYD": -1003597414206, "БИД": -1003597414206,
    "CHERY": -1003597414206, "ЧЕРИ": -1003597414206,
    "ICAR": -1003597414206, "АЙКАР": -1003597414206,
    "JETOUR": -1003597414206, "ЖЕТУР": -1003597414206,
    "HAVAL": -1003597414206, "ХАВАЛ": -1003597414206,
    "GEELY": -1003597414206, "ДЖИЛИ": -1003597414206,
    "ZEEKR": -1003597414206, "ЗИКР": -1003597414206,
    "CHANGAN": -1003597414206, "ЧАНГАН": -1003597414206,
    "LIXIANG": -1003597414206, "LI": -1003597414206, "ЛИСЯН": -1003597414206, "ЛИ": -1003597414206,
    "LEAPMOTOR": -1003597414206, "ЛЕАПМОТОР": -1003597414206,
    "GAC": -1003597414206, "ГАК": -1003597414206,
    "JAC": -1003597414206, "ЖАК": -1003597414206,
    "VOYAH": -1003597414206, "ВОЯ": -1003597414206,
    "EXEED": -1003597414206, "ЭКСИД": -1003597414206,
    "HONGQI": -1003597414206, "ХОНГЧИ": -1003597414206,
    "AVATR": -1003597414206, "АВАТР": -1003597414206,
    "DENZA": -1003597414206, "ДЕНЗА": -1003597414206,

 # --- YUK AVTOMOBILLARI (Barcha turdagi yuk mashinalari uchun ID: -1003538024901) ---
    "KIA_BONGO": -1003538024901, "КИА_БОНГО": -1003538024901,
    "HYUNDAI_PORTER": -1003538024901, "ХУНДАЙ_ПОРТЕР": -1003538024901,
    "PORTER": -1003538024901, "ПОРТЕР": -1003538024901,
    "BONGO": -1003538024901, "БОНГО": -1003538024901,
    "KAMAZ": -1003538024901, "КАМАЗ": -1003538024901,
    "ZIL": -1003538024901, "ЗИЛ": -1003538024901,
    "GAZ": -1003538024901, "ГАЗ": -1003538024901,
    "53": -1003538024901, "52": -1003538024901,
    "HOWO": -1003538024901, "ХОВО": -1003538024901,
    "SHACMAN": -1003538024901, "ШАКМАН": -1003538024901,
    "SHANXAY": -1003538024901, "ШАНХАЙ": -1003538024901,
    "FAW": -1003538024901, "ФАВ": -1003538024901,
    "MAN": -1003538024901, "МАН": -1003538024901,
    "DAF": -1003538024901, "ДАФ": -1003538024901,
    "SCANIA": -1003538024901, "СКАНИЯ": -1003538024901,
    "VOLVO": -1003538024901, "ВОЛЬВО": -1003538024901,
    "IVECO": -1003538024901, "ИВЕКО": -1003538024901,
    "SITRAK": -1003538024901, "СИТРАК": -1003538024901,
    "ISUZU": -1003538024901, "ИСУЗУ": -1003538024901,
    "GAZEL": -1003538024901, "ГАЗЕЛЬ": -1003538024901,
    "MAZ": -1003538024901, "МАЗ": -1003538024901,
    "FOTON": -1003538024901, "ФОТОН": -1003538024901,
    "YUK": -1003538024901, "ЮК": -1003538024901,
    "FURA": -1003538024901, "ФУРА": -1003538024901,
    "LUI": -1003538024901, "ЛУИ": -1003538024901,


}

VODIY_LIST = ["ANDIJON", "NAMANGAN", "FARGONA", "FARG'ONA", "АНДИЖОН", "НАМАНГАН", "ФАРҒОНА", "ФАРГОНА"]
VODIY_CHANNEL_ID = -1003636956752
UNIVERSAL_CHANNEL_ID = -1003484451449  # Avto bozor chat IDS

DB_PATH = "ads.db" # Ma'lumotlar bazasi nomi

def load_data():
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, 'r') as f:
                d = json.load(f)
                return {int(k): {int(ck): int(cv) for ck, cv in v.items()} for k, v in d.items()}
        except: return {}
    return {}

def save_data(data):
    with open(STORAGE_FILE, 'w') as f:
        json.dump({str(k): {str(ck): cv for ck, cv in v.items()} for k, v in data.items()}, f, indent=4)

def load_relations():
    if os.path.exists(RELATIONS_FILE):
        try:
            with open(RELATIONS_FILE, 'r') as f:
                d = json.load(f)
                return {int(k): [int(i) for i in v] for k, v in d.items()}
        except: return {}
    return {}

def save_relations(data):
    with open(RELATIONS_FILE, 'w') as f:
        json.dump({str(k): v for k, v in data.items()}, f, indent=4)

children_map = load_relations()
sent_messages = load_data()
post_queue = asyncio.Queue()
SEND_LOCK = asyncio.Lock()
bot = Bot(
    token=AIN_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()

def get_targets(text):
    # Har doim universal kanalni ro'yxatga qo'shamiz
    res = {UNIVERSAL_CHANNEL_ID}

    if not text:
        return list(res)

    upper_text = text.upper()
    is_vodiy = False

    # Modellarni tekshirish
    for k, v in MODEL_MAP.items():
        if re.search(rf"#{re.escape(k.upper())}\b", upper_text):
            res.add(v)

    # Viloyatlarni tekshirish
    for k, v in REGION_MAP.items():
        if f"#{k.upper()}" in upper_text:
            res.add(v)
            if k.upper() in VODIY_LIST:
                is_vodiy = True

    if is_vodiy:
        res.add(VODIY_CHANNEL_ID)

    # Agar Yuk mashinasi (KIA BONGO, PORTER) bo'lsa, Inomarka kanalidan olib tashlash
    if -1003538024901 in res and -1003597414206 in res:
        res.remove(-1003597414206)

    return list(res)

def get_post_report_links(text_or_data):
    """E'lon yuborilgan kanallar haqida HTML hisobotini yaratadi."""
    report = []
    if isinstance(text_or_data, dict):
        text_up = (text_or_data.get('raw_caption') or "").upper()
    else:
        text_up = str(text_or_data).upper()

    # Viloyatlarni tekshirish (REGION_MAP dan)
    is_vodiy = False
    processed_cids = set()
    for reg, cid in REGION_MAP.items():
        if f"#{reg.upper()}" in text_up and cid not in processed_cids:
            link = f"https://t.me/c/{str(cid).replace('-100', '')}/1"
            report.append(f"• <a href='{link}'>{reg.capitalize()} viloyati</a>")
            processed_cids.add(cid)
            # Agar viloyat Vodiyga tegishli bo'lsa belgilaymiz
            if reg.upper() in VODIY_LIST:
                is_vodiy = True

    # Vodiy kanali (Agar viloyat vodiyga tegishli bo'lsa)
    if is_vodiy:
        link = f"https://t.me/c/{str(VODIY_CHANNEL_ID).replace('-100', '')}/1"
        report.append(f"• <a href='{link}'>Vodiy kanali</a>")

    # Universal chat
    link = f"https://t.me/c/{str(UNIVERSAL_CHANNEL_ID).replace('-100', '')}/1"
    report.append(f"• <a href='{link}'>Avto Bozor Chat</a>")

    return "\n".join(list(dict.fromkeys(report)))

async def safe_send(request_func, delay=1.5):
    async with SEND_LOCK:
        try:
            res = await request_func()
            await asyncio.sleep(delay)
            return res
        except TelegramRetryAfter as e:
            logging.warning(f"FloodWait: {e.retry_after}s. Retrying...")
            await asyncio.sleep(e.retry_after)
            return await safe_send(request_func, delay)
        except Exception as e:
            logging.error(f"Safe send error: {e}")
            return None

async def post_worker():
    while True:
        msg = await post_queue.get()
        try:
            text = msg.text or msg.caption or ""
            reply_msg = msg.reply_to_message
            parent_id = None
            if reply_msg and reply_msg.message_id in sent_messages:
                parent_id = reply_msg.message_id
                targets = list(sent_messages[parent_id].keys())
            else:
                targets = get_targets(text)

            sent_messages[msg.message_id] = {}

            for ch_id in targets:
                reply_to_id = None
                if parent_id and parent_id in sent_messages and ch_id in sent_messages[parent_id]:
                    reply_to_id = sent_messages[parent_id][ch_id]

                try:
                    if msg.photo:
                        m = await safe_send(lambda: bot.send_photo(
                            chat_id=ch_id,
                            photo=msg.photo[-1].file_id,
                            caption=msg.caption,
                            reply_markup=msg.reply_markup,
                            reply_to_message_id=reply_to_id
                        ), delay=1.5)
                    else:
                        m = await safe_send(lambda: bot.send_message(
                            chat_id=ch_id,
                            text=msg.text,
                            reply_markup=msg.reply_markup,
                            reply_to_message_id=reply_to_id
                        ), delay=1.0)
                    if m:
                        sent_messages[msg.message_id][ch_id] = m.message_id
                except Exception as e:
                    logging.error(f"Xabar yuborishda xato ({ch_id}): {e}")

            save_data(sent_messages)
        except Exception as e:
            logging.error(f"Worker error: {e}")
        finally:
            post_queue.task_done()
            await asyncio.sleep(0.5)

# YANGI POST
@dp.channel_post(F.chat.id == AVTOBOZOR_CHANNEL)
async def on_post(msg: types.Message):
    await post_queue.put(msg)

# TAHRIRLASH
# --- TAHRIRLASH (EDIT) QISMI ---
@dp.edited_channel_post(F.chat.id == AVTOBOZOR_CHANNEL)
async def on_edit(msg: types.Message):
    sid = msg.message_id
    if sid not in sent_messages:
        return

    new_text = msg.text or msg.caption or ""

    # 1. Mavjud xabarlarni tahrirlash (Eski kanallarda)
    for ch_id, mid in sent_messages[sid].items():
        try:
            if msg.photo:
                await bot.edit_message_caption(
                    chat_id=ch_id,
                    message_id=mid,
                    caption=new_text,
                    reply_markup=msg.reply_markup # Tugmalarni yangilash
                )
            else:
                await bot.edit_message_text(
                    chat_id=ch_id,
                    message_id=mid,
                    text=new_text,
                    reply_markup=msg.reply_markup # Tugmalarni yangilash
                )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e).lower():
                continue
            logging.error(f"Tahrirlashda xato ({ch_id}): {e}")
        except Exception as e:
            logging.error(f"Tahrirlashda xato ({ch_id}): {e}")

    # 2. Yangi kanallarni aniqlash va yuborish (Agar yangi hashtag qo'shilgan bo'lsa)
    new_targets = get_targets(new_text)
    existing_targets = set(sent_messages[sid].keys())

    # Faqat yangi qo'shilgan kanallarni topamiz
    targets_to_add = set(new_targets) - existing_targets

    if targets_to_add:
        for ch_id in targets_to_add:
            try:
                if msg.photo:
                    m = await bot.send_photo(
                        chat_id=ch_id,
                        photo=msg.photo[-1].file_id,
                        caption=new_text,
                        reply_markup=msg.reply_markup
                    )
                else:
                    m = await bot.send_message(
                        chat_id=ch_id,
                        text=new_text,
                        reply_markup=msg.reply_markup
                    )
                sent_messages[sid][ch_id] = m.message_id
            except Exception as e:
                logging.error(f"Yangi kanalga yuborishda xato ({ch_id}): {e}")

        save_data(sent_messages)

# --- O'CHIRISH (DELETE) QISMI ---
# Diqqat: Bu ishlashi uchun bot kanalda "Postlarni o'chirish" huquqiga ega admin bo'lishi kerak
@dp.channel_post()
@dp.message(F.content_type == types.ContentType.DELETE_CHAT_PHOTO) # Bu qism platforma cheklovlariga bog'liq
async def on_delete(msg: types.Message):
    # Eslatma: Telegram botlar odatda xabar o'chirilganini bevosita "event" sifatida olmasligi mumkin.
    # Lekin tahrirlash orqali o'chirish mantiqini yuqorida shakllantirdik.
    pass

async def start_ain_bot():
    print("✅ Bot Lotin/Kril va Sinxronizatsiya bilan ishga tushdi.")
    asyncio.create_task(post_worker())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(start_ain_bot())