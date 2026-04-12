# AvtoBozor — O'rnatish va Ishga Tushurish

## Fayl tuzilmasi
```
avtobozor/
├── app_main.py          ← Flask backend (API + static server)
├── bot.py               ← Telegram bot
├── channel_parser.py    ← Kanal parser (ixtiyoriy)
├── .env                 ← Sozlamalar
├── requirements.txt     ← Python paketlar
├── static/
│   ├── AvtoBozor2.html  ← Mini App (shu papkaga ko'chiring)
│   └── uploads/         ← Avtomatik yaratiladi
└── database.db          ← Avtomatik yaratiladi
```

## O'rnatish

```bash
pip install -r requirements.txt
```

## .env faylini tahrirlang
```
BOT_TOKEN=...
API_ID=...
API_HASH=...
MINI_APP_URL=https://sizningsayting.com/static/AvtoBozor2.html
DOMAIN=https://sizningsayting.com
ADMIN_ID=584067347
CHANNEL_ID=-1003666619602
GROUP_LINK=https://t.me/+guruhhavolasi
```

## HTML faylini ko'chirish
```bash
mkdir -p static
cp AvtoBozor2.html static/AvtoBozor2.html
```

## Ishga tushurish (3 ta alohida terminal)

### 1. Flask backend (doim ishlashi kerak)
```bash
python app_main.py
```

### 2. Telegram bot (doim ishlashi kerak)
```bash
python bot.py
```

### 3. Kanal parser (ixtiyoriy)
```bash
python channel_parser.py
# Birinchi marta telefon raqam va kod so'raladi
```

## PythonAnywhere uchun
- `app_main.py` → Web App sifatida sozlang (port 8080)
- `bot.py` → Always-on task sifatida
- `channel_parser.py` → Always-on task sifatida (ixtiyoriy)

## VIP tizimi
1. Foydalanuvchi "🔗 Do'stlarni taklif qilish" tugmasini bosadi
2. Bot unga shaxsiy havola beradi
3. Do'sti shu havola orqali botga kiradi
4. Guruhga link biriktirilgan (GROUP_LINK) — do'sti shu guruhga qo'shiladi
5. **10 ta taklif** → 24 soat VIP
6. **20 ta taklif** → 48 soat VIP
7. E'lon bergandan keyin "✅ Tekshirish" bosiladi — VIP avtomatik beriladi
