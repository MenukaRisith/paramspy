import asyncio
import typer
import json
import yaml
from typing import List, Optional
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from paramspy import _version_
from paramspy.core.json_cache import JSONParamCache
from paramspy.core.fetcher import fetch_wayback_urls
from paramspy.core.parser import extract_params_from_url, merge_and_filter_all_params
from paramspy.utils.output import generate_tagged_json_output, print_plain_output

# --- Setup ---
app = typer.Typer(
    name="paramspy",
    help="Smart Parameter Discovery Tool. Use target-specific Wayback data to find high-signal parameters.",
    no_args_is_help=True
)
console = Console()

# Path to the built-in wordlist (relative to the package)
DATA_PATH = Path(__file__).parent / "data" / "builtin_params.json"


def _load_builtin_params() -> List[str]:
    """Loads the curated wordlist from the JSON file."""
    try:
        with open(DATA_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        console.print("[bold red]Error:[/bold red] Built-in parameter list not found. Check installation.")
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
    # FIX: Instantiate cache locally to ensure correct resource initialization
    param_cache = JSONParamCache() 
    
    domain = domain.lower().strip().replace('http://', '').replace('https://', '')
    
    # 1. Check Cache
    cached_params = param_cache.get(domain)
    if cached_params:
        final_params = cached_params
    else:
        # 2. Fetch URLs (Asynchronous)
        console.print(f"[bold yellow]→[/bold yellow] Scanning [bold green]{domain}[/bold green]...")
        
        # We need an async function call, so we wrap it
        # NOTE: fetch_wayback_urls is decorated with retry_on_failure in fetcher.py
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
        console.print("[bold blue]2/3 Merging & Filtering Parameters...[/bold blue]")
        builtin_params = _load_builtin_params()
        final_params = merge_and_filter_all_params(list(extracted_set), builtin_params)
        
        # 5. Store in Cache
        param_cache.set(domain, final_params)
        console.print(f"[bold green]✓[/bold green] Final list saved to cache.")


    # 6. Output Results
    if not final_params:
        console.print("[bold yellow]![/bold yellow] No high-signal parameters found after filtering.")
        return

    # Use utils/output.py for formatting
    if output == "json":
        json_output = generate_tagged_json_output(domain, final_params)
        print(json_output)
    else:
        # Default: Print clean list to stdout (perfect for piping)
        console.print(
            Panel(
                f"Found {len(final_params)} high-signal parameters.", 
                title=f"[bold green]✓ Scan Complete: {domain}[/bold green]",
                border_style="green"
            )
        )
        print_plain_output(final_params)


# --- Cache Management Group ---

cache_app = typer.Typer(name="cache", help="Manage the local parameter cache.")
app.add_typer(cache_app, name="cache")

@cache_app.command("status")
def cache_status():
    """Shows the status of cached domains."""
    # FIX: Instantiate cache locally
    param_cache = JSONParamCache()
    status = param_cache.get_status()
    
    if not status:
        console.print("[yellow]Cache is empty.[/yellow]")
        return
        
    table = Table(title="paramspy Local Cache Status", style="dim")
    table.add_column("Domain", style="green", justify="left")
    table.add_column("Cached Since", justify="left")
    table.add_column("Expires In", style="bold yellow", justify="right")

    for item in status:
        table.add_row(item['domain'], item['cached_since'], item['expires_in'])
        
    console.print(table)
        
@cache_app.command("clear")
def cache_clear(
    domain: Optional[str] = typer.Argument(None, help="Specific domain to clear, or clear all if none specified.")
):
    """Clears the entire cache or a specific domain entry."""
    # FIX: Instantiate cache locally
    param_cache = JSONParamCache()

    if domain:
        param_cache.delete(domain)
        console.print(f"[bold green]✓[/bold green] Cache entry for [bold]{domain}[/bold] cleared.")
    else:
        count = param_cache.clear_all()
        console.print(f"[bold green]✓[/bold green] Cleared [bold]{count}[/bold] entries from the cache.")

# --- Version Command ---

# Using the fixed _version_
def version_callback(value: bool):
    if value:
        console.print(f"paramspy v{_version_}")
        raise typer.Exit()

@app.callback()
def main_callback(
    version: bool = typer.Option(None, "--version", callback=version_callback, is_eager=True, help="Show the application version and exit.")
):
    """The main entry point callback."""
    pass

# Standard practice to run the application
if __name__ == "_main_":
    app()