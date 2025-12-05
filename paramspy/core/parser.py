import re
from typing import List, Set
from urllib.parse import urlparse, parse_qs

# Regex to find parameters in query strings (?p=v) or matrix parameters (/path;p=v)
# 1. Finds key=value pairs in a query string (after ?)
# 2. Finds key=value pairs after a semicolon (;) for matrix parameters
PARAM_REGEX = re.compile(r'[?&;](?P<param>[^=]+)=')

# Blacklist patterns to filter out common noise that looks like a parameter name
# (e.g., long tokens, UUIDs, single digits that sometimes show up)
NOISE_PATTERNS = [
    r'^__utm[a-z]$',  # Google Analytics garbage
    r'^sid$', r'^session$', # Often session IDs in query string values, not useful as a generic param
    r'^v$', r'^ts$', r'^t$', r'^id\d*$', # Version, timestamp, simple IDs (can be noisy)
]
NOISE_REGEX = re.compile('|'.join(NOISE_PATTERNS), re.IGNORECASE)

def extract_params_from_url(url: str) -> Set[str]:
    """
    Extracts parameter names from a single URL using regex to handle both
    standard query strings and matrix parameters.
    """
    params: Set[str] = set()
    
    # 1. Use regex for quick extraction (handles both ?p=v and ;p=v)
    matches = PARAM_REGEX.findall(url)
    params.update(matches)
    
    # 2. Use urllib.parse for robust handling of the query string part
    try:
        parsed = urlparse(url)
        # parse_qs returns a dictionary where keys are the parameter names
        query_params = parse_qs(parsed.query).keys()
        params.update(query_params)
    except Exception:
        # Silently ignore parsing errors
        pass
    
    return params

def clean_and_filter_params(params: Set[str]) -> List[str]:
    """
    Applies aggressive cleaning, filtering, and blacklisting to parameter names.
    """
    cleaned_params: Set[str] = set()
    
    for param in params:
        # 1. Lowercase and strip whitespace
        p = param.lower().strip()
        
        # 2. Filter out single-character or excessively long garbage
        if len(p) < 2 or len(p) > 50:
            continue
            
        # 3. Filter out parameters that are purely numeric (usually noise like timestamps or codes)
        if p.isdigit():
            continue
            
        # 4. Filter against known noise patterns
        if NOISE_REGEX.search(p):
            continue
            
        # 5. Check for basic characters (avoiding parameters with weird encoding or characters)
        if re.search(r'[^a-z0-9_\-\.]', p):
            continue

        cleaned_params.add(p)
            
    # Convert the resulting set to a sorted list for consistent output
    return sorted(list(cleaned_params))

def merge_and_filter_all_params(
    target_params: List[str], 
    builtin_params: List[str]
) -> List[str]:
    """
    Merges target-specific params with the high-signal built-in list, 
    removes duplicates, and sorts.
    """
    
    # Use a set for efficient merging and deduplication
    final_set = set(target_params)
    final_set.update(builtin_params)
    
    # Final check: run through the cleaning logic one more time to catch 
    # any noise that may have slipped into the built-in list over time
    final_list = clean_and_filter_params(final_set)
    
    return final_list