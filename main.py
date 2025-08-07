import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import json
import os
import time
from dotenv import load_dotenv

TELEGRAM_TOKEN='7796095559:AAEHWAE8FehvcNw2UNK5hru_O33SjS-4q6E'
TELEGRAM_CHAT_ID=6202982315

HEADERS = {
    "User-Agent": UserAgent().random
}
SEARCH_URL = "https://www.olx.pl/oferty/q-oculus-quest-2/?search%5Border%5D=created_at%3Adesc"
BASE_URL = "https://www.olx.pl"

SEEN_FILE = "seen.json"

def load_seen_ids():
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, "r") as f:
        return set(json.load(f))

def save_seen_ids(seen_ids):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen_ids), f)

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
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
        ad_id = full_url.split("-ID")[1].split(".")[0]

        if ad_id in seen_ids:
            continue

        title_tag = item.select_one("h4")
        price_tag = item.select_one("p[data-testid='ad-price']")

        ad = {
            "id": ad_id,
            "title": title_tag.text.strip() if title_tag else "Нет заголовка",
            "price": price_tag.text.strip() if price_tag else "Цена не указана",
            "url": full_url
        }
        ads.append(ad)

    return ads

def main():
    print("[*] Запуск парсера OLX.pl")
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

        time.sleep(12 * 5)  # каждые 5 минут

if __name__ == "__main__":
    main()
