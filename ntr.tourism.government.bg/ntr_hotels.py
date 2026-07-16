"""Национален туристически регистър — места за настаняване.

Регистърът (Lotus Domino) има Data Service REST API, което захранва
публичната таблица на mn.xsp — ползваме него вместо HTML скрейпинг:
/CategoryzationAll.nsf/api/data/collections/name/vRegistarMNValid1

Забележка: публичният регистър съдържа име/град/адрес/категория (звезди),
но НЕ публикува телефони и имейли.
"""
import json

from base import BaseScraper, RetryableHTTPError

API_URL = ("https://ntr.tourism.government.bg/CategoryzationAll.nsf"
           "/api/data/collections/name/vRegistarMNValid1")
PAGE_SIZE = 100  # максимумът, който API-то връща


class NtrHotelsScraper(BaseScraper):
    name = "ntr_hotels"

    def _fetch_page(self, page: int) -> list[dict]:
        self._rate_limit(API_URL)
        resp = self.client.get(API_URL, params={"ps": PAGE_SIZE, "page": page})
        if resp.status_code != 200:
            self.errors += 1
            raise RetryableHTTPError(f"HTTP {resp.status_code} за страница {page}")
        self.pages_visited += 1
        return resp.json()

    def scrape(self) -> None:
        state = self.load_checkpoint()
        page = state.get("next_page", 1)

        while True:
            try:
                items = self._fetch_page(page)
            except json.JSONDecodeError:
                self.log.warning("Невалиден JSON на страница %d — спирам", page)
                break
            if not items:
                break
            for it in items:
                stars = str(it.get("CategoryGiven", "")).strip()
                beds = it.get("TOBedsGiven", "")
                dop = "; ".join(x for x in (
                    f"Категория: {stars} звезди" if stars else "",
                    f"Легла: {beds}" if beds else "",
                    f"Удостоверение: {it.get('CNumber', '')}",
                ) if x)
                prefix = (it.get("Prefix") or "").strip()
                city = (it.get("TOCity") or "").strip()
                self.add_record(
                    ime=str(it.get("TOName", "")),
                    grad=f"{prefix} {city}".strip(),
                    adres=str(it.get("TOAddress", "")),
                    podkategoria=str(it.get("TOSubType1", "")) or "Място за настаняване",
                    dopalnitelno=dop,
                    iztochnik="https://ntr.tourism.government.bg/CategoryzationAll.nsf/mn.xsp",
                )
            total = items[0].get("@siblings", "?")
            if page % 20 == 0 or len(items) < PAGE_SIZE:
                self.log.info("Страница %d (общо %s записа в регистъра)", page, total)
            page += 1
            self.save_checkpoint({"next_page": page})
            if len(items) < PAGE_SIZE:
                break
