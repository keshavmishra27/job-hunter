from backend.modules.fetchers.base_fetcher import BaseFetcher, RawJob
from backend.modules.fetchers.internshala_fetcher import InternshalaFetcher
from backend.modules.fetchers.indeed_fetcher import IndeedFetcher
__all__ = [                                                                     
    "BaseFetcher", "RawJob",
    "InternshalaFetcher", "IndeedFetcher", "LinkedInFetcher",
    "GitHubFetcher", "YCFetcher", "CutshortFetcher", "WellfoundFetcher",
]
