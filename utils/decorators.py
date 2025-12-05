import time
import functools
from typing import Callable, Any
from httpx import HTTPStatusError, ConnectError
from rich.console import Console

console = Console()

def retry_on_failure(max_retries: int = 3, delay: int = 2, exceptions=None) -> Callable:
    """
    A decorator to retry a function call if specific exceptions occur.
    Designed primarily for network operations (like fetcher.py).
    """
    if exceptions is None:
        # Default exceptions to retry on for network operations
        exceptions = (HTTPStatusError, ConnectError, TimeoutError)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt < max_retries - 1:
                        console.print(f"[yellow]Warning:[/yellow] Attempt {attempt + 1}/{max_retries} failed ({e}). Retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        console.print(f"[bold red]Error:[/bold red] Function failed after {max_retries} attempts.")
                        raise # Re-raise the final exception
            return None # Should not be reached

        return wrapper
    return decorator

def handle_exceptions(func: Callable) -> Callable:
    """
    A decorator for CLI commands to catch and print common exceptions cleanly
    instead of letting the program crash with a traceback.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            console.print(f"\n[bold red]FATAL ERROR:[/bold red] An unexpected error occurred.")
            console.print(f"Details: [red]{type(e)._name_}: {e}[/red]")
            # In production, you might log this traceback instead of printing it fully
            # console.print(traceback.format_exc(), style="dim")
            raise SystemExit(1)
            
    return wrapper