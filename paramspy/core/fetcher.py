import httpx
import asyncio
import json
from typing import Set, List, Any
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.console import Console # <-- IMPORT THE CONSOLE

# --- Module-level Setup ---
# Initialize the Console object here, so it is ready for use in the Progress bar
console = Console() 

# Base URL for the Wayback Machine CDX API
WAYBACK_CDX_URL = "https://web.archive.org/cdx/search/cdx"

# --- Core Fetching Logic ---

async def _fetch_cdx_data(client: httpx.AsyncClient, domain: str, max_retries: int, progress_task: Progress, task_id: Any) -> Set[str]:
    """
    Asynchronously fetches URLs for a given domain from the Wayback CDX API 
    with built-in retry logic.
    """
    urls: Set[str] = set()
    
    # Parameters for the CDX API request
    params = {
        'url': f".{domain}/",
        'output': 'json',
        'fl': 'original', # We only need the URL itself
        'collapse': 'urlkey', # Deduplicate URLs based on path and query parameters
        'limit': '100000' # Request up to 100,000 records
    }

    for attempt in range(max_retries):
        try:
            progress_task.update(task_id, description=f"[bold cyan]Attempt {attempt + 1}/{max_retries}:[/bold cyan] Fetching CDX data...")
            
            # Use streaming for potentially large responses
            async with client.stream('GET', WAYBACK_CDX_URL, params=params, timeout=60) as response:
                
                response.raise_for_status() # Raise HTTPStatusError for 4xx/5xx responses
                
                content = await response.aread()
                
                # Treat empty content as a successful fetch with no URLs
                if not content.strip():
                     return urls 
                
                # Check for the common error where Wayback returns an error array
                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    # If it's not valid JSON, treat as a fetch error and retry
                    raise Exception("Received invalid JSON response from Wayback.")

                
                # The first item is a header ['urlkey', 'timestamp', 'original', ...]
                if data and len(data) > 1:
                    # Skip the header row and extract the URL (index 0 of the record)
                    for record in data[1:]:
                        if record and len(record) > 0:
                            urls.add(record[0])

                progress_task.update(task_id, total=len(urls), completed=len(urls), description=f"[bold green]Fetch Complete:[/bold green] Found {len(urls):,} URLs.")
                return urls # Success! Exit the retry loop

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP Error {e.response.status_code}"
        except httpx.ConnectError:
            error_msg = "Connection Error"
        except httpx.TimeoutException:
            error_msg = "Timeout Error"
        except Exception as e:
            error_msg = f"Unexpected Error: {type(e)._name_}"

        # Handle failure before retrying
        if attempt < max_retries - 1:
            progress_task.update(task_id, description=f"[bold yellow]Warning:[/bold yellow] Fetch failed ({error_msg}). Retrying in 5s...")
            await asyncio.sleep(5)
        else:
            # Final failure
            progress_task.update(task_id, description=f"[bold red]Fetch Failed:[/bold red] Max retries reached ({error_msg}).", style="red")
            # Raise an explicit error for cli.py to handle
            raise Exception(f"Failed to fetch data after {max_retries} attempts. Last error: {error_msg}")

    return urls # Should be unreachable

async def fetch_wayback_urls(domain: str, progress_title: str = "Fetching URLs") -> Set[str]:
    """
    Main entry point to fetch and process all historical URLs for a domain.
    """
    # Use Progress bar for visualization
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console, # <--- Uses the module-level console INSTANCE
        transient=True
    ) as progress:
        
        task_id = progress.add_task(progress_title, total=None) # Total unknown initially
        
        # Use a single AsyncClient instance for all requests
        async with httpx.AsyncClient(http2=True, follow_redirects=True) as client:
            try:
                # Call the inner function with retry logic
                urls = await _fetch_cdx_data(client, domain, max_retries=3, progress_task=progress, task_id=task_id)
                return urls
            except Exception as e:
                # Re-raise the exception caught by the inner function
                raise e