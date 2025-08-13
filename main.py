import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import json
import os
import time
import threading
from datetime import datetime

TELEGRAM_TOKEN = '7796095559:AAEHWAE8FehvcNw2UNK5hru_O33SjS-4q6E'
TELEGRAM_CHAT_ID = 6202982315

HEADERS = {
    "User-Agent": UserAgent().random
}
SEARCH_URL = "https://olx.pl/oferty/q-maszyna-do-szycia/?search%5Bfilter_float_price%3Afrom%5D=free&search%5Border%5D=relevance%3Adesc"
BASE_URL = "https://www.olx.pl"

SEEN_FILE = "seen.json"
LAST_UPDATE_FILE = "last_update.json"

def load_seen_ids():
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, "r") as f:
        return set(json.load(f))

def save_seen_ids(seen_ids):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen_ids), f)

def send_telegram_message(text, chat_id=TELEGRAM_CHAT_ID):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, data=data)
        if not response.ok:
            print(f"[!] Telegram error: {response.text}")
    except Exception as e:
        print(f"[!] Telegram exception: {e}")


def fetch_new_ads(seen_ids):
    try:
        response = requests.get(SEARCH_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[!] Request failed: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    ads = []

    for item in soup.select("div[data-cy='l-card']"):
        link_tag = item.select_one("a")
        if not link_tag:
            continue
        url = link_tag["href"]
        full_url = url if url.startswith("http") else BASE_URL + url

        ad_id_part = full_url.split("-ID")
        if len(ad_id_part) < 2:
            continue
        ad_id = ad_id_part[1].split(".")[0]

        if ad_id in seen_ids:
            continue

        title_tag = item.select_one("h4")
        price_tag = item.select_one("p[data-testid='ad-price']")
        date_tag = item.select_one("p[data-testid='location-date']")

        if not date_tag:
            continue

        date_text = date_tag.text.strip().lower()

        if "dzisiaj" not in date_text:
            continue  # ⛔️ Пропускаем, если не сегодня

        ad = {
            "id": ad_id,
            "title": title_tag.text.strip() if title_tag else "Нет заголовка",
            "price": price_tag.text.strip() if price_tag else "Цена не указана",
            "url": full_url
        }
        ads.append(ad)

    return ads

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"timeout": 10}
    if offset:
        params["offset"] = offset
    try:
        response = requests.get(url, params=params)
        return response.json()["result"]
    except Exception as e:
        print(f"[!] Error fetching updates: {e}")
        return []

def load_last_update_id():
    if os.path.exists(LAST_UPDATE_FILE):
        with open(LAST_UPDATE_FILE, "r") as f:
            return json.load(f).get("last_update_id")
    return None

def save_last_update_id(update_id):
    with open(LAST_UPDATE_FILE, "w") as f:
        json.dump({"last_update_id": update_id}, f)

def echo_loop():
    print("[*] Эхо-бот запущен")
    while True:
        last_update_id = load_last_update_id()
        updates = get_updates(offset=last_update_id + 1 if last_update_id else None)

        for update in updates:
            if "message" in update:
                chat_id = update["message"]["chat"]["id"]
                text = update["message"].get("text")
                if text:
                    send_telegram_message(f"Эхо: {text}", chat_id)
            last_update_id = update["update_id"]

        if last_update_id:
            save_last_update_id(last_update_id)

        time.sleep(2)  # проверка сообщений каждые 2 секунды

def parser_loop():
    print("[*] Парсер OLX запущен")
    seen_ids = load_seen_ids()

    while True:
        new_ads = fetch_new_ads(seen_ids)
        if new_ads:
            print(f"[+] Найдено {len(new_ads)} новых объявлений")
            for ad in new_ads:
                msg = f"<b>{ad['title']}</b>\n{ad['price']}\n{ad['url']}"
                send_telegram_message(msg)
                seen_ids.add(ad['id'])
            save_seen_ids(seen_ids)
        else:
            print("[-] Новых объявлений нет.")

        time.sleep(20)  # парсинг каждые 5 минут

def main():
    echo_thread = threading.Thread(target=echo_loop, daemon=True)
    parser_thread = threading.Thread(target=parser_loop, daemon=True)

    echo_thread.start()
    parser_thread.start()

    echo_thread.join()
    parser_thread.join()

if __name__ == "__main__":
    main()
    
