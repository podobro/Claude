"""Business.bg — бизнес каталог: хотели, бензиностанции, автокъщи,
търговски центрове, рекламни агенции."""
import config
from scrapers.base import BaseScraper, extract_emails, extract_phones


class BusinessBgScraper(BaseScraper):
    name = "business_bg"

    def scrape(self) -> None:
        categories = config.SOURCES[self.name]["categories"]
        if self.category_filter:
            categories = {k: v for k, v in categories.items()
                          if k == self.category_filter}
            if not categories:
                self.log.error("Непозната категория: %s", self.category_filter)
                return

        home = self.soup(self.base_url)
        if home is None:
            return

        for slug, label in categories.items():
            # Откриваме линка към категорията по slug или по етикета.
            cat_url = None
            for a in home.find_all("a", href=True):
                href, text = a["href"].lower(), a.get_text(strip=True).lower()
                if slug.replace("-", "") in href.replace("-", "") or label.lower() in text:
                    cat_url = self.abs_url(a["href"])
                    break
            if cat_url is None:
                self.log.warning("Не открих категория '%s' на началната страница", label)
                continue
            self._scrape_category(cat_url, label)

    def _scrape_category(self, url: str, label: str, max_pages: int = 30) -> None:
        seen_pages = set()
        queue = [url]
        while queue and len(seen_pages) < max_pages:
            page_url = queue.pop(0)
            if page_url in seen_pages:
                continue
            seen_pages.add(page_url)
            soup = self.soup(page_url)
            if soup is None:
                continue
            # Всеки елемент от каталога съдържа телефон — намираме блоковете.
            for item in soup.find_all(["li", "div", "article", "tr"]):
                text = item.get_text(" ", strip=True)
                if len(text) > 600 or len(text) < 15:
                    continue
                phones = extract_phones(text)
                if not phones:
                    continue
                heading = item.find(["h2", "h3", "h4", "a", "strong", "b"])
                ime = heading.get_text(strip=True) if heading else text[:60]
                emails = extract_emails(text)
                if any(r["ime"] == ime and r["telefon"] == phones[0]
                       for r in self.records[-50:]):
                    continue  # вложени блокове дублират съдържание
                self.add_record(
                    ime=ime, podkategoria=label,
                    telefon=phones[0], email=emails[0] if emails else "",
                    iztochnik=page_url,
                )
            # Пагинация.
            for a in soup.find_all("a", href=True):
                t = a.get_text(strip=True).lower()
                if t in (">", "следваща", "напред", "next") or t.isdigit():
                    nxt = self.abs_url(a["href"], page_url)
                    if nxt not in seen_pages:
                        queue.append(nxt)
            self.save_checkpoint()
