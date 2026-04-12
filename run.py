import subprocess
import time
import sys
import os

def run_all():
    # Ishga tushirilishi kerak bo'lgan python fayllari
    # "html" qismi odatda main.py ichidagi API server orqali ishlaydi,
    # lekin agar alohida serveringiz bo'lsa ro'yxatga qo'shishingiz mumkin.
    scripts = [
    "app_main.py",   # <-- qo'shing
    "bot-1.py",
    "channel_parser.py"
]

    processes = []

    print("🛠 Tizim ishga tushmoqda...")

    for script in scripts:
        script_path = os.path.join(os.path.dirname(__file__), script)
        print(f"🚀 {script} ishga tushirilmoqda...")

        # subprocess.Popen orqali faylni ishga tushiramiz
        process = subprocess.Popen([sys.executable, script_path])
        processes.append(process)

        time.sleep(3) # 3 soniyalik oraliq kutish

    print("✅ Barcha botlar va API server muvaffaqiyatli ishga tushdi.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Barcha jarayonlar to'xtatilmoqda...")
        for p in processes:
            p.terminate()
        print("👋 Xayr!")

if __name__ == "__main__":
    run_all()