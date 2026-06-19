# -*- coding: utf-8 -*-
"""
Books Catalogue Scraper
=======================

Парсер каталога товаров с пагинацией. Собирает по всем страницам сайта
название, цену, рейтинг и наличие товара, очищает данные и выгружает
результат в CSV и/или JSON.

Демонстрационная цель: books.toscrape.com — сайт, специально предназначенный
для тренировки скрапинга (1000 товаров на 50 страницах).

Пример запуска:
    python scraper.py
    python scraper.py --format both --delay 1.0 --output-dir data
    python scraper.py --max-pages 5 --format json
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# --- Настройки по умолчанию -------------------------------------------------

BASE_URL = "https://books.toscrape.com/catalogue/page-1.html"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}

# Словесный рейтинг ("Three") -> число (3). Используется при парсинге.
RATING_MAP = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

# Настраиваем логирование: уровень, формат и вывод в консоль.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("scraper")


# --- Модель данных ----------------------------------------------------------

@dataclass
class Book:
    """Одна запись о товаре. dataclass даёт удобную сериализацию в dict."""
    title: str
    price: float
    currency: str
    rating: int
    availability: str
    url: str


# --- Сетевой слой -----------------------------------------------------------

def fetch_page(session: requests.Session, url: str, retries: int = 3,
               delay: float = 1.0) -> str | None:
    """
    Загружает HTML страницы с повторными попытками.

    Возвращает HTML-текст или None, если все попытки провалились.
    Это важно для реальной работы: сеть нестабильна, и одна ошибка
    не должна ронять весь парсинг.
    """
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, timeout=15)
            response.raise_for_status()
            response.encoding = "utf-8"
            return response.text
        except requests.RequestException as exc:
            log.warning("Попытка %d/%d не удалась (%s): %s",
                        attempt, retries, url, exc)
            if attempt < retries:
                time.sleep(delay * attempt)  # увеличиваем паузу с каждой попыткой
    log.error("Не удалось загрузить страницу после %d попыток: %s", retries, url)
    return None


# --- Парсинг ----------------------------------------------------------------

def parse_price(raw_price: str) -> tuple[float, str]:
    """
    Превращает строку цены вида '£51.77' в (51.77, '£').
    Возвращает число и символ валюты отдельно — так данными удобнее
    пользоваться дальше (сортировать, считать суммы).
    """
    raw_price = raw_price.strip()
    currency = raw_price[0] if raw_price and not raw_price[0].isdigit() else ""
    number = raw_price.lstrip("£$€ ").replace(",", "")
    try:
        return float(number), currency
    except ValueError:
        return 0.0, currency


def parse_books(html: str, page_url: str) -> list[Book]:
    """Извлекает все товары с одной страницы каталога."""
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("article", class_="product_pod")

    books: list[Book] = []
    for card in cards:
        # Название — в атрибуте title тега <a> внутри <h3>.
        link = card.h3.a
        title = link["title"].strip()

        # Относительную ссылку превращаем в абсолютную через urljoin.
        url = urljoin(page_url, link["href"])

        # Цена — в <p class="price_color">.
        price_raw = card.find("p", class_="price_color").text
        price, currency = parse_price(price_raw)

        # Рейтинг закодирован в классе: <p class="star-rating Three">.
        rating_classes = card.find("p", class_="star-rating")["class"]
        rating_word = next((c for c in rating_classes if c in RATING_MAP), None)
        rating = RATING_MAP.get(rating_word, 0)

        # Наличие — в <p class="instock availability">.
        availability = card.find("p", class_="instock").text.strip()

        books.append(Book(title, price, currency, rating, availability, url))

    return books


def find_next_url(html: str, current_url: str) -> str | None:
    """
    Ищет ссылку на следующую страницу (кнопка 'next').
    Возвращает абсолютный URL или None, если страниц больше нет.
    Это правильный способ обходить пагинацию — без жёсткого
    зашивания количества страниц в код.
    """
    soup = BeautifulSoup(html, "html.parser")
    next_li = soup.find("li", class_="next")
    if next_li and next_li.a:
        return urljoin(current_url, next_li.a["href"])
    return None


# --- Оркестрация ------------------------------------------------------------

def scrape_all(start_url: str, delay: float, max_pages: int | None) -> list[Book]:
    """Обходит все страницы каталога и собирает товары в один список."""
    session = requests.Session()
    session.headers.update(HEADERS)

    all_books: list[Book] = []
    url: str | None = start_url
    page_num = 0

    while url:
        page_num += 1
        if max_pages and page_num > max_pages:
            log.info("Достигнут лимит страниц (%d). Останавливаюсь.", max_pages)
            break

        log.info("Страница %d: %s", page_num, url)
        html = fetch_page(session, url, delay=delay)
        if html is None:
            break

        books = parse_books(html, url)
        all_books.extend(books)
        log.info("  собрано %d товаров (всего %d)", len(books), len(all_books))

        url = find_next_url(html, url)

        # Вежливая пауза между запросами, чтобы не нагружать сервер.
        if url:
            time.sleep(delay)

    return all_books


# --- Сохранение результатов -------------------------------------------------

def save_csv(books: list[Book], path: Path) -> None:
    """Сохраняет данные в CSV (utf-8-sig — чтобы корректно открылось в Excel)."""
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(books[0]).keys()))
        writer.writeheader()
        for book in books:
            writer.writerow(asdict(book))
    log.info("CSV сохранён: %s (%d строк)", path, len(books))


def save_json(books: list[Book], path: Path) -> None:
    """Сохраняет данные в JSON (ensure_ascii=False — для читаемого текста)."""
    data = [asdict(b) for b in books]
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info("JSON сохранён: %s (%d записей)", path, len(books))


# --- Точка входа / CLI ------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Парсер каталога товаров с пагинацией -> CSV/JSON."
    )
    parser.add_argument("--output-dir", default="data",
                        help="папка для результатов (по умолчанию: data)")
    parser.add_argument("--format", choices=["csv", "json", "both"],
                        default="both", help="формат выгрузки")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="пауза между запросами в секундах")
    parser.add_argument("--max-pages", type=int, default=None,
                        help="ограничить число страниц (для тестов)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    log.info("Запуск парсинга...")
    books = scrape_all(BASE_URL, delay=args.delay, max_pages=args.max_pages)

    if not books:
        log.error("Данные не собраны. Проверьте подключение к сети.")
        return 1

    log.info("Готово. Всего собрано товаров: %d", len(books))

    if args.format in ("csv", "both"):
        save_csv(books, output_dir / "books.csv")
    if args.format in ("json", "both"):
        save_json(books, output_dir / "books.json")

    return 0


if __name__ == "__main__":
    sys.exit(main())