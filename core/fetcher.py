import httpx
from typing import List, Optional, Set
from urllib.parse import urlparse
from rich.progress import track

# Constants
WAYBACK_CDX_API = "https://web.archive.org/cdx/search/cdx"
WAYBACK_TIMEOUT = 10.0
WAYBACK_LIMIT = 500000 # Max URLs to fetch

async def fetch_wayback_urls(domain: str, progress_title: str = "Fetching URLs") -> Set[str]:
    """
    Asynchronously fetches unique, successful URLs from the Wayback Machine CDX API.

    Args:
        domain: The target domain (e.g., example.com).
        progress_title: Title for the Rich progress bar.

    Returns:
        A set of unique URLs (string).
    """
    urls: Set[str] = set()
    
    # CDX Query Parameters (Efficient and Clean)
    params = {
        'url': f".{domain}/",
        'output': 'json',
        'fl': 'original', # Only return the URL string
        'filter': ['statuscode:200', 'statuscode:301', 'statuscode:302'], # Only successful/redirecting links
        'limit': WAYBACK_LIMIT,
        'collapse': 'urlkey' # Unique per URL path
    }
    
    # Use limits for safety and rate-limiting headers
    client_limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    
    try:
        async with httpx.AsyncClient(timeout=WAYBACK_TIMEOUT, limits=client_limits) as client:
            response = await client.get(WAYBACK_CDX_API, params=params)
            response.raise_for_status() 

            # The CDX API returns a JSON array of arrays, where the first element 
            # is the headers, and the rest are the data.
            data = response.json()
            if not data or len(data) <= 1:
                return urls
            
            # The actual URLs start from the second element [1:]
            for row in track(data[1:], description=progress_title):
                # Row is guaranteed to be ['original'] based on 'fl': 'original'
                url = row[0]
                
                # Basic sanity check: ensure the fetched URL actually belongs to the domain
                parsed_url = urlparse(url)
                if parsed_url.netloc.endswith(domain) or parsed_url.netloc == domain:
                    urls.add(url)

    except httpx.ConnectError:
        print(f"[ERROR] Connection failed while fetching {domain} Wayback data.")
    except httpx.HTTPStatusError as e:
        print(f"[ERROR] HTTP error {e.response.status_code} while fetching {domain} Wayback data.")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred during fetching: {e}")

    return urls