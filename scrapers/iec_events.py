"""Интер Експо Център (iec.bg) — календар на изложенията: организатори."""
import re

from scrapers.base import BaseScraper, extract_emails, extract_phones

CALENDAR_PATHS = ["/bg/izlozheniya", "/bg/events", "/events", "/bg/calendar", "/"]
EVENT_LINK_RE = re.compile(r"/(event|izlozheni|exhibition|sabitie)", re.I)
ORGANIZER_RE = re.compile(r"Организатор[:\s]+(.{3,120}?)(?:\n|Тел|Email|E-mail|$)", re.I)


class IecEventsScraper(BaseScraper):
    name = "iec_events"

    def scrape(self) -> None:
        event_urls: list[str] = []
        for path in CALENDAR_PATHS:
            soup = self.soup(self.abs_url(path))
            if soup is None:
                continue
            for a in soup.find_all("a", href=True):
                href = self.abs_url(a["href"])
                if EVENT_LINK_RE.search(href) and href not in event_urls:
                    event_urls.append(href)
            if event_urls:
                break

        for url in event_urls:
            page = self.soup(url)
            if page is None:
                continue
            text = page.get_text("\n", strip=True)
            h1 = page.find(["h1", "h2"])
            event = h1.get_text(strip=True) if h1 else url
            m = ORGANIZER_RE.search(text)
            organizer = m.group(1).strip() if m else ""
            emails = extract_emails(text)
            phones = extract_phones(text)
            if not organizer and not emails and not phones:
                continue
            self.add_record(
                ime=organizer or f"Организатор на {event}",
                grad="София",
                telefon=phones[0] if phones else "",
                email=emails[0] if emails else "",
                podkategoria="Организатор на изложение",
                dopalnitelno=f"Събитие: {event}",
                iztochnik=url,
            )
            self.save_checkpoint()
