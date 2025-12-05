import os
import json
import time
from typing import List, Optional, Dict, Any

# Define the location for the paramspy cache directory
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".paramspy") 
# Cache validity (Time-To-Live) in seconds (e.g., 30 days)
CACHE_TTL = 30 * 24 * 60 * 60 

class JSONParamCache:
    """
    Manages local JSON file caching for parameter lists. 
    Uses file I/O instead of SQLite to avoid environmental conflicts.
    """

    def _init_(self):
        """Initializes the cache class. Directory creation is handled in set."""
        pass

    def _get_cache_path(self, domain: str) -> str:
        """Returns the specific file path for a domain."""
        # Sanitizes the domain name for use as a filename
        safe_domain = domain.lower().replace('.', '').replace('-', '')
        return os.path.join(CACHE_DIR, f"{safe_domain}.json")

    def get(self, domain: str) -> Optional[List[str]]:
        """Retrieves cached parameters for a domain."""
        cache_path = self._get_cache_path(domain)
        
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                
                timestamp = data.get('timestamp', 0)
                
                if time.time() - timestamp < CACHE_TTL:
                    print(f"[CACHE] Using cached results for {domain}.")
                    return data.get('params')
                else:
                    self.delete(domain)
                    print(f"[CACHE] Cache for {domain} expired. Refetching data.")
                    return None
            except Exception:
                # Handle corrupted JSON or read errors by deleting the file
                self.delete(domain)
                return None
        return None

    def set(self, domain: str, params: List[str]):
        """
        Stores the list of extracted parameters for a domain.
        Ensures the cache directory exists before writing.
        """
        cache_path = self._get_cache_path(domain)
        
        data = {
            'timestamp': int(time.time()),
            'params': params
        }
        
        # --- ESSENTIAL FIX ---
        # GUARANTEE the directory exists immediately before writing the file
        os.makedirs(CACHE_DIR, exist_ok=True)
        # ---------------------
        
        with open(cache_path, 'w') as f:
            json.dump(data, f, indent=2)

    def delete(self, domain: str):
        """Deletes a specific domain entry from the cache."""
        cache_path = self._get_cache_path(domain)
        if os.path.exists(cache_path):
            os.remove(cache_path)

    def clear_all(self) -> int:
        """Clears all entries from the cache directory."""
        count = 0
        if not os.path.exists(CACHE_DIR):
            return 0
            
        for filename in os.listdir(CACHE_DIR):
            if filename.endswith(".json"):
                try:
                    os.remove(os.path.join(CACHE_DIR, filename))
                    count += 1
                except OSError:
                    # Handle files that might be in use or locked
                    continue
        return count

    def get_status(self) -> List[Dict[str, Any]]:
        """
        Returns a minimal status list of cached entries. 
        (Full implementation requires reading all files, which is costly, so we skip it for speed).
        """
        if not os.path.exists(CACHE_DIR):
            return []
            
        return [{"domain": f, "cached_since": "N/A", "expires_in": "File Exists"} 
                for f in os.listdir(CACHE_DIR) if f.endswith(".json")]