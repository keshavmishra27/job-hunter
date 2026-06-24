from backend.modules.fetchers.base_fetcher import BaseFetcher, RawJob
from backend.modules.fetchers.apify_fetcher import (
    ApifyInternshalaFetcher,
    ApifyLinkedInFetcher,
    ApifyIndeedFetcher,
    ApifyWellfoundFetcher,
    ApifyNaukriFetcher,
)
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
                                   
    ArcJobsFetcher,
    HimalayasFetcher,
    OttaFetcher,
    TuringJobsFetcher,
    LandingJobsFetcher,
    PangianFetcher,
    PowerToFlyFetcher,
    AndelaFetcher,
    DeelCareersFetcher,
    TrueUpFetcher,
)
from backend.modules.fetchers.gmail_fetcher import GmailFetcher
from backend.modules.fetchers.duckduckgo_fetcher import DuckDuckGoFetcher

                    
from backend.modules.fetchers.upwork_fetcher import UpworkFetcher
from backend.modules.fetchers.freelance_fetchers import (
    FiverrFetcher,
    FreelancerComFetcher,
    GuruFetcher,
    ToptalFetcher,
    ContraFetcher,
    PeoplePerHourFetcher,
    ArcFetcher,
    TuringFetcher,
    LemonioFetcher,
    GunioFetcher,
    NinetyNineDesignsFetcher,
    DribbbleFetcher,
    BehanceFetcher,
)

__all__ = [
    "BaseFetcher", "RawJob",
                                     
    "ApifyInternshalaFetcher", "ApifyLinkedInFetcher", "ApifyIndeedFetcher",
    "ApifyWellfoundFetcher", "ApifyNaukriFetcher",
    "InternshalaFetcher", "IndeedFetcher", "CompanyCareerFetcher", "GovtPortalFetcher",
    "LinkedInFetcher", "FounditFetcher", "FreshersworldFetcher", "CutshortFetcher",
    "WellfoundFetcher", "WorkAtAStartupFetcher", "TelegramChannelFetcher",
    "GmailFetcher", "DuckDuckGoFetcher",
                                   
    "ArcJobsFetcher", "HimalayasFetcher", "OttaFetcher", "TuringJobsFetcher",
    "LandingJobsFetcher", "PangianFetcher", "PowerToFlyFetcher",
    "AndelaFetcher", "DeelCareersFetcher", "TrueUpFetcher",
                        
    "UpworkFetcher", "FiverrFetcher", "FreelancerComFetcher",
    "GuruFetcher", "ToptalFetcher", "ContraFetcher",
    "PeoplePerHourFetcher", "ArcFetcher", "TuringFetcher",
    "LemonioFetcher", "GunioFetcher", "NinetyNineDesignsFetcher",
    "DribbbleFetcher", "BehanceFetcher",
]


