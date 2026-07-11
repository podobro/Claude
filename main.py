"""CLI за системата за извличане на контакти.

Примери:
    python main.py --all
    python main.py --source namrb
    python main.py --source business_bg --category hoteli
    python main.py --export-only
"""
import argparse
import logging
import sys

import config
from exporter import export_excel
from scrapers import SCRAPERS


def setup_logging() -> None:
    config.LOGS_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(config.LOGS_DIR / "main.log", encoding="utf-8"),
        ],
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Извличане на контакти на потенциални клиенти (знамена)")
    parser.add_argument("--all", action="store_true",
                        help="пусни всички скрейпъри в приоритетен ред")
    parser.add_argument("--source", choices=sorted(SCRAPERS),
                        help="пусни само един източник")
    parser.add_argument("--category",
                        help="филтър по категория (за business_bg/zlatni_stranici)")
    parser.add_argument("--export-only", action="store_true",
                        help="само генерирай Excel от наличните JSON-и в data/")
    args = parser.parse_args()

    setup_logging()
    log = logging.getLogger("main")

    if not (args.all or args.source or args.export_only):
        parser.print_help()
        return 1

    failed = []
    if args.all:
        for name in config.RUN_ORDER:
            scraper = SCRAPERS[name](category_filter=args.category)
            if not scraper.run():
                failed.append(name)
    elif args.source:
        scraper = SCRAPERS[args.source](category_filter=args.category)
        if not scraper.run():
            failed.append(args.source)

    # Excel се генерира винаги накрая (и при --export-only е единствената стъпка).
    df = export_excel()
    log.info("Готово: %d записа в %s", len(df), config.EXCEL_PATH)

    if failed:
        log.warning("Неуспешни източници: %s", ", ".join(failed))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
