"""Verify the fixed fetchers work correctly."""
import asyncio
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding='utf-8')

from backend.modules.fetchers.internshala_fetcher import InternshalaFetcher
from backend.modules.fetchers.indeed_fetcher import IndeedFetcher


async def test():
    print("=" * 60)
    print("Testing Internshala Fetcher")
    print("=" * 60)
    fetcher = InternshalaFetcher()
    results = await fetcher.fetch(["internship"])
    print(f"Total results: {len(results)}")
    valid = [r for r in results if r.title and r.title != "Unknown"]
    print(f"Valid (non-Unknown) results: {len(valid)}")
    for r in valid[:5]:
        print(f"  [{r.title}] @ {r.company} | {r.location} | {r.apply_link and r.apply_link[:60]}")
    
    print()
    print("=" * 60)
    print("Testing Indeed Fetcher")
    print("=" * 60)
    fetcher2 = IndeedFetcher()
    results2 = await fetcher2.fetch(["AI intern", "machine learning"])
    print(f"Total results: {len(results2)}")
    valid2 = [r for r in results2 if r.title and r.title != "Unknown"]
    print(f"Valid results: {len(valid2)}")
    for r in valid2[:5]:
        print(f"  [{r.title}] @ {r.company} | {r.location}")


asyncio.run(test())
