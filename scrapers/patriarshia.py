"""Българска патриаршия (bg-patriarshia.bg) — епархии: адрес, телефон."""
import re

from scrapers.base import BaseScraper, extract_emails, extract_phones

EPARCHY_LINK_RE = re.compile(r"(eparhi|епархи|mitropol|митрополи)", re.I)
ADDRESS_RE = re.compile(r"(?:Адрес|адрес)[:\s]+(.{5,150}?)(?:\n|Тел|тел|$)")


class PatriarshiaScraper(BaseScraper):
    name = "patriarshia"

    def scrape(self) -> None:
        home = self.soup(self.base_url)
        if home is None:
            return
        eparchy_urls = {}
        for a in home.find_all("a", href=True):
            nm = a.get_text(strip=True)
            if EPARCHY_LINK_RE.search(a["href"]) or EPARCHY_LINK_RE.search(nm):
                url = self.abs_url(a["href"])
                if url not in eparchy_urls and nm:
                    eparchy_urls[url] = nm

        if not eparchy_urls:
            self.log.warning("Не открих линкове към епархии")
            return

        for url, nm in eparchy_urls.items():
            page = self.soup(url)
            if page is None:
                continue
            text = page.get_text("\n", strip=True)
            m = ADDRESS_RE.search(text)
            phones = extract_phones(text)
            emails = extract_emails(text)
            self.add_record(
                ime=nm if "епархия" in nm.lower() or "митрополия" in nm.lower()
                    else f"{nm} (епархия)",
                adres=m.group(1).strip() if m else "",
                telefon=phones[0] if phones else "",
                email=emails[0] if emails else "",
                podkategoria="Епархия",
                iztochnik=url,
            )
            self.save_checkpoint()
