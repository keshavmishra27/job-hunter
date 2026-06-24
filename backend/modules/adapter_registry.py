"""
Adapter Registry — single lookup table mapping parser_type → fetcher class.

Replaces the separate FETCHERS dicts that were duplicated across
jobs.py, internships.py, and freelancing.py routers.

Usage:
    adapter_cls = get_adapter("internshala")
    fetcher = adapter_cls()
    raw_jobs = await fetcher.fetch(keywords, location)
"""
from __future__ import annotations

from typing import TYPE_CHECKING
from loguru import logger

if TYPE_CHECKING:
    from backend.modules.fetchers.base_fetcher import BaseFetcher

                                                                               
                                                                      


def _build_registry() -> dict[str, type]:
    """Build the complete adapter registry.  Called once on first access."""
    from backend.modules.fetchers import (
                                         
        ApifyInternshalaFetcher,
        ApifyIndeedFetcher,
        CompanyCareerFetcher,
        GovtPortalFetcher,
        TelegramChannelFetcher,
        GmailFetcher,
        ApifyLinkedInFetcher,
        FounditFetcher,
        FreshersworldFetcher,
        CutshortFetcher,
        ApifyWellfoundFetcher,
        ApifyNaukriFetcher,
        WorkAtAStartupFetcher,
                                        
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
                            
        UpworkFetcher,
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
        DuckDuckGoFetcher,
    )

    return {
                                                                          
        "internshala":       ApifyInternshalaFetcher,
        "indeed":            ApifyIndeedFetcher,
        "linkedin":          ApifyLinkedInFetcher,
        "naukri":            ApifyNaukriFetcher,
        "foundit":           FounditFetcher,
        "freshersworld":     FreshersworldFetcher,
        "cutshort":          CutshortFetcher,

                                                                          
        "wellfound":         ApifyWellfoundFetcher,
        "workatastartup":    WorkAtAStartupFetcher,
        "trueup":            TrueUpFetcher,

                                                                          
        "arcdev":            ArcJobsFetcher,
        "himalayas":         HimalayasFetcher,
        "otta":              OttaFetcher,
        "turing_jobs":       TuringJobsFetcher,
        "landingjobs":       LandingJobsFetcher,
        "pangian":           PangianFetcher,
        "powertofly":        PowerToFlyFetcher,
        "andela":            AndelaFetcher,
        "deel":              DeelCareersFetcher,

                                                                          
        "company_career":    CompanyCareerFetcher,
        "govt_portal":       GovtPortalFetcher,
        "telegram":          TelegramChannelFetcher,
        "gmail":             GmailFetcher,

                                                                          
        "upwork":            UpworkFetcher,
        "fiverr":            FiverrFetcher,
        "freelancer_com":    FreelancerComFetcher,
        "guru":              GuruFetcher,
        "toptal":            ToptalFetcher,
        "contra":            ContraFetcher,
        "peopleperhour":     PeoplePerHourFetcher,
        "arc":               ArcFetcher,
        "turing":            TuringFetcher,
        "lemonio":           LemonioFetcher,
        "gunio":             GunioFetcher,
        "ninetynine_designs": NinetyNineDesignsFetcher,
        "dribbble":          DribbbleFetcher,
        "behance":           BehanceFetcher,
        
                                                                          
        "duckduckgo":        DuckDuckGoFetcher,
    }


                                
_REGISTRY: dict[str, type] | None = None


def _get_registry() -> dict[str, type]:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_registry()
    return _REGISTRY


                                                                               

def get_adapter(parser_type: str) -> type | None:
    """Resolve a parser_type to its fetcher class.  Returns None if unknown."""
    return _get_registry().get(parser_type)


def get_adapter_or_raise(parser_type: str) -> type:
    """Resolve a parser_type to its fetcher class.  Raises KeyError if unknown."""
    cls = get_adapter(parser_type)
    if cls is None:
        raise KeyError(f"No adapter registered for parser_type: {parser_type}")
    return cls


def list_registered_adapters() -> list[str]:
    """Return all registered parser_type keys."""
    return sorted(_get_registry().keys())


def has_adapter(parser_type: str) -> bool:
    """Check if an adapter exists for a parser_type."""
    return parser_type in _get_registry()
