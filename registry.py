"""Динамично откриване на скрейпърите, разпределени по подпапки за всеки сайт.

Общата логика (base.py, config.py, exporter.py) стои в корена, а всеки
сайт-специфичен скрейпър е в собствена подпапка, кръстена на домейна
(напр. namrb.org/namrb.py). Тук сканираме тези подпапки, зареждаме всеки
модул по път до файла (importlib) и го регистрираме по неговото поле .name.
"""
import importlib.util
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Папки, които не съдържат скрейпъри.
_SKIP_DIRS = {"tests", "data", "output", "logs", "__pycache__", ".git", ".github"}


def _load_scrapers() -> dict:
    from base import BaseScraper

    scrapers: dict[str, type] = {}
    for py in sorted(BASE_DIR.glob("*/*.py")):
        if py.parent.name in _SKIP_DIRS or py.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(py.stem, py)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:  # noqa: BLE001 — счупен модул не спира останалите
            print(f"[registry] Пропускам {py}: {e}", file=sys.stderr)
            continue
        for obj in vars(module).values():
            if (isinstance(obj, type) and issubclass(obj, BaseScraper)
                    and obj is not BaseScraper and getattr(obj, "name", "")):
                scrapers[obj.name] = obj
    return scrapers


SCRAPERS = _load_scrapers()
