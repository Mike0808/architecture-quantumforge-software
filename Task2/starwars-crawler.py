import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import random
import json
import re
BASE = "https://starwars.fandom.com"
SEARCH_PATH = "/wiki/Special:Search"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/121.0 Safari/537.36"
}

def search_pages(query, limit=30, per_page=20):
    pages = []
    page = 1
    while len(pages) < limit:
        params = {
            "query": query,
            "scope": "internal",
            "limit": per_page,
            "page": page,
            "lang": "en"
        }
        resp = requests.get(urljoin(BASE, SEARCH_PATH), params=params, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print("Ошибка загрузки поиска:", resp.status_code)
            break

        soup = BeautifulSoup(resp.text, "html.parser")

        # --- правильный селектор: сам <a> имеет класс unified-search__result__title ---
        anchors = soup.select("a.unified-search__result__title, a.unified-search__result__link")
        if not anchors:
            print("Не найдено результатов на странице", page)
            break

        for a in anchors:
            href = a.get("href")
            if not href:
                continue
            # сделать абсолютной ссылку, если относительная
            href = urljoin(BASE, href)
            if href not in pages:
                pages.append(href)
                if len(pages) >= limit:
                    break

        page += 1
        time.sleep(random.uniform(0.8, 1.6))

    return pages[:limit]

def scrape_article(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
    except Exception as e:
        print("Ошибка запроса:", url, e)
        return None

    if r.status_code != 200:
        print("Страница не доступна:", url, r.status_code)
        return None

    soup = BeautifulSoup(r.text, "html.parser")

    # Заголовок
    title_tag = soup.select_one("h1.page-header__title") or soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Без названия"

    # Основной контент
    content_div = soup.select_one(".mw-parser-output")
    if not content_div:
        return {"url": url, "title": title, "text": ""}

    # Удаляем ненужные блоки: инфобокс, таблицы, оглавление, сноски
    for bad in content_div.select("aside, table, .pi-theme-character, .portable-infobox, .toc, .reference"):
        bad.decompose()

    # Берём только абзацы
    paragraphs = [
        p.get_text(" ", strip=True)
        for p in content_div.find_all("p")
        if p.get_text(strip=True)
    ]

    # Склеиваем в один текст — перенос только одинарный
    text = "\n".join(paragraphs)

    return {"url": url, "title": title, "text": text}

def normalize_prefix(query: str) -> str:
    # приводим к нижнему регистру, заменяем пробелы на _
    prefix = query.strip().lower().replace(" ", "_")
    # убираем лишние символы (оставляем буквы, цифры и "_")
    prefix = re.sub(r"[^a-z0-9_]+", "", prefix)
    return prefix

def save_json(articles, query, filename=None):
    prefix = normalize_prefix(query)
    filename = filename or f"{prefix}_articles.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

def save_txt(articles, query, filename=None):
    prefix = normalize_prefix(query)
    filename = filename or f"{prefix}_articles.txt"
    with open(filename, "w", encoding="utf-8") as f:
        for art in articles:
            f.write(f"# {art['title']}\n{art['url']}\n\n{art['text']}\n\n{'='*80}\n\n")


if __name__ == "__main__":
    query = "Eternal Empire conquest"  # 🔹 пример поискового слова
    limit = 5
    queries = [
            "Darth Bane",
    "Eternal Empire Conquest",
    "Galactic War",
    "Korriban",
    "Revan",
    "Sith Order",
    "Yoda",
    "Anakin Skywalker",
    "Obi-Wan Kenobi",
    "Mace Windu",
    "Count Dooku",
    "Darth Sidious",
    "Darth Maul",
    "Darth Vader",
    "Luke Skywalker",
    "Princess Leia",
    "Han Solo",
    "Chewbacca",
    "Lando Calrissian",
    "The Last Jedi",
    "Revenge of the Sith",
    "Galactic Republic",
    "Galactic Empire",
    "Clone Wars",
    "New Republic",
    "First Order",
    "Boba Fett",
    "Jango Fett",
    "Ahsoka Tano",
    "Asajj Ventress",
    "Qui-Gon Jinn"
    ]  # 🔹 теперь список поисковых слов
    
    print("Поиск ссылок...")
    for query in queries:
        urls = search_pages(query, limit=limit)
        print(f"Найдено ссылок: {len(urls)}")
        articles = []
        for i, u in enumerate(urls, 1):
            print(f"[{i}/{len(urls)}] Скачиваю {u}")
            art = scrape_article(u)
            if art:
                articles.append(art)
            time.sleep(random.uniform(0.8, 1.6))

        save_json(articles, query)
        save_txt(articles, query)
        print("Готово. Сохранено в darth_bane_articles.json и darth_bane_articles.txt")
