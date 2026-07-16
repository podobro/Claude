"""Business.bg — бизнес каталог: хотели, бензиностанции, автокъщи,
търговски центрове/строителни фирми, рекламни агенции.

Категорийните страници (o-<id>/<slug>.html) листват фирмени картички;
детайлните фирмени страници (f-<id>/<slug>.html) съдържат чисти
schema.org микроданни (itemprop=telephone/email/streetAddress). Пагинация:
o-<id>/s-<N>/<slug>.html.
"""
import re

from base import BaseScraper, ScrapeBlocked

# Ключ = URL slug на категория, стойност = (id, етикет за подкатегория).
CATEGORIES = {
    "hoteli": ("18", "hoteli.html", "Хотел"),
    "benzinostancii": ("77", "benzinostancii.html", "Бензиностанция"),
    "avtokyshti": ("340", "avtokyshti.html", "Автокъща"),
    "reklamni-agencii": ("394", "reklamni-agencii.html", "Рекламна агенция"),
    "stroitelni-firmi": ("747", "stroitelni-firmi.html", "Строителна фирма"),
}
FIRM_RE = re.compile(r"/f-\d+/[a-z0-9-]+\.html")


class BusinessBgScraper(BaseScraper):
    name = "business_bg"

    def scrape(self) -> None:
        cats = CATEGORIES
        if self.category_filter:
            cats = {k: v for k, v in CATEGORIES.items() if k == self.category_filter}
            if not cats:
                self.log.error("Непозната категория: %s (избери от %s)",
                               self.category_filter, ", ".join(CATEGORIES))
                return

        state = self.load_checkpoint()
        done = set(state.get("done_firms", []))

        for slug, (cat_id, page_file, label) in cats.items():
            firm_urls = self._collect_firms(cat_id, page_file)
            self.log.info("Категория %s: %d фирми", label, len(firm_urls))
            for url in firm_urls:
                if url in done:
                    continue
                try:
                    self._scrape_firm(url, label)
                except ScrapeBlocked:
                    raise
                done.add(url)
                if len(done) % 25 == 0:
                    self.save_checkpoint({"done_firms": sorted(done)})
            self.save_checkpoint({"done_firms": sorted(done)})

    def _collect_firms(self, cat_id: str, page_file: str, max_pages: int = 60) -> list[str]:
        urls: list[str] = []
        seen_urls = set()
        page = 0
        while page < max_pages:
            path = (f"/o-{cat_id}/{page_file}" if page == 0
                    else f"/o-{cat_id}/s-{page}/{page_file}")
            html = self.fetch(self.abs_url(path))
            if html is None:
                break
            found = [self.abs_url(m) for m in FIRM_RE.findall(html)]
            new = [u for u in found if u not in seen_urls]
            if not new:
                break
            for u in new:
                seen_urls.add(u)
                urls.append(u)
            page += 1
        return urls

    def _scrape_firm(self, url: str, label: str) -> None:
        soup = self.soup(url)
        if soup is None:
            return
        h1 = soup.find("h1")
        ime = h1.get_text(strip=True) if h1 else ""

        def itemprop(name):
            el = soup.find(attrs={"itemprop": name})
            if not el:
                return ""
            return (el.get("content") or el.get_text(" ", strip=True)).strip()

        phones = [a.get_text(strip=True) for a in
                  soup.find_all(attrs={"itemprop": "telephone"})]
        self.add_record(
            ime=ime,
            grad=itemprop("addressLocality"),
            adres=itemprop("streetAddress"),
            telefon=phones[0] if phones else "",
            email=itemprop("email"),
            podkategoria=label,
            iztochnik=url,
        )
