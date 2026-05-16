import httpx
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Cache-Control': 'max-age=0',
    'Referer': 'https://wellfound.com/',
}

url = 'https://wellfound.com/jobs?q=software&job_types=Internship'

try:
    with httpx.Client(headers=HEADERS, timeout=20) as client:
        resp = client.get(url, follow_redirects=True)
        print(f'Status Code: {resp.status_code}')
        print(f'Response headers: {dict(resp.headers)}')
        print(f'Response length: {len(resp.text)}')
        print(f'First 500 chars: {resp.text[:500]}')
        
        if resp.status_code == 200:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'lxml')
            print('=== Page parsed successfully ===')
        elif resp.status_code == 403:
            print('Blocked by server - 403 Forbidden')

except Exception as e:
    print(f'Error: {e}')
