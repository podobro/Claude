"""ЦАИС ЕОП (app.eop.bg) — възложители на приключили поръчки за знамена.

SPA приложение — Playwright. Търсим по ключови думи ("знамена", "знаме",
"флагове") в публичните обявления и извличаме възложител, град, стойност
и година на поръчката.
"""
import re

import config
from scrapers.base import BaseScraper

SEARCH_URL = "https://app.eop.bg/today/search?q={kw}"
YEAR_RE = re.compile(r"\b(20\d{2})\b")
VALUE_RE = re.compile(r"([\d\s.,]{3,})\s*(?:лв|BGN|EUR)", re.I)


class EopScraper(BaseScraper):
    name = "eop"

    def scrape(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.log.error("playwright не е инсталиран — пропускам")
            return

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            for kw in config.EOP_KEYWORDS:
                url = SEARCH_URL.format(kw=kw)
                self.log.info("Търсене: %s", kw)
                page.goto(url, wait_until="networkidle", timeout=90000)
                self.pages_visited += 1
                # Резултатите са карти/редове със заглавие и възложител.
                items = page.locator("[class*='result'], [class*='notice'], article")
                count = items.count()
                self.log.info("Открити %d резултата за '%s'", count, kw)
                for i in range(min(count, 200)):
                    text = items.nth(i).inner_text()
                    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
                    if not lines:
                        continue
                    title = lines[0]
                    vazlozhitel = ""
                    for ln in lines[1:]:
                        if any(w in ln.lower() for w in ("община", "министерство",
                                                         "агенция", "университет",
                                                         "болница", "дирекция")):
                            vazlozhitel = ln
                            break
                    year = YEAR_RE.search(text)
                    value = VALUE_RE.search(text)
                    dop = f"Поръчка: {title}"
                    if value:
                        dop += f"; стойност: {value.group(0)}"
                    if year:
                        dop += f"; година: {year.group(1)}"
                    self.add_record(
                        ime=vazlozhitel or title,
                        podkategoria=f"Купувач на '{kw}'",
                        dopalnitelno=dop,
                        iztochnik=url,
                    )
                self.save_checkpoint()
            browser.close()
