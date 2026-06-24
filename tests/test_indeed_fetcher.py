import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from backend.modules.fetchers.indeed_fetcher import IndeedFetcher
from backend.modules.deduper import canonical_fingerprint


@pytest.fixture
def fetcher():
    return IndeedFetcher()


def test_applied_job_exclusion(fetcher):
                                    
    job = {
        "title": "Software Engineer",
        "company": "Tech Corp",
        "location": "Remote",
        "apply_link": "https://in.indeed.com/viewjob?jk=123"
    }
    fp = canonical_fingerprint(job)
    applied_fps = {fp}
    
                         
    with patch.object(fetcher, '_parse_cards', return_value=[job]):
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
                                          
            mock_resp = MagicMock()
            mock_resp.text = "<html></html>"
            mock_resp.status_code = 200
            mock_get.return_value = mock_resp
            
                                                                  
                                                                         
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
                
                                                                         
                assert mock_enrich.call_count == 1
                assert len(results) == 1


def test_pagination_and_fallback(fetcher):
                                                                                 
    
    with patch.object(fetcher, '_parse_cards', side_effect=[
        [],                         
        [],                      
        [{"title": "Fallback Job", "company": "B", "location": "India", "apply_link": "http://x"}],             
        []                                 
    ]):
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_resp = MagicMock()
            mock_resp.text = "<html></html>"
            mock_get.return_value = mock_resp
            
            with patch.object(fetcher, '_enrich_card', new_callable=AsyncMock) as mock_enrich:
                mock_enrich.return_value = "enriched_job"
                
                                                                                         
                results = asyncio.run(fetcher.fetch(["senior", "software", "engineer"], location="Pune"))
                
                                                          
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
                                                                      
            
                                        
            detail_resp = MagicMock()
            detail_resp.status_code = 200
            detail_resp.text = "<html><body>This job has expired.</body></html>"
            
                                                                                          
                                                                       
            mock_get.side_effect = [MagicMock(status_code=200, text=""), detail_resp]
            
                                                         
                                                                                            
            with patch.object(fetcher, '_parse_cards', side_effect=[[job], []]):
                results = asyncio.run(fetcher.fetch(["dev"]))
                
                                                                     
                assert len(results) == 0
