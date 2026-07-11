"""Базов клас за всички скрейпъри: rate limiting, retry, robots.txt,
checkpoint-и, logging и общ интерфейс + помощни функции за контакти."""
import json
import logging
import re
import sys
import time
import urllib.robotparser
from datetime import date
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

import config

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+|00)?[\d(][\d\s\-()/.]{6,18}\d")

# Лични имейл префикси, които пропускаме — събираме само служебни контакти.
PERSONAL_EMAIL_HINTS = ("gmail.", "abv.bg", "yahoo.", "mail.bg", "hotmail.")
OFFICE_EMAIL_HINTS = ("office", "info", "admin", "contact", "kmet", "obshtina",
                      "priemna", "delovodstvo", "mail", "reception", "sales")


class ScrapeBlocked(Exception):
    """403/429 — сайтът ни блокира; спираме и логваме, без да заобикаляме."""


class RetryableHTTPError(Exception):
    """5xx или timeout — подлежи на retry с exponential backoff."""


def validate_email(email: str) -> str | None:
    """Валидира имейл през regex; връща нормализиран (lowercase) или None."""
    if not email:
        return None
    email = email.strip().strip(".,;:")
    m = EMAIL_RE.fullmatch(email)
    return m.group(0).lower() if m else None


def normalize_phone(raw: str) -> str | None:
    """Нормализира телефон към +359... (само за български номера).

    Чужди номера (напр. посолства зад граница) се запазват с техния
    международен префикс. Връща None при невалиден/твърде кратък номер.
    """
    if not raw:
        return None
    s = re.sub(r"[^\d+]", "", raw)
    if s.startswith("00"):
        s = "+" + s[2:]
    if s.startswith("359"):
        s = "+" + s
    if s.startswith("0") and 9 <= len(s) <= 10:
        s = "+359" + s[1:]
    digits = s.lstrip("+")
    if not digits.isdigit() or not 8 <= len(digits) <= 15:
        return None
    if not s.startswith("+"):
        # Номер без национален префикс — приемаме, че е български.
        s = "+359" + s if len(s) <= 8 else "+" + s
    return s


def extract_emails(text: str) -> list[str]:
    """Всички валидни служебни имейли от текст (без явно лични кутии)."""
    found = []
    for m in EMAIL_RE.finditer(text or ""):
        email = m.group(0).lower()
        local, _, domain = email.partition("@")
        is_free_mail = any(h in domain for h in PERSONAL_EMAIL_HINTS)
        looks_official = any(h in local for h in OFFICE_EMAIL_HINTS)
        # При безплатни пощи вземаме само явно служебни кутии (office@, info@…).
        if is_free_mail and not looks_official:
            continue
        if email not in found:
            found.append(email)
    return found


def extract_phones(text: str) -> list[str]:
    """Всички нормализирани телефони от текст."""
    found = []
    for m in PHONE_RE.finditer(text or ""):
        phone = normalize_phone(m.group(0))
        # Отхвърляме „телефони“, които са всъщност дати/числа: искаме
        # реалистична дължина за стационарен/мобилен номер.
        if phone and phone not in found and len(phone.lstrip("+")) >= 9:
            found.append(phone)
    return found


class BaseScraper:
    """Общ интерфейс: наследниците имплементират scrape()."""

    name: str = ""            # ключ от config.SOURCES
    kategoria: str = ""

    def __init__(self, category_filter: str | None = None):
        src = config.SOURCES[self.name]
        self.base_url = src["url"]
        self.kategoria = self.kategoria or src["kategoria"]
        self.category_filter = category_filter
        self.records: list[dict] = []
        self.pages_visited = 0
        self.errors = 0
        self._last_request: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self.log = self._setup_logger()
        self.client = httpx.Client(
            headers={"User-Agent": config.USER_AGENT},
            timeout=config.REQUEST_TIMEOUT,
            follow_redirects=True,
            verify=not getattr(config, "INSECURE_TLS", False),
        )

    # ------------------------------------------------------------------ util
    def _setup_logger(self) -> logging.Logger:
        config.LOGS_DIR.mkdir(exist_ok=True)
        log = logging.getLogger(f"scraper.{self.name}")
        log.setLevel(logging.INFO)
        log.propagate = False  # има си собствени handler-и — без дублиране в root
        if not log.handlers:
            fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
            fh = logging.FileHandler(config.LOGS_DIR / f"{self.name}.log", encoding="utf-8")
            sh = logging.StreamHandler(sys.stdout)
            fh.setFormatter(fmt)
            sh.setFormatter(fmt)
            log.addHandler(fh)
            log.addHandler(sh)
        return log

    def _robots_allowed(self, url: str) -> bool:
        """Проверява robots.txt за домейна; при недостъпен robots — allow."""
        domain = urlparse(url).netloc
        if domain not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            robots_url = f"{urlparse(url).scheme}://{domain}/robots.txt"
            try:
                resp = self.client.get(robots_url)
                if resp.status_code == 200:
                    rp.parse(resp.text.splitlines())
                    self._robots[domain] = rp
                else:
                    self._robots[domain] = None
            except httpx.HTTPError:
                self._robots[domain] = None
        rp = self._robots[domain]
        if rp is None:
            return True
        allowed = rp.can_fetch(config.USER_AGENT, url)
        if not allowed:
            self.log.warning("robots.txt забранява достъп до %s — пропускам", url)
        return allowed

    def _rate_limit(self, url: str) -> None:
        domain = urlparse(url).netloc
        last = self._last_request.get(domain, 0.0)
        wait = config.RATE_LIMIT_SECONDS - (time.monotonic() - last)
        if wait > 0:
            time.sleep(wait)
        self._last_request[domain] = time.monotonic()

    @retry(
        retry=retry_if_exception_type(RetryableHTTPError),
        stop=stop_after_attempt(config.MAX_RETRIES),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        reraise=True,
    )
    def fetch(self, url: str) -> str | None:
        """GET с rate limit, robots проверка и retry при 5xx/timeout.

        При 403/429 вдига ScrapeBlocked — не заобикаляме защити.
        """
        if not self._robots_allowed(url):
            return None
        self._rate_limit(url)
        try:
            resp = self.client.get(url)
        except (httpx.TimeoutException, httpx.TransportError) as e:
            self.errors += 1
            raise RetryableHTTPError(f"{type(e).__name__}: {e}") from e
        if resp.status_code in (403, 429):
            raise ScrapeBlocked(f"HTTP {resp.status_code} за {url}")
        if resp.status_code >= 500:
            self.errors += 1
            raise RetryableHTTPError(f"HTTP {resp.status_code} за {url}")
        if resp.status_code != 200:
            self.log.warning("HTTP %s за %s", resp.status_code, url)
            self.errors += 1
            return None
        self.pages_visited += 1
        return resp.text

    def soup(self, url: str) -> BeautifulSoup | None:
        html = self.fetch(url)
        return BeautifulSoup(html, "lxml") if html else None

    def abs_url(self, href: str, base: str | None = None) -> str:
        return urljoin(base or self.base_url, href)

    # --------------------------------------------------------------- records
    def add_record(self, *, ime: str, grad: str = "", adres: str = "",
                   telefon: str = "", email: str = "", uebsait: str = "",
                   podkategoria: str = "", dopalnitelno: str = "",
                   iztochnik: str = "") -> None:
        ime = re.sub(r"\s+", " ", (ime or "")).strip()
        if not ime:
            return
        self.records.append({
            "kategoria": self.kategoria,
            "podkategoria": podkategoria,
            "ime": ime,
            "grad": re.sub(r"\s+", " ", grad or "").strip(),
            "adres": re.sub(r"\s+", " ", adres or "").strip(),
            "telefon": normalize_phone(telefon) or "",
            "email": validate_email(email) or "",
            "uebsait": (uebsait or "").strip(),
            "dopalnitelno": (dopalnitelno or "").strip(),
            "iztochnik": iztochnik or self.base_url,
            "data_izvlichane": date.today().isoformat(),
        })

    def add_from_page_text(self, ime: str, text: str, url: str, **kw) -> None:
        """Удобен метод: извлича първия имейл/телефон от текста на страница."""
        emails = extract_emails(text)
        phones = extract_phones(text)
        self.add_record(
            ime=ime,
            telefon=phones[0] if phones else "",
            email=emails[0] if emails else "",
            iztochnik=url,
            **kw,
        )

    # ----------------------------------------------------------- checkpoints
    @property
    def checkpoint_path(self):
        return config.DATA_DIR / f"{self.name}.json"

    def save_checkpoint(self, extra_state: dict | None = None) -> None:
        config.DATA_DIR.mkdir(exist_ok=True)
        payload = {"records": self.records, "state": extra_state or {}}
        self.checkpoint_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
        )

    def load_checkpoint(self) -> dict:
        if self.checkpoint_path.exists():
            payload = json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
            self.records = payload.get("records", [])
            return payload.get("state", {})
        return {}

    # -------------------------------------------------------------- lifecycle
    def scrape(self) -> None:  # pragma: no cover — имплементира се от наследника
        raise NotImplementedError

    def run(self) -> bool:
        """Пуска скрейпъра с обработка на грешки; връща успех/неуспех."""
        self.log.info("Старт: %s (%s)", self.name, self.base_url)
        ok = True
        try:
            self.scrape()
        except ScrapeBlocked as e:
            self.log.error("БЛОКИРАН (403/429), спирам без заобикаляне: %s", e)
            ok = False
        except RetryableHTTPError as e:
            self.log.error("Мрежова грешка след %s опита: %s", config.MAX_RETRIES, e)
            ok = False
        except Exception as e:  # noqa: BLE001 — един счупен сайт не спира --all
            self.log.exception("Неочаквана грешка: %s", e)
            ok = False
        finally:
            self.save_checkpoint()
            self.client.close()
            with_email = sum(1 for r in self.records if r["email"])
            with_phone = sum(1 for r in self.records if r["telefon"])
            self.log.info(
                "Финал: %d обходени страници, %d записа (%d с имейл, %d с телефон), %d грешки",
                self.pages_visited, len(self.records), with_email, with_phone, self.errors,
            )
        return ok
