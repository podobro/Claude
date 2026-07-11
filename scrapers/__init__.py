"""Регистър на всички скрейпъри."""
from scrapers.bfs_clubs import BfsClubsScraper
from scrapers.business_bg import BusinessBgScraper
from scrapers.eop import EopScraper
from scrapers.fair_plovdiv import FairPlovdivScraper
from scrapers.iec_events import IecEventsScraper
from scrapers.iisda import IisdaScraper
from scrapers.mfa_embassies import MfaEmbassiesScraper
from scrapers.mms_sport_clubs import MmsSportClubsScraper
from scrapers.mon_schools import MonSchoolsScraper
from scrapers.namrb import NamrbScraper
from scrapers.ntr_hotels import NtrHotelsScraper
from scrapers.patriarshia import PatriarshiaScraper
from scrapers.zlatni_stranici import ZlatniStraniciScraper

SCRAPERS = {cls.name: cls for cls in (
    NamrbScraper, MfaEmbassiesScraper, MonSchoolsScraper, NtrHotelsScraper,
    IisdaScraper, EopScraper, BusinessBgScraper, ZlatniStraniciScraper,
    BfsClubsScraper, MmsSportClubsScraper, IecEventsScraper,
    FairPlovdivScraper, PatriarshiaScraper,
)}
