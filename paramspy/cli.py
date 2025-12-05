import asyncio
import typer
import json
from typing import List, Optional
from pathlib import Path
from rich.console import Console

from paramspy import _version_
from paramspy.core.cache import ParamCache
from paramspy.core.fetcher import fetch_wayback_urls
from paramspy.core.parser import extract_params_from_url, merge_and_filter_all_params

# --- Setup ---
app = typer.Typer(
    name="paramspy",
    help="Smart Parameter Discovery Tool. Use target-specific Wayback data to find high-signal parameters.",
    no_args_is_help=True
)
console = Console()
param_cache = ParamCache()

# Path to the built-in wordlist (relative to the package)
DATA_PATH = Path(_file_).parent / "data" / "builtin_params.json"


def _load_builtin_params() -> List[str]:
    """Loads the curated wordlist from the JSON file."""
    try:
        with open(DATA_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        console.print("[bold red]Error:[/bold red] Built-in parameter list not found.")
        return []
    except json.JSONDecodeError:
        console.print("[bold red]Error:[/bold red] Failed to parse built-in parameter list.")
        return []

# --- Core Logic Command ---

@app.command()
def scan(
    domain: str = typer.Argument(..., help="The target domain (e.g., tesla.com)."),
    aggressive: bool = typer.Option(False, "--aggressive", "-a", help="Enable aggressive mode (future: includes CommonCrawl/OTX)."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output format: json or leave blank for plain list (stdout)."),
):
    """
    Scans the given domain using Wayback Machine data to extract parameters.
    """
    
    domain = domain.lower().strip().replace('http://', '').replace('https://', '')
    
    # 1. Check Cache
    cached_params = param_cache.get(domain)
    if cached_params:
        final_params = cached_params
    else:
        # 2. Fetch URLs (Asynchronous)
        console.print(f"[bold yellow]→[/bold yellow] Scanning [bold green]{domain}[/bold green]...")
        
        # We need an async function call, so we wrap it
        urls = asyncio.run(fetch_wayback_urls(domain, progress_title="[bold blue]1/3 Fetching URLs[/bold blue]"))
        
        if not urls:
            console.print(f"[bold red]Error:[/bold red] No URLs found for {domain} in Wayback Machine.")
            raise typer.Exit(code=1)
        
        console.print(f"[bold green]✓[/bold green] Found {len(urls):,} unique URLs.")
        
        # 3. Extract and Clean Params
        extracted_set = set()
        for url in urls:
            extracted_set.update(extract_params_from_url(url))

        # 4. Merge with Built-in List
        builtin_params = _load_builtin_params()
        final_params = merge_and_filter_all_params(list(extracted_set), builtin_params)
        
        # 5. Store in Cache
        param_cache.set(domain, final_params)

    # 6. Output Results
    if not final_params:
        console.print("[bold yellow]![/bold yellow] No high-signal parameters found after filtering.")
        return

    if output == "json":
        # Future: Use GF tags here for full JSON object
        print(json.dumps({"domain": domain, "parameters": final_params}, indent=2))
    else:
        # Default: Print clean list to stdout (perfect for piping)
        console.print(f"\n[bold green]✓ Final List ({len(final_params)})[/bold green] (Ready to pipe):")
        for param in final_params:
            print(param)

# --- Cache Management Group ---

cache_app = typer.Typer(name="cache", help="Manage the local parameter cache.")
app.add_typer(cache_app, name="cache")

@cache_app.command("status")
def cache_status():
    """Shows the status of cached domains."""
    status = param_cache.get_status()
    if not status:
        console.print("[yellow]Cache is empty.[/yellow]")
        return
        
    console.print(f"[bold blue]Cache Status ({len(status)} domains):[/bold blue]")
    for item in status:
        console.print(f"  [green]{item['domain']}[/green]: Cached since {item['cached_since']} (Expires in {item['expires_in']})")
        
@cache_app.command("clear")
def cache_clear(
    domain: Optional[str] = typer.Argument(None, help="Specific domain to clear, or clear all if none specified.")
):
    """Clears the entire cache or a specific domain entry."""
    if domain:
        param_cache.delete(domain)
        console.print(f"[bold green]✓[/bold green] Cache entry for [bold]{domain}[/bold] cleared.")
    else:
        count = param_cache.clear_all()
        console.print(f"[bold green]✓[/bold green] Cleared [bold]{count}[/bold] entries from the cache.")

# --- Version Command ---

def version_callback(value: bool):
    if value:
        print(f"paramspy v{_version_}")
        raise typer.Exit()

@app.callback()
def main_callback(
    version: bool = typer.Option(None, "--version", callback=version_callback, is_eager=True, help="Show the application version and exit.")
):
    """The main entry point callback."""
    pass

# Standard practice to run the application
if _name_ == "_main_":
    app()