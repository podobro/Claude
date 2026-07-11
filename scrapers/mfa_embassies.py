"""МВнР (mfa.bg) — задгранични мисии: име, адрес, телефон, имейл."""
import re

from scrapers.base import BaseScraper, extract_emails, extract_phones

LISTING_PATH = "/bg/embassyinfo"
MISSION_LINK_RE = re.compile(r"/(embass|consul|mission|embassyinfo)", re.I)

LABELS = {
    "adres": re.compile(r"Адрес[:\s]+(.{5,200}?)(?:Телефон|Тел|E-mail|Имейл|Факс|$)", re.I | re.S),
}


class MfaEmbassiesScraper(BaseScraper):
    name = "mfa_embassies"

    def scrape(self) -> None:
        state = self.load_checkpoint()
        done = set(state.get("done_urls", []))

        soup = self.soup(self.base_url)
        if soup is None:
            return
        links: list[str] = []
        for a in soup.find_all("a", href=True):
            href = self.abs_url(a["href"], self.base_url)
            if MISSION_LINK_RE.search(href) and href.rstrip("/") != self.base_url.rstrip("/"):
                if href not in links:
                    links.append(href)

        for url in links:
            if url in done:
                continue
            page = self.soup(url)
            if page is None:
                continue
            h1 = page.find(["h1", "h2"])
            ime = h1.get_text(strip=True) if h1 else ""
            if not ime:
                continue
            text = page.get_text(" ", strip=True)
            emails = extract_emails(text)
            phones = extract_phones(text)
            m = LABELS["adres"].search(text)
            adres = m.group(1).strip() if m else ""
            self.add_record(
                ime=ime, adres=adres,
                telefon=phones[0] if phones else "",
                email=emails[0] if emails else "",
                podkategoria="Задгранична мисия",
                iztochnik=url,
            )
            done.add(url)
            if len(done) % 20 == 0:
                self.save_checkpoint({"done_urls": sorted(done)})

        self.save_checkpoint({"done_urls": sorted(done)})
