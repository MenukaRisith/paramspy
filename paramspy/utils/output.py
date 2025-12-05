import json
import yaml
from typing import List, Dict, Any, Tuple
from pathlib import Path

# Path to the GF mappings file
MAPPING_PATH = Path(_file_).parent.parent / "data" / "gf_mappings.yaml"

def _load_gf_mappings() -> Dict[str, List[str]]:
    """Loads and returns the GF tag mappings from the YAML file."""
    try:
        with open(MAPPING_PATH, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print("Warning: GF mapping file not found.")
        return {}
    except yaml.YAMLError:
        print("Warning: Failed to parse GF mapping YAML.")
        return {}

def generate_tagged_json_output(domain: str, params: List[str]) -> str:
    """
    Generates a structured JSON output list where each parameter is tagged
    with its relevant Gf-patterns (e.g., 'redirect', 'xss').
    """
    mappings = _load_gf_mappings()
    tagged_list: List[Dict[str, Any]] = []

    for param in params:
        tags: List[str] = []
        
        # Check against all known GF mapping categories
        for tag, param_list in mappings.items():
            if param in param_list:
                tags.append(tag)
        
        tagged_list.append({
            "param": param,
            "tags": tags,
            "domain": domain
        })

    output_data = {
        "domain": domain,
        "count": len(tagged_list),
        "parameters": tagged_list
    }

    return json.dumps(output_data, indent=2)

def print_plain_output(params: List[str]):
    """Prints the clean parameter list directly to stdout for piping."""
    for param in params:
        print(param)