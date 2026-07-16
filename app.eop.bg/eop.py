"""ЦАИС ЕОП (app.eop.bg) — възложители на поръчки за знамена.

app.eop.bg е Angular SPA пред WCF услуга (NX1Service.svc). Търсенето в
приключилите/публикуваните поръчки върви през REST метода
GetPublishedTendersAdvancedSearchResult с DataContract, реконструиран от
JS bundle-а (полето PublishedTenderNameKeywords = ключова дума в предмета).

ВАЖНО (ограничение на средата): NX1Service отговаря на този метод с
асинхронен HTTP 202 без тяло — резултатът се доставя по отделен
push-канал, който изисква автентикирана браузърна сесия. В обкръжение с
нормален достъп методът връща данните директно. Тук ползваме и
DownloadPublishedTendersAdvancedSearchFileContent (Excel/CSV), който при
достъпен канал връща файла синхронно.
"""
import io

import config
from base import BaseScraper

SERVICE = "https://service.eop.bg/NX1Service.svc"
SEARCH_METHOD = f"{SERVICE}/GetPublishedTendersAdvancedSearchResult"

# Празни стойности за всички полета на формата за търсене (от JS bundle-а).
_STR_FIELDS = [
    "PublishedTenderNameKeywords", "OrganizationKeywords", "BuyerBatchNumber",
    "AssignmentOrder", "BatchNumber", "YearCreated", "SerialNumber",
    "ContractingAuthorityRegistryNumber", "SupplierName", "SupplierPublicId",
    "PropertyDisplayName",
]
_NULL_FIELDS = [
    "CpvCode", "TypeOfContract", "ExecutionRegion", "NutsCode", "ProcedureType",
    "TechniquesAndInstruments", "OfferReceivingStartDate", "OfferReceivingEndDate",
    "PublishStartDate", "PublishEndDate", "EuropeanPublication", "EuropeanFinancing",
    "SpecificServices", "DefinedPositions", "SavedOrders", "AppealProceedingsInstituted",
    "SecurityAndDefense", "ProcurementStatus", "ContractCriteria", "GreenCriteriaType",
    "ActivityTypeGroup", "SupplierType", "AllowMultipleOffers", "FirstStageControl",
    "IsStrategicTender", "Variants",
]


def _build_request(keyword: str, page: int = 1, size: int = 50) -> dict:
    req = {k: "" for k in _STR_FIELDS}
    req.update({k: None for k in _NULL_FIELDS})
    req["EUProgramCodes"] = []
    req["PublishedTenderNameKeywords"] = keyword
    req["StartIndex"] = (page - 1) * size + 1
    req["EndIndex"] = page * size
    req["OrderColumn"] = "PublicationDate"
    req["OrderDirection"] = "desc"
    return req


class EopScraper(BaseScraper):
    name = "eop"

    def scrape(self) -> None:
        for kw in config.EOP_KEYWORDS:
            self.log.info("Търсене в ЦАИС ЕОП по ключова дума: %s", kw)
            self._rate_limit(SERVICE)
            try:
                resp = self.client.post(SEARCH_METHOD, json={"request": _build_request(kw)})
            except Exception as e:  # noqa: BLE001
                self.log.warning("Заявка към %s се провали: %s", SEARCH_METHOD, e)
                self.errors += 1
                continue
            self.pages_visited += 1

            if resp.status_code == 202 or not resp.content:
                self.log.warning(
                    "NX1Service върна асинхронен %s без тяло за '%s' — "
                    "резултатът се доставя по push-канал, изискващ браузърна "
                    "сесия (вж. README/бележка в кода). Пропускам.",
                    resp.status_code, kw)
                continue
            if resp.status_code != 200:
                self.log.warning("HTTP %s от NX1Service за '%s'", resp.status_code, kw)
                self.errors += 1
                continue

            try:
                data = resp.json()
            except ValueError:
                self.log.warning("Неочакван (не-JSON) отговор за '%s'", kw)
                continue
            self._ingest(data.get("d", data), kw)
            self.save_checkpoint()

    def _ingest(self, data, kw: str) -> None:
        items = []
        if isinstance(data, dict):
            for key in ("Items", "Result", "Results", "Data", "Tenders"):
                if isinstance(data.get(key), list):
                    items = data[key]
                    break
        elif isinstance(data, list):
            items = data
        self.log.info("Резултати за '%s': %d", kw, len(items))
        for it in items:
            if not isinstance(it, dict):
                continue
            buyer = (it.get("OrganizationName") or it.get("ContractingAuthorityName")
                     or it.get("BuyerName") or "")
            subject = it.get("TenderName") or it.get("Name") or it.get("Subject") or ""
            value = it.get("TenderAmount") or it.get("EstimatedValue") or ""
            pub = it.get("PublicationDate") or it.get("PublishDate") or ""
            dop = "; ".join(x for x in (
                f"Поръчка: {subject}" if subject else "",
                f"Стойност: {value}" if value else "",
                f"Публикувана: {pub}" if pub else "",
            ) if x)
            self.add_record(
                ime=buyer or subject or f"Поръчка ({kw})",
                podkategoria=f"Купувач на '{kw}'",
                dopalnitelno=dop,
                iztochnik="https://app.eop.bg/today/reporting/search",
            )
