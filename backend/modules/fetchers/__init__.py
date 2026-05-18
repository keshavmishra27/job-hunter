from backend.modules.fetchers.base_fetcher import BaseFetcher, RawJob
from backend.modules.fetchers.internshala_fetcher import InternshalaFetcher
from backend.modules.fetchers.indeed_fetcher import IndeedFetcher
from backend.modules.fetchers.company_career_fetcher import CompanyCareerFetcher
from backend.modules.fetchers.govt_portal_fetcher import GovtPortalFetcher
from backend.modules.fetchers.extended_fetchers import (
    LinkedInFetcher,
    FounditFetcher,
    FreshersworldFetcher,
    CutshortFetcher,
    WellfoundFetcher,
    WorkAtAStartupFetcher,
    TelegramChannelFetcher,
)
__all__ = [
    "BaseFetcher", "RawJob",
    "InternshalaFetcher", "IndeedFetcher", "CompanyCareerFetcher", "GovtPortalFetcher",
    "LinkedInFetcher", "FounditFetcher", "FreshersworldFetcher", "CutshortFetcher",
    "WellfoundFetcher", "WorkAtAStartupFetcher", "TelegramChannelFetcher",
]
