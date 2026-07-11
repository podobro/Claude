"""Административен регистър (iisda.government.bg) — държавни институции.

Сайтът е с JS рендиране — използваме Playwright за списъка на
администрациите и извличаме адрес/телефон/имейл от детайлните страници.
"""
from scrapers.base import BaseScraper, extract_emails, extract_phones

LIST_URL = "https://iisda.government.bg/adm_register/adm_structures"


class IisdaScraper(BaseScraper):
    name = "iisda"

    def scrape(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.log.error("playwright не е инсталиран — пропускам")
            return

        state = self.load_checkpoint()
        done = set(state.get("done_urls", []))

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(LIST_URL, wait_until="networkidle", timeout=60000)
            self.pages_visited += 1

            detail_urls: list[str] = []
            while True:
                for a in page.locator("a[href*='adm_register']").all():
                    href = a.get_attribute("href") or ""
                    url = self.abs_url(href)
                    if "/adm_structures/" in url and url not in detail_urls:
                        detail_urls.append(url)
                nxt = page.locator("a[rel='next'], .pagination a:has-text('Следваща')")
                if nxt.count() == 0:
                    break
                nxt.first.click()
                page.wait_for_load_state("networkidle")
                self.pages_visited += 1
                if self.pages_visited > 200:  # предпазен лимит
                    break

            self.log.info("Открити %d администрации", len(detail_urls))
            for url in detail_urls:
                if url in done:
                    continue
                page.goto(url, wait_until="networkidle", timeout=60000)
                self.pages_visited += 1
                text = page.inner_text("body")
                h1 = page.locator("h1, h2").first
                ime = h1.inner_text().strip() if h1.count() else ""
                if not ime:
                    continue
                emails = extract_emails(text)
                phones = extract_phones(text)
                self.add_record(
                    ime=ime,
                    telefon=phones[0] if phones else "",
                    email=emails[0] if emails else "",
                    podkategoria="Администрация",
                    iztochnik=url,
                )
                done.add(url)
                if len(done) % 20 == 0:
                    self.save_checkpoint({"done_urls": sorted(done)})
            browser.close()

        self.save_checkpoint({"done_urls": sorted(done)})
