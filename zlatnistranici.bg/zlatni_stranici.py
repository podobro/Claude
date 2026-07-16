"""Златни страници (zlatnistranici.bg) — същите категории като Business.bg.

Каталогът поддържа търсене по ключова дума — обхождаме резултатите
за всяка целева категория.
"""
from urllib.parse import quote

import config
from base import BaseScraper, extract_emails, extract_phones

SEARCH_URL = "https://www.zlatnistranici.bg/търсене/{kw}"


class ZlatniStraniciScraper(BaseScraper):
    name = "zlatni_stranici"

    def scrape(self) -> None:
        categories = config.SOURCES[self.name]["categories"]
        if self.category_filter:
            categories = {k: v for k, v in categories.items()
                          if k == self.category_filter}
            if not categories:
                self.log.error("Непозната категория: %s", self.category_filter)
                return

        for kw, label in categories.items():
            url = SEARCH_URL.format(kw=quote(kw))
            self._scrape_results(url, label)

    def _scrape_results(self, url: str, label: str, max_pages: int = 30) -> None:
        seen = set()
        queue = [url]
        while queue and len(seen) < max_pages:
            page_url = queue.pop(0)
            if page_url in seen:
                continue
            seen.add(page_url)
            soup = self.soup(page_url)
            if soup is None:
                continue
            for item in soup.find_all(["li", "div", "article", "tr"]):
                text = item.get_text(" ", strip=True)
                if len(text) > 600 or len(text) < 15:
                    continue
                phones = extract_phones(text)
                if not phones:
                    continue
                heading = item.find(["h2", "h3", "h4", "a", "strong", "b"])
                ime = heading.get_text(strip=True) if heading else text[:60]
                emails = extract_emails(text)
                if any(r["ime"] == ime and r["telefon"] == phones[0]
                       for r in self.records[-50:]):
                    continue
                self.add_record(
                    ime=ime, podkategoria=label,
                    telefon=phones[0], email=emails[0] if emails else "",
                    iztochnik=page_url,
                )
            for a in soup.find_all("a", href=True):
                t = a.get_text(strip=True).lower()
                if t in (">", "следваща", "напред", "next") or t.isdigit():
                    nxt = self.abs_url(a["href"], page_url)
                    if nxt not in seen:
                        queue.append(nxt)
            self.save_checkpoint()
