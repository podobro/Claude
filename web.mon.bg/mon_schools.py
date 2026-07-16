"""Регистър на МОН (web.mon.bg/bg/100107) — училища и детски градини.

Регистърът се предлага като изтегляем файл — първо търсим CSV/XLSX линкове
на страницата и ги парсваме с pandas, вместо да скрейпваме HTML.
"""
import io
import re

import pandas as pd

from base import BaseScraper

FILE_RE = re.compile(r"\.(xlsx|xls|csv)(\?|$)", re.I)

# Евристично разпознаване на колоните в експортирания файл.
COLUMN_HINTS = {
    "ime": ("наименование", "име", "училище", "институция", "детска градина"),
    "grad": ("населено място", "град", "село", "нас. място"),
    "adres": ("адрес",),
    "telefon": ("телефон", "тел."),
    "email": ("mail", "имейл", "e-mail", "поща"),
    "uebsait": ("сайт", "уеб", "web", "интернет"),
    "podkategoria": ("вид", "тип"),
}


def _match_column(columns, hints):
    for col in columns:
        low = str(col).lower()
        if any(h in low for h in hints):
            return col
    return None


class MonSchoolsScraper(BaseScraper):
    name = "mon_schools"

    def scrape(self) -> None:
        soup = self.soup(self.base_url)
        if soup is None:
            return
        file_links = []
        for a in soup.find_all("a", href=True):
            href = self.abs_url(a["href"], self.base_url)
            if FILE_RE.search(href) and href not in file_links:
                file_links.append(href)
        if not file_links:
            self.log.warning(
                "Няма CSV/XLSX линкове на %s — регистърът може да изисква "
                "ръчно сваляне (вж. README)", self.base_url,
            )
            return

        for url in file_links:
            self.log.info("Свалям регистър: %s", url)
            self._rate_limit(url)
            resp = self.client.get(url)
            if resp.status_code != 200:
                self.errors += 1
                continue
            self.pages_visited += 1
            try:
                if url.lower().split("?")[0].endswith(".csv"):
                    df = pd.read_csv(io.BytesIO(resp.content))
                else:
                    df = pd.read_excel(io.BytesIO(resp.content))
            except Exception as e:  # noqa: BLE001
                self.log.warning("Не мога да парсна %s: %s", url, e)
                self.errors += 1
                continue

            cols = {k: _match_column(df.columns, v) for k, v in COLUMN_HINTS.items()}
            if not cols["ime"]:
                self.log.warning("Файлът %s няма разпознаваема колона с име", url)
                continue
            for _, row in df.iterrows():
                def val(key):
                    c = cols.get(key)
                    v = row.get(c) if c else None
                    return "" if pd.isna(v) else str(v).strip()
                self.add_record(
                    ime=val("ime"), grad=val("grad"), adres=val("adres"),
                    telefon=val("telefon"), email=val("email"),
                    uebsait=val("uebsait"), podkategoria=val("podkategoria"),
                    iztochnik=url,
                )
            self.save_checkpoint()
