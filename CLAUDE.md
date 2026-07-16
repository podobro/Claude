# CLAUDE.md — контекст за нова сесия

Този файл се зарежда автоматично от Claude Code при старт в тази папка и
дава пълен контекст за проекта без нужда потребителят да обяснява отначало.

## Какво е проектът

Система за B2B lead generation за фирма за знамена/флагове — обхожда 13
публични български държавни/бизнес сайта, извлича служебни контакти
(имейл + телефон) на организации и ги консолидира в един Excel файл
(`output/kontakti_znamena.xlsx`) с листове по категория.

Пълна документация: виж `README.md` (структура, статус на всеки
скрейпър, технически детайли, GDPR бележки).

## Архитектура (накратко)

- `base.py` — `BaseScraper`: rate limiting, retry/backoff, robots.txt
  проверка, checkpoint save/load, helper функции `extract_emails`,
  `extract_phones`, `normalize_phone`, `validate_email`.
- `config.py` — URL-и, лимити, `RATE_LIMIT_OVERRIDES` по сайт, категории.
- `exporter.py` — дедупликация (по имейл И по нормализиран телефон),
  валидация, генериране на Excel (freeze panes, autofilter, автоширина,
  лист "Статистика").
- `registry.py` — динамично сканира `*/*.py` подпапките, зарежда всеки
  модул по път (importlib) и регистрира класовете, наследяващи
  `BaseScraper`, по тяхното поле `.name`. **Папките могат да се
  преименуват свободно** — регистърът не разчита на hardcoded imports.
- `main.py` — CLI: `--all`, `--source <name>`, `--category`,
  `--export-only`.
- Всеки сайт си има собствена подпапка, кръстена на домейна
  (`namrb.org/namrb.py`, `business.bg/business_bg.py`, ...), съдържаща
  точно един скрейпър файл.

## Текущ статус на скрейпърите (13 общо)

✅ Работят напълно (7): `namrb`, `ntr_hotels`, `iisda`, `business_bg`,
`fair_plovdiv`, `iec_events`, `patriarshia` — общо ≈36 460 записа след
дедупликация.

⚠️ Частично / блокирани от средата, но кодът е готов (2):
- `mfa_embassies` — Radware/perfdrive bot защита след 2-3 заявки.
- `eop` (ЦАИС ЕОП) — REST DataContract е реконструиран правилно, но
  NX1Service връща async `202` без тяло; трябва браузърна сесия.

⛔ Недостъпни от облачната среда, но може да проработят от локална
мрежа/IP (4):
- `mon_schools` (web.mon.bg) — Cloudflare "Just a moment" 403.
- `zlatni_stranici` (zlatnistranici.bg) — proxy 502, домейнът вероятно
  не е в allowlist-а на облачната среда.
- `bfs_clubs` (bfunion.bg) — HTTP 403 bot защита.
- `mms_sport_clubs` (mmsbg.info) — proxy 502.

## Защо преминаваме към локална сесия

Облачната среда (тази, в която е писан кодът досега) има ограничения,
които пречат на горните 6 източника:
- Playwright/Chromium не може да мине през proxy-то на средата
  (`ERR_PROXY_CONNECTION_FAILED`) → EOP не може да отвори браузърна
  сесия за push-канала.
- Някои домейни връщат proxy 502 (изглежда не са в мрежовия allowlist).
- Bot защитите (Cloudflare, Radware) може да реагират различно на
  реален потребителски IP срещу облачен datacenter IP.

**Цел на локалната сесия**: пусни `python main.py --all` от реална
мрежа/IP и виж дали горните 6 източника вече дават резултати. Ако да —
довърши/шлайфай съответните скрейпъри с реалните HTML/API отговори.

## Правила, които НЕ се заобикалят (важно за всяка нова сесия)

- Не се заобикаля CAPTCHA, login форми, bot защита (Cloudflare,
  Radware) — при 403/429 скрейпърът трябва да спре и да логне, не да
  опитва да имитира браузър агресивно.
- Rate limiting се спазва навсякъде (`config.RATE_LIMIT_SECONDS`,
  `RATE_LIMIT_OVERRIDES`).
- robots.txt се проверява за всеки домейн.
- Събират се само служебни контакти (info@, office@ и др.), не лични
  имейли на физически лица — филтърът е в `base.py`.

## Как да продължиш работата тук

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium     # само ако EOP push-канала все пак трябва браузър
python main.py --all            # пусни всички източници
python tests/test_pipeline.py   # тестове (дедуп, валидация, Excel)
```

При проблем с конкретен източник — виж `logs/<източник>.log` и
съответния файл в `<домейн>/<име>.py`. Checkpoint-ите в `data/*.json`
позволяват resume след прекъсване; `python main.py --export-only`
регенерира само Excel-а от наличните checkpoint-и.

## Git

Разработен клон: `claude/test-website-scripts-mjrf96` (от `main`/default
branch на `podobro/Claude`). Последен commit при преминаването към
локална сесия: реорганизация с подпапка за всеки сайт (виж `git log`).
