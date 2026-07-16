"""МВнР (mfa.bg/bg/embassyinfo) — задгранични мисии: име, адрес, тел., имейл.

Листингът съдържа линк към страница за всяка държава; на нея мисиите са
текстови блокове: „Посолство на Република България в …" / „Генерално
консулство …" с редове „Адрес:", „Тел.:", „Е-mail:", „Website:".
"""
import re

from base import BaseScraper, extract_emails, extract_phones

LISTING_URL = "https://www.mfa.bg/bg/embassyinfo"
MISSION_HEADER_RE = re.compile(
    r"^(Посолство на Република България[^\n]*|Генерално консулство[^\n]*|"
    r"Консулство на Република България[^\n]*|Постоянно представителство[^\n]*)$",
    re.M,
)
ADDRESS_RE = re.compile(r"Адрес:\s*([^\n]+)")
CITY_RE = re.compile(r"\sв\s+([А-ЯA-Z][^,\n]+)")


class MfaEmbassiesScraper(BaseScraper):
    name = "mfa_embassies"

    def scrape(self) -> None:
        state = self.load_checkpoint()
        done = set(state.get("done_urls", []))

        soup = self.soup(LISTING_URL)
        if soup is None:
            return
        country_urls = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/bg/embassyinfo/" in href:
                url = self.abs_url(href)
                if url not in country_urls:
                    country_urls.append(url)
        self.log.info("Открити %d държавни страници", len(country_urls))

        for url in country_urls:
            if url in done:
                continue
            page = self.soup_safe(url)
            if page is None:
                continue  # блокирана страница — ще пробваме пак при следващ пуск
            main = page.find("main") or page
            text = main.get_text("\n", strip=True)
            headers = list(MISSION_HEADER_RE.finditer(text))
            for i, m in enumerate(headers):
                start = m.start()
                end = headers[i + 1].start() if i + 1 < len(headers) else min(
                    len(text), start + 1500)
                block = text[start:end]
                ime = m.group(1).strip().rstrip(",")
                adr = ADDRESS_RE.search(block)
                city = CITY_RE.search(ime)
                emails = extract_emails(block)
                phones = extract_phones(block)
                self.add_record(
                    ime=ime,
                    grad=city.group(1).strip() if city else "",
                    adres=adr.group(1).strip() if adr else "",
                    telefon=phones[0] if phones else "",
                    email=emails[0] if emails else "",
                    podkategoria="Задгранична мисия",
                    iztochnik=url,
                )
            done.add(url)
            if len(done) % 10 == 0:
                self.save_checkpoint({"done_urls": sorted(done)})

        self.save_checkpoint({"done_urls": sorted(done)})
