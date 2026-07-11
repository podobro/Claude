"""БФС (bfunion.bg) — футболни клубове по лиги."""
import re

from scrapers.base import BaseScraper, extract_emails, extract_phones

LEAGUE_PATHS = {
    "/first-league": "Футболен клуб — Първа лига",
    "/second-league": "Футболен клуб — Втора лига",
    "/bg/first-league": "Футболен клуб — Първа лига",
    "/bg/second-league": "Футболен клуб — Втора лига",
}
CLUB_LINK_RE = re.compile(r"/(team|club|otbor|klub)", re.I)


class BfsClubsScraper(BaseScraper):
    name = "bfs_clubs"

    def scrape(self) -> None:
        found_any = False
        for path, label in LEAGUE_PATHS.items():
            soup = self.soup(self.abs_url(path))
            if soup is None:
                continue
            club_links = {}
            for a in soup.find_all("a", href=True):
                href = self.abs_url(a["href"])
                nm = a.get_text(strip=True)
                if CLUB_LINK_RE.search(href) and nm and href not in club_links:
                    club_links[href] = nm
            for url, nm in club_links.items():
                page = self.soup(url)
                grad, phone, email = "", "", ""
                if page is not None:
                    text = page.get_text(" ", strip=True)
                    m = re.search(r"(?:гр\.|град)\s*([А-Яа-я\- ]{3,25})", text)
                    grad = m.group(1).strip() if m else ""
                    phones = extract_phones(text)
                    emails = extract_emails(text)
                    phone = phones[0] if phones else ""
                    email = emails[0] if emails else ""
                self.add_record(
                    ime=nm, grad=grad, telefon=phone, email=email,
                    podkategoria=label, iztochnik=url,
                )
                found_any = True
            self.save_checkpoint()
        if not found_any:
            self.log.warning("Не открих клубове — проверете LEAGUE_PATHS")
