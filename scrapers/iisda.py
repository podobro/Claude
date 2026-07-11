"""Административен регистър (iisda.government.bg) — държавни институции.

Регистърът е сървърно рендиран; контактните данни на всяка структура се
зареждат през xajax POST (`getAjaxInfo`) на страницата на организационната
ѝ схема — извикваме го директно, без браузър.
"""
import re

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, extract_emails, extract_phones

BASE = "https://iisda.government.bg"
CATEGORIES = [
    "administration_council_of_ministers",
    "ministries",
    "state_agencies",
    "state_commissions",
    "executive_agencies",
    "adm_stuctures_with_law",       # правописът е такъв в сайта
    "adm_structures_with_decree",
    "adm_structures_parliament",
    "state_public_commissions",
    "special_terr_administrations",
    "district_administrations",
    "municipality_administrations",
    "area_administrations",
]
# Общинските/районните администрации отиват при общините.
MUNICIPAL_CATEGORIES = {"municipality_administrations", "area_administrations"}

ORG_LINK_RE = re.compile(r'/ras/adm_structures/\w*organigram\w*/(\d+)$')
CDATA_RE = re.compile(r"<!\[CDATA\[S?(.*)\]\]>", re.S)


class IisdaScraper(BaseScraper):
    name = "iisda"

    def _collect_category(self, cat: str) -> dict[str, str]:
        """Връща {url на organigram: име на структурата} за една категория.

        Списъците показват по 30 елемента: при наличие на филтър по област
        обхождаме областите (search=1&districtId=N), иначе ползваме xajax
        пагинацията getItemList(page, 30).
        """
        cat_url = f"{BASE}/ras/adm_structures/{cat}"
        links: dict[str, str] = {}

        def harvest(soup) -> int:
            new = 0
            for a in soup.find_all("a", href=True):
                if ORG_LINK_RE.search(a["href"]):
                    url = self.abs_url(a["href"], BASE)
                    if url not in links:
                        links[url] = a.get_text(strip=True)
                        new += 1
            return new

        first = self.soup(cat_url)
        if first is None:
            return links
        harvest(first)

        district_sel = first.find("select", {"name": "districtId"})
        if district_sel is not None:
            for opt in district_sel.find_all("option"):
                val = opt.get("value")
                if not val or val == "0":
                    continue
                page = self.soup(f"{cat_url}?search=1&districtId={val}")
                if page is not None:
                    harvest(page)
            return links

        total_el = first.find(id="totalCount")
        total = int(total_el.get_text(strip=True)) if total_el else len(links)
        page = 0
        while len(links) < total and page <= total // 30 + 2:
            self._rate_limit(cat_url)
            resp = self.client.post(
                cat_url,
                content=f"xjxfun=getItemList&xjxargs[]={page}&xjxargs[]=30",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            page += 1
            if resp.status_code != 200:
                self.errors += 1
                break
            self.pages_visited += 1
            if harvest(BeautifulSoup(resp.text, "lxml")) == 0 and page > 1:
                break
        return links

    def _fetch_info(self, url: str) -> BeautifulSoup | None:
        """Директно xajax извикване за контактните данни на структура."""
        struct_id = url.rstrip("/").rsplit("/", 1)[-1]
        self._rate_limit(url)
        resp = self.client.post(
            url, data={"xjxfun": "getAjaxInfo", "xjxargs[]": f"batchInfo-{struct_id}"})
        if resp.status_code != 200:
            self.errors += 1
            return None
        self.pages_visited += 1
        m = CDATA_RE.search(resp.text)
        if not m:
            return None
        return BeautifulSoup(m.group(1), "lxml")

    def scrape(self) -> None:
        state = self.load_checkpoint()
        done = set(state.get("done_urls", []))

        for cat in CATEGORIES:
            links = self._collect_category(cat)
            self.log.info("Категория %s: %d структури", cat, len(links))
            kategoria = "Общини" if cat in MUNICIPAL_CATEGORIES else ""
            for url, ime in links.items():
                if url in done:
                    continue
                info = self._fetch_info(url)
                done.add(url)
                if info is None:
                    continue
                sections: dict[str, str] = {}
                for sec in info.find_all("div", class_="organigram-section"):
                    h2 = sec.find("h2")
                    if h2:
                        sections[h2.get_text(strip=True).lower()] = sec.get_text(" ", strip=True)
                addr_txt = sections.get("седалище и адрес", "")
                corr_txt = sections.get("данни за кореспонденция", "")
                grad = ""
                if m := re.search(r"Населено място:\s*([^|]+?)(?:Адрес|Пощенски|$)", addr_txt):
                    grad = m.group(1).strip()
                adres = ""
                if m := re.search(r"Адрес:\s*(.+?)(?:Пощенски код:|$)", addr_txt):
                    adres = m.group(1).strip()
                if m := re.search(r"Пощенски код:\s*(\d+)", addr_txt):
                    adres = f"{adres}, {m.group(1)}" if adres else m.group(1)
                site = ""
                if m := re.search(r"Уеб сайт:\s*(\S+)", corr_txt):
                    site = m.group(1).strip()
                    if site and not site.startswith("http"):
                        site = "https://" + site
                emails = extract_emails(corr_txt)
                phones = _phones_with_area_code(corr_txt)
                self.add_record(
                    ime=ime,
                    grad=grad.replace("гр.", "").replace("с.", "").strip(),
                    adres=adres,
                    telefon=phones[0] if phones else "",
                    email=emails[0] if emails else "",
                    uebsait=site,
                    podkategoria=cat_label(cat),
                    kategoria=kategoria,
                    iztochnik=url,
                )
                if len(done) % 25 == 0:
                    self.save_checkpoint({"done_urls": sorted(done)})
            self.save_checkpoint({"done_urls": sorted(done)})


CAT_LABELS = {
    "administration_council_of_ministers": "Администрация на МС",
    "ministries": "Министерство",
    "state_agencies": "Държавна агенция",
    "state_commissions": "Държавна комисия",
    "executive_agencies": "Изпълнителна агенция",
    "adm_stuctures_with_law": "Структура, създадена със закон",
    "adm_structures_with_decree": "Структура, създадена с ПМС",
    "adm_structures_parliament": "Структура към НС",
    "state_public_commissions": "Държавно-обществена комисия",
    "special_terr_administrations": "Специализирана терит. администрация",
    "district_administrations": "Областна администрация",
    "municipality_administrations": "Общинска администрация",
    "area_administrations": "Районна администрация",
}


def cat_label(cat: str) -> str:
    return CAT_LABELS.get(cat, cat)


def _phones_with_area_code(corr_txt: str) -> list[str]:
    """Телефони от секцията „Данни за кореспонденция".

    Кодът за междуселищно избиране често е отделен от номерата
    (напр. „Kод: (02) … Телефон: 9482999"), затова го долепваме,
    когато номерът не започва с 0.
    """
    from scrapers.base import normalize_phone
    kod = ""
    if m := re.search(r"избиране:\s*\((\d+)\)", corr_txt):
        kod = m.group(1)
    m = re.search(r"Телефони?:\s*(.+?)(?:Факс|Численост|$)", corr_txt)
    if not m:
        return extract_phones(corr_txt)
    result = []
    for part in re.split(r"[;,]", m.group(1)):
        digits = re.sub(r"[^\d]", "", part)
        if len(digits) < 5:
            continue
        if not digits.startswith("0") and kod:
            digits = kod + digits
        if phone := normalize_phone(digits):
            if phone not in result:
                result.append(phone)
    return result
