"""Централна конфигурация: URL-и, лимити, настройки."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"

EXCEL_PATH = OUTPUT_DIR / "kontakti_znamena.xlsx"

# Честна идентификация — не имитираме браузър при requests/httpx скрейпърите.
USER_AGENT = (
    "FlagLeadsBot/1.0 (+B2B contact research; respects robots.txt; "
    "contact: podobro@gmail.com)"
)

# Минимум секунди между заявки към един и същ домейн.
RATE_LIMIT_SECONDS = 2.0
REQUEST_TIMEOUT = 30.0
MAX_RETRIES = 3

# Ключови думи за търсене в ЦАИС ЕОП (приключили поръчки).
EOP_KEYWORDS = ["знамена", "знаме", "флагове"]

SOURCES = {
    "eop": {
        "url": "https://app.eop.bg",
        "kategoria": "Институции (доказани купувачи)",
        "js": True,
    },
    "iisda": {
        "url": "https://iisda.government.bg",
        "kategoria": "Държавни институции",
        "js": True,
    },
    "namrb": {
        "url": "https://www.namrb.org",
        "kategoria": "Общини",
        "js": False,
    },
    "mon_schools": {
        "url": "https://web.mon.bg/bg/100107",
        "kategoria": "Училища и детски градини",
        "js": False,
    },
    "mfa_embassies": {
        "url": "https://www.mfa.bg/bg/embassyinfo",
        "kategoria": "Посолства",
        "js": False,
    },
    "business_bg": {
        "url": "https://www.business.bg",
        "kategoria": "Бизнес клиенти",
        "js": False,
        # Категории за обхождане: ключова дума -> етикет за подкатегория
        "categories": {
            "hoteli": "Хотел",
            "benzinostancii": "Бензиностанция",
            "avtokashti": "Автокъща",
            "targovski-centrove": "Търговски център",
            "reklamni-agencii": "Рекламна агенция",
        },
    },
    "zlatni_stranici": {
        "url": "https://www.zlatnistranici.bg",
        "kategoria": "Бизнес клиенти",
        "js": False,
        "categories": {
            "хотели": "Хотел",
            "бензиностанции": "Бензиностанция",
            "автокъщи": "Автокъща",
            "търговски центрове": "Търговски център",
            "рекламни агенции": "Рекламна агенция",
        },
    },
    "ntr_hotels": {
        "url": "https://ntr.tourism.government.bg",
        "kategoria": "Хотели",
        "js": True,
    },
    "bfs_clubs": {
        "url": "https://bfunion.bg",
        "kategoria": "Спортни клубове",
        "js": False,
    },
    "mms_sport_clubs": {
        "url": "https://www.mmsbg.info",
        "kategoria": "Спортни клубове",
        "js": False,
    },
    "iec_events": {
        "url": "https://www.iec.bg",
        "kategoria": "Организатори на събития",
        "js": False,
    },
    "fair_plovdiv": {
        "url": "https://www.fair.bg",
        "kategoria": "Организатори на събития",
        "js": False,
    },
    "patriarshia": {
        "url": "https://bg-patriarshia.bg",
        "kategoria": "Църкви",
        "js": False,
    },
}

# Ред на изпълнение при --all (приоритет от заданието).
RUN_ORDER = [
    "namrb",
    "mfa_embassies",
    "mon_schools",
    "ntr_hotels",
    "iisda",
    "eop",
    "business_bg",
    "zlatni_stranici",
    "bfs_clubs",
    "mms_sport_clubs",
    "iec_events",
    "fair_plovdiv",
    "patriarshia",
]

# Имена на листовете в Excel по категория.
CATEGORY_SHEETS = {
    "Институции (доказани купувачи)": "Институции",
    "Държавни институции": "Институции",
    "Общини": "Общини",
    "Училища и детски градини": "Училища",
    "Посолства": "Посолства",
    "Бизнес клиенти": "Бизнес",
    "Хотели": "Хотели",
    "Спортни клубове": "Спортни клубове",
    "Организатори на събития": "Събития",
    "Църкви": "Църкви",
}
