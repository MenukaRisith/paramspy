import sqlite3
import os
import json
import time
from typing import List, Optional, Dict, Any

# Define the location for the paramspy cache directory
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".paramspy", "cache")
CACHE_DB_PATH = os.path.join(CACHE_DIR, "paramspy_cache.db")
# Cache validity (Time-To-Live) in seconds (e.g., 30 days)
CACHE_TTL = 30 * 24 * 60 * 60 

class ParamCache:
    """Manages the local SQLite database cache for parameter lists."""

    def _init_(self):
        """Initializes the cache directory and database connection."""
        os.makedirs(CACHE_DIR, exist_ok=True)
        self.conn = sqlite3.connect(CACHE_DB_PATH)
        self.cursor = self.conn.cursor()
        self._setup_db()

    def _setup_db(self):
        """Creates the necessary table if it doesn't exist."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS params (
                domain TEXT PRIMARY KEY,
                params_json TEXT NOT NULL,
                timestamp INTEGER NOT NULL
            )
        """)
        self.conn.commit()

    def get(self, domain: str) -> Optional[List[str]]:
        """
        Retrieves cached parameters for a domain if they are not expired.
        Returns None if not found or expired.
        """
        self.cursor.execute("SELECT params_json, timestamp FROM params WHERE domain = ?", (domain,))
        row = self.cursor.fetchone()

        if row:
            params_json, timestamp = row
            # Check for cache expiration
            if time.time() - timestamp < CACHE_TTL:
                print(f"[CACHE] Using cached results for {domain}. Expires in {self._time_remaining(timestamp)}.")
                return json.loads(params_json)
            else:
                # Cache expired, remove it
                self.delete(domain)
                print(f"[CACHE] Cache for {domain} expired. Refetching data.")
                return None
        return None

    def set(self, domain: str, params: List[str]):
        """
        Stores the list of extracted parameters for a domain.
        Overwrites existing entry.
        """
        params_json = json.dumps(params)
        timestamp = int(time.time())
        self.cursor.execute("""
            INSERT OR REPLACE INTO params (domain, params_json, timestamp)
            VALUES (?, ?, ?)
        """, (domain, params_json, timestamp))
        self.conn.commit()

    def delete(self, domain: str):
        """Deletes a specific domain entry from the cache."""
        self.cursor.execute("DELETE FROM params WHERE domain = ?", (domain,))
        self.conn.commit()

    def clear_all(self) -> int:
        """Clears all entries from the cache."""
        count = self.cursor.execute("SELECT COUNT(*) FROM params").fetchone()[0]
        self.cursor.execute("DELETE FROM params")
        self.conn.commit()
        return count

    def get_status(self) -> List[Dict[str, Any]]:
        """Returns the status of all cached entries."""
        self.cursor.execute("SELECT domain, timestamp FROM params")
        status = []
        for domain, timestamp in self.cursor.fetchall():
            status.append({
                "domain": domain,
                "cached_since": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp)),
                "expires_in": self._time_remaining(timestamp)
            })
        return status

    def _time_remaining(self, timestamp: int) -> str:
        """Helper to calculate and format time remaining until expiration."""
        remaining_seconds = (timestamp + CACHE_TTL) - time.time()
        if remaining_seconds <= 0:
            return "Expired"
        
        days = int(remaining_seconds // (24 * 3600))
        hours = int((remaining_seconds % (24 * 3600)) // 3600)
        
        if days > 0:
            return f"{days} days, {hours} hours"
        elif hours > 0:
            return f"{hours} hours"
        else:
            return "Less than 1 hour"

    def _del_(self):
        """Closes the database connection when the object is destroyed."""
        self.conn.close()