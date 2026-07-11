"""Национален туристически регистър (ntr.tourism.government.bg) — хотели.

Първо търсим export функция (CSV/XLSX). Регистърът е с JS рендиране,
затова при липса на export използваме Playwright.
"""
import io
import re

import pandas as pd

from scrapers.base import BaseScraper, extract_phones

FILE_RE = re.compile(r"\.(xlsx|xls|csv)(\?|$)", re.I)
STARS_RE = re.compile(r"(\d)\s*звезд", re.I)


class NtrHotelsScraper(BaseScraper):
    name = "ntr_hotels"

    def scrape(self) -> None:
        # 1) Опит за директен export файл.
        soup = self.soup(self.base_url)
        if soup is not None:
            for a in soup.find_all("a", href=True):
                href = self.abs_url(a["href"], self.base_url)
                if FILE_RE.search(href):
                    if self._parse_export(href):
                        return
        # 2) JS таблица през Playwright.
        self._scrape_with_playwright()

    def _parse_export(self, url: str) -> bool:
        self.log.info("Открит export: %s", url)
        self._rate_limit(url)
        resp = self.client.get(url)
        if resp.status_code != 200:
            self.errors += 1
            return False
        self.pages_visited += 1
        try:
            if url.lower().split("?")[0].endswith(".csv"):
                df = pd.read_csv(io.BytesIO(resp.content))
            else:
                df = pd.read_excel(io.BytesIO(resp.content))
        except Exception as e:  # noqa: BLE001
            self.log.warning("Неуспешен парсинг на export %s: %s", url, e)
            return False

        def find(colhints):
            for c in df.columns:
                if any(h in str(c).lower() for h in colhints):
                    return c
            return None

        c_ime = find(("наименование", "име", "обект"))
        c_grad = find(("населено", "град"))
        c_adres = find(("адрес",))
        c_kat = find(("категория", "звезди"))
        c_vid = find(("вид",))
        if not c_ime:
            return False
        for _, row in df.iterrows():
            def val(c):
                v = row.get(c) if c else None
                return "" if pd.isna(v) else str(v).strip()
            self.add_record(
                ime=val(c_ime), grad=val(c_grad), adres=val(c_adres),
                podkategoria=val(c_vid) or "Място за настаняване",
                dopalnitelno=f"Категория: {val(c_kat)}" if val(c_kat) else "",
                iztochnik=url,
            )
        self.save_checkpoint()
        return len(self.records) > 0

    def _scrape_with_playwright(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.log.error("playwright не е инсталиран — пропускам JS обхождането")
            return
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(user_agent=None)
            page.goto(self.base_url, wait_until="networkidle", timeout=60000)
            self.pages_visited += 1
            # Търсим таблица с категоризирани места за настаняване.
            rows = page.locator("table tbody tr")
            count = rows.count()
            self.log.info("Открити %d реда в таблицата", count)
            for i in range(count):
                cells = [c.strip() for c in rows.nth(i).locator("td").all_inner_texts()]
                if len(cells) < 2:
                    continue
                text = " | ".join(cells)
                m = STARS_RE.search(text)
                phones = extract_phones(text)
                self.add_record(
                    ime=cells[0], grad=cells[1] if len(cells) > 1 else "",
                    adres=cells[2] if len(cells) > 2 else "",
                    telefon=phones[0] if phones else "",
                    podkategoria="Място за настаняване",
                    dopalnitelno=f"{m.group(1)} звезди" if m else "",
                    iztochnik=self.base_url,
                )
            browser.close()
        self.save_checkpoint()
