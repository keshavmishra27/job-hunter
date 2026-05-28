import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from backend.modules.fetchers.indeed_fetcher import IndeedFetcher
from backend.modules.deduper import canonical_fingerprint


@pytest.fixture
def fetcher():
    return IndeedFetcher()


def test_applied_job_exclusion(fetcher):
    # Setup mock applied fingerprint
    job = {
        "title": "Software Engineer",
        "company": "Tech Corp",
        "location": "Remote",
        "apply_link": "https://in.indeed.com/viewjob?jk=123"
    }
    fp = canonical_fingerprint(job)
    applied_fps = {fp}
    
    # Mock soup and cards
    with patch.object(fetcher, '_parse_cards', return_value=[job]):
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            # mock getting the search page
            mock_resp = MagicMock()
            mock_resp.text = "<html></html>"
            mock_resp.status_code = 200
            mock_get.return_value = mock_resp
            
            # Since the only job matches the applied fingerprint, 
            # it should be skipped and _enrich_card should not be called.
            with patch.object(fetcher, '_enrich_card', new_callable=AsyncMock) as mock_enrich:
                results = asyncio.run(fetcher.fetch(["software", "engineer"], location="Remote", applied_fingerprints=applied_fps))
                
                assert len(results) == 0
                mock_enrich.assert_not_called()


def test_duplicate_filtering_in_run(fetcher):
    job1 = {
        "title": "Dev",
        "company": "A",
        "location": "Remote",
        "apply_link": "https://in.indeed.com/viewjob?jk=1"
    }
    job2 = {
        "title": "Dev",
        "company": "A",
        "location": "Remote",
        "apply_link": "https://in.indeed.com/viewjob?jk=1"
    }
    
    with patch.object(fetcher, '_parse_cards', side_effect=[[job1, job2], []]):
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_resp = MagicMock()
            mock_resp.text = "<html></html>"
            mock_get.return_value = mock_resp
            
            with patch.object(fetcher, '_enrich_card', new_callable=AsyncMock) as mock_enrich:
                mock_enrich.return_value = "enriched_job"
                
                results = asyncio.run(fetcher.fetch(["dev"], location="Remote"))
                
                # Should only enrich once because of in-run deduplication
                assert mock_enrich.call_count == 1
                assert len(results) == 1


def test_pagination_and_fallback(fetcher):
    # Test that if page 1 has no cards, it breaks pagination and goes to fallback
    
    with patch.object(fetcher, '_parse_cards', side_effect=[
        [], # First attempt, 0 cards
        [], # Fallback 1, 0 cards
        [{"title": "Fallback Job", "company": "B", "location": "India", "apply_link": "http://x"}], # Fallback 2
        [] # Stop pagination for Fallback 2
    ]):
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_resp = MagicMock()
            mock_resp.text = "<html></html>"
            mock_get.return_value = mock_resp
            
            with patch.object(fetcher, '_enrich_card', new_callable=AsyncMock) as mock_enrich:
                mock_enrich.return_value = "enriched_job"
                
                # Use a specific small city to trigger fallback level 2 (Broader + India)
                results = asyncio.run(fetcher.fetch(["senior", "software", "engineer"], location="Pune"))
                
                # It should have enriched the fallback job
                assert mock_enrich.call_count == 1
                assert len(results) == 1


def test_expired_listing_removal(fetcher):
    job = {
        "title": "Dev",
        "company": "A",
        "location": "Remote",
        "apply_link": "https://in.indeed.com/viewjob?jk=1"
    }
    
    with patch.object(fetcher, '_parse_cards', return_value=[job]):
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            # We want to test _enrich_card directly for expired marker
            
            # Setup mock for detail page
            detail_resp = MagicMock()
            detail_resp.status_code = 200
            detail_resp.text = "<html><body>This job has expired.</body></html>"
            
            # The client.get is called for search page (handled by our _parse_cards mock) 
            # and then detail page (which is the one that matters here)
            mock_get.side_effect = [MagicMock(status_code=200, text=""), detail_resp]
            
            # Call original enrich card by NOT mocking it
            # But we have to make sure the fetch loop breaks, so we side_effect _parse_cards
            with patch.object(fetcher, '_parse_cards', side_effect=[[job], []]):
                results = asyncio.run(fetcher.fetch(["dev"]))
                
                # The job should be filtered out because it's expired
                assert len(results) == 0
