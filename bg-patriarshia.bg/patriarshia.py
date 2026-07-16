"""Българска патриаршия (bg-patriarshia.bg) — епархии: адрес, телефон, имейл.

Списъкът на епархиите е на /dioceses. Имейлите са скрити с Cloudflare
email-protection (data-cfemail) — декодираме ги. Телефоните са в tel:
линкове. Footer-ът съдържа централния контакт на Св. Синод, затова го
изключваме, за да вземем епархийския контакт от съдържанието.
"""
import re

from base import BaseScraper, extract_phones

DIOCESES_URL = "https://bg-patriarshia.bg/dioceses"
DIOCESE_RE = re.compile(r"/[a-z-]+-diocese$")


def cf_decode(hexstr: str) -> str:
    """Декодира Cloudflare-обфускиран имейл (XOR с първия байт)."""
    try:
        raw = bytes.fromhex(hexstr)
    except ValueError:
        return ""
    key = raw[0]
    return "".join(chr(b ^ key) for b in raw[1:])


class PatriarshiaScraper(BaseScraper):
    name = "patriarshia"

    def scrape(self) -> None:
        soup = self.soup(DIOCESES_URL)
        if soup is None:
            return
        dioceses: dict[str, str] = {}
        for a in soup.find_all("a", href=True):
            href = a["href"].rstrip("/")
            if DIOCESE_RE.search(href):
                name = a.get_text(strip=True)
                url = self.abs_url(href)
                if name and url not in dioceses:
                    dioceses[url] = name
        self.log.info("Открити %d епархии", len(dioceses))

        for url, name in dioceses.items():
            page = self.soup(url)
            if page is None:
                continue
            # Централният контакт на Св. Синод е във footer — премахваме го.
            for tag in page.find_all(["footer"]):
                tag.decompose()

            emails = [cf_decode(el.get("data-cfemail"))
                      for el in page.find_all(class_="__cf_email__")
                      if el.get("data-cfemail")]
            emails = [e for e in emails if "@" in e]

            tel = page.find("a", href=re.compile(r"tel:"))
            phone = tel["href"].replace("tel:", "") if tel else ""

            text = page.get_text("\n", strip=True)
            adres = ""
            if m := re.search(r"Адрес:\s*([^\n]{5,120})", text):
                adres = m.group(1).strip()
            if not phone:
                if m := re.search(r"Телефон:\s*([^\n]{5,40})", text):
                    ph = extract_phones(m.group(1))
                    phone = ph[0] if ph else ""

            self.add_record(
                ime=name,
                adres=adres,
                telefon=phone,
                email=emails[0] if emails else "",
                podkategoria="Епархия",
                iztochnik=url,
            )
        self.save_checkpoint()
