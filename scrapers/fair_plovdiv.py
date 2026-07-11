"""Пловдивски панаир (fair.bg) — организатор на изложения.

Всяко изложение (/bg/event/<год>/<slug>) е организирано от Международен
панаир Пловдив и има свой отговорник с имейл (mailto:) и телефон.
Извличаме по един запис на изложение с контакта за участие.
"""
import re

from scrapers.base import BaseScraper, extract_phones

EVENTS_URL = "https://www.fair.bg/bg/events/event/upcoming/2026"
EVENT_RE = re.compile(r"/bg/event/\d{4}/[a-z0-9-]+$")


class FairPlovdivScraper(BaseScraper):
    name = "fair_plovdiv"

    def scrape(self) -> None:
        event_urls: dict[str, str] = {}
        for listing in (EVENTS_URL, "https://www.fair.bg/bg/events"):
            soup = self.soup_safe(listing)
            if soup is None:
                continue
            for a in soup.find_all("a", href=True):
                href = a["href"].rstrip("/")
                if EVENT_RE.search(href):
                    url = self.abs_url(href)
                    if url not in event_urls:
                        event_urls[url] = a.get_text(strip=True)
        self.log.info("Открити %d изложения", len(event_urls))

        for url in event_urls:
            page = self.soup_safe(url)
            if page is None:
                continue
            # Име на изложението от URL slug (надеждно; h1 е общ банер).
            slug = url.rstrip("/").rsplit("/", 1)[-1]
            event = slug.replace("-", " ").upper()

            mails = [a["href"].replace("mailto:", "").strip()
                     for a in page.find_all("a", href=re.compile(r"mailto:"))]
            # Предпочитаме конкретния отговорник на изложението пред общите кутии.
            generic = {"info@fair.bg", "fairinfo@fair.bg", "office@fair.bg"}
            specific = [m for m in mails if m.lower() not in generic]
            email = (specific or mails or [""])[0]

            text = page.get_text(" ", strip=True)
            # Телефоните на панаира са в централата 032 902 xxx — филтрираме,
            # за да не хванем дати (напр. „22 04 2026") като телефон.
            phones = [p for p in extract_phones(text) if p.startswith("+35932902")]
            if not phones:
                phones = extract_phones(text)

            self.add_record(
                ime="Международен панаир Пловдив",
                grad="Пловдив",
                telefon=phones[0] if phones else "",
                email=email,
                uebsait="https://www.fair.bg",
                podkategoria="Организатор на изложение",
                dopalnitelno=f"Изложение: {event}",
                iztochnik=url,
            )
            self.save_checkpoint()
