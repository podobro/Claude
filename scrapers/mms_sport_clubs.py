"""Регистър на ММС (mmsbg.info) — публичен регистър на спортните клубове."""
import re

from scrapers.base import BaseScraper, extract_emails, extract_phones

REGISTER_HINT_RE = re.compile(r"(регистър|клуб|register|club)", re.I)


class MmsSportClubsScraper(BaseScraper):
    name = "mms_sport_clubs"

    def scrape(self) -> None:
        home = self.soup(self.base_url)
        if home is None:
            return
        register_urls = []
        for a in home.find_all("a", href=True):
            if REGISTER_HINT_RE.search(a.get_text(strip=True)) or \
               REGISTER_HINT_RE.search(a["href"]):
                url = self.abs_url(a["href"])
                if url not in register_urls:
                    register_urls.append(url)

        for url in register_urls[:10]:
            soup = self.soup(url)
            if soup is None:
                continue
            # Регистърът обикновено е таблица: клуб, град, спорт, контакти.
            for tr in soup.find_all("tr"):
                cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
                if len(cells) < 2 or not cells[0]:
                    continue
                text = " | ".join(cells)
                phones = extract_phones(text)
                emails = extract_emails(text)
                self.add_record(
                    ime=cells[0],
                    grad=cells[1] if len(cells) > 1 else "",
                    telefon=phones[0] if phones else "",
                    email=emails[0] if emails else "",
                    podkategoria="Спортен клуб",
                    dopalnitelno=cells[2] if len(cells) > 2 else "",
                    iztochnik=url,
                )
            self.save_checkpoint()
        if not self.records:
            self.log.warning("Не открих регистърна таблица на %s", self.base_url)
