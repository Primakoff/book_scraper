# Books Catalogue Scraper

A small, production-style web scraper that crawls a paginated product
catalogue, cleans the data, and exports it to **CSV** and **JSON**.

Built as a learning / portfolio project to demonstrate practical web
scraping skills with `requests` and `BeautifulSoup4`: pagination handling,
retries, logging, polite request delays, and clean data export.

> Target site: [books.toscrape.com](https://books.toscrape.com) — a sandbox
> site explicitly built for scraping practice (1000 products, 50 pages).

## Features

- Crawls **all pages** automatically by following the "next" button
  (no hard-coded page count)
- Extracts title, price (number + currency), star rating, availability and URL
- **Retries** failed requests with increasing back-off
- **Logging** of progress and errors
- **Polite delay** between requests to avoid hammering the server
- Command-line interface (output folder, format, delay, page limit)
- Exports to **CSV** (Excel-friendly) and **JSON**

## Tech stack

- Python 3.10+
- [requests](https://pypi.org/project/requests/) — HTTP requests
- [beautifulsoup4](https://pypi.org/project/beautifulsoup4/) — HTML parsing

## Installation

```bash
# Clone the repo
git clone https://github.com/<your-username>/books-scraper.git
cd books-scraper

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
# Scrape everything to ./data/ in both CSV and JSON
python scraper.py

# Only the first 5 pages, JSON only, with a 1.5s delay
python scraper.py --max-pages 5 --format json --delay 1.5

# Custom output folder
python scraper.py --output-dir results
```

### CLI options

| Option | Default | Description |
|--------|---------|-------------|
| `--output-dir` | `data` | Folder for output files |
| `--format` | `both` | `csv`, `json`, or `both` |
| `--delay` | `1.0` | Seconds to wait between requests |
| `--max-pages` | (all) | Limit number of pages (useful for testing) |

## Example output

`data/books.json`

```json
[
  {
    "title": "A Light in the Attic",
    "price": 51.77,
    "currency": "£",
    "rating": 3,
    "availability": "In stock",
    "url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
  }
]
```

## Project structure

```
books-scraper/
├── scraper.py          # main script
├── requirements.txt    # dependencies
├── README.md           # this file
├── .gitignore
└── data/               # generated output (git-ignored)
```

## Responsible scraping

This project targets a site designed for scraping practice. When adapting it
to other sites, always:

- check the site's `robots.txt` and Terms of Service,
- keep request rates low (the built-in `--delay`),
- identify your scraper honestly and avoid collecting personal data.

## License

MIT — feel free to reuse and adapt.