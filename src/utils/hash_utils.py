"""
Utility functions for generating hash codes
"""
import hashlib
import json
from typing import Dict, Any


def generate_hash_code(data: Dict[str, Any]) -> str:
    """
    Generate a 24-character hash code from a dictionary of data
    
    Args:
        data: Dictionary of data to hash
        
    Returns:
        24-character hash code
    """
    # Sort the keys to ensure consistent hashing
    sorted_data = {k: data[k] for k in sorted(data.keys())}
    
    # Convert to JSON string
    json_str = json.dumps(sorted_data, sort_keys=True, default=str)
    
    # Generate hash
    hash_obj = hashlib.sha256(json_str.encode())
    
    # Return first 24 characters of the hexadecimal digest
    return hash_obj.hexdigest()[:24]