"""НСОРБ (namrb.org) — всички 265 общини: име, адрес, телефон, имейл, сайт."""
import re

from scrapers.base import BaseScraper, extract_emails, extract_phones

# Страници, на които може да живее списъкът с общини.
START_PATHS = [
    "/bg/obshtinite-dnes",
    "/bg/obshtini",
    "/municipalities-today",
    "/en/municipalities-today/29",
    "/",
]

MUNICIPALITY_LINK_RE = re.compile(r"(obshtin|municipalit)", re.I)


class NamrbScraper(BaseScraper):
    name = "namrb"

    def scrape(self) -> None:
        state = self.load_checkpoint()
        done = set(state.get("done_urls", []))

        detail_urls: list[str] = []
        for path in START_PATHS:
            soup = self.soup(self.abs_url(path))
            if soup is None:
                continue
            for a in soup.find_all("a", href=True):
                href = self.abs_url(a["href"])
                if MUNICIPALITY_LINK_RE.search(href) and href not in detail_urls:
                    detail_urls.append(href)
            if len(detail_urls) > 50:  # намерили сме каталога
                break

        if not detail_urls:
            self.log.warning("Не открих списък с общини — проверете START_PATHS")
            return

        for url in detail_urls:
            if url in done:
                continue
            soup = self.soup(url)
            if soup is None:
                continue
            h1 = soup.find(["h1", "h2"])
            ime = h1.get_text(strip=True) if h1 else ""
            if "община" not in ime.lower():
                if not ime:
                    continue
                ime = f"Община {ime}"
            text = soup.get_text(" ", strip=True)
            emails = extract_emails(text)
            phones = extract_phones(text)
            site = ""
            for a in soup.find_all("a", href=True):
                if a["href"].startswith("http") and "namrb" not in a["href"]:
                    site = a["href"]
                    break
            grad = ime.replace("Община", "").strip()
            self.add_record(
                ime=ime, grad=grad,
                telefon=phones[0] if phones else "",
                email=emails[0] if emails else "",
                uebsait=site, iztochnik=url,
            )
            done.add(url)
            if len(done) % 20 == 0:
                self.save_checkpoint({"done_urls": sorted(done)})

        self.save_checkpoint({"done_urls": sorted(done)})
