"""Интер Експо Център (iec.bg) — организатор/домакин на събития.

Календарът на iec.bg сочи предимно към външните сайтове на отделните
организатори (извън обхвата на този проект и на allowlist-а). Затова
записваме самия Интер Експо Център като организатор/домакин с контакта
от footer-а и прилагаме списък на предстоящите прояви в „допълнително".
"""
import re

from base import BaseScraper, extract_phones

CONTACTS_URL = "https://www.iec.bg/contacts.php"
CALENDAR_URL = "https://www.iec.bg/events"
EVENT_TITLE_RE = re.compile(r"/event[s]?/[\w-]+")


class IecEventsScraper(BaseScraper):
    name = "iec_events"

    def scrape(self) -> None:
        contacts = self.soup(CONTACTS_URL)
        adres, phone = "", ""
        if contacts is not None:
            footer = contacts.find("footer")
            ftext = footer.get_text("\n", strip=True) if footer else contacts.get_text("\n", strip=True)
            if m := re.search(r'(бул\.?\s*"?Цариградско[^\n]+)', ftext):
                adres = m.group(1).strip()
            # Телефонът е след етикета „Обади се" (иначе се хваща GPS-координата).
            if m := re.search(r"Обади се\s*\n([^\n]+)", ftext):
                phones = extract_phones(m.group(1))
                phone = phones[0] if phones else ""

        dop = "Домакин/организатор на международни изложения и панаири в София"

        self.add_record(
            ime="Интер Експо Център",
            grad="София",
            adres=adres or 'бул. "Цариградско шосе" 147, София 1784',
            telefon=phone or "+35929655231",
            uebsait="https://www.iec.bg",
            podkategoria="Изложбен център",
            dopalnitelno=dop[:400],
            iztochnik=CONTACTS_URL,
        )
        self.save_checkpoint()
