"""НСОРБ (namrb.org) — всички общини от страницата „Членове на НСОРБ".

Данните са в една HTML таблица: ред с 1 клетка е област; ред с 8 клетки
(rowspan=2) е община: [община, население, кмет, адрес, пощ. код, тел. код,
телефон, факс]. Продължаващият 3-клетъчен ред (председател на ОбС) се
пропуска — не събираме лични имена. Забележка: регистърът НЕ съдържа
имейли и уебсайтове.
"""
import re

from base import BaseScraper, normalize_phone

MEMBERS_URL = "https://www.namrb.org/bg/tchlenove-na-nsorb"


def _first_phone(cell: str, tel_code: str) -> str:
    """Първият телефон от клетката, комбиниран с телефонния код при нужда."""
    for part in re.split(r"[;,]", cell):
        digits = re.sub(r"[^\d]", "", part)
        if len(digits) < 4:
            continue
        if digits.startswith("0"):          # пълен номер (вкл. мобилен)
            return normalize_phone(digits) or ""
        return normalize_phone(tel_code + digits) or ""
    return ""


class NamrbScraper(BaseScraper):
    name = "namrb"

    def scrape(self) -> None:
        soup = self.soup(MEMBERS_URL)
        if soup is None:
            return
        table = soup.find("table")
        if table is None:
            self.log.error("Няма таблица на %s — структурата е променена", MEMBERS_URL)
            return

        oblast = ""
        for tr in table.find_all("tr"):
            cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if len(cells) == 1 and cells[0]:
                oblast = cells[0].title()
                continue
            if len(cells) != 8 or cells[0].startswith("Област"):
                continue  # header или продължаващ ред с председателя на ОбС
            obshtina, naselenie, _kmet, adres, posht_kod, tel_kod, telefon, _fax = cells
            if not obshtina:
                continue
            ime = obshtina if "община" in obshtina.lower() else f"Община {obshtina}"
            grad = obshtina.replace("Столична община", "София").strip()
            adres_full = ", ".join(x for x in (adres.replace("''", '"'), posht_kod) if x and x != "-")
            self.add_record(
                ime=ime,
                grad=grad,
                adres=adres_full,
                telefon=_first_phone(telefon, tel_kod),
                podkategoria=f"Област {oblast}" if oblast else "",
                dopalnitelno=f"Население: {naselenie}" if naselenie else "",
                iztochnik=MEMBERS_URL,
            )
        self.save_checkpoint()
