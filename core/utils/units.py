# zman/core/utils/units.py
"""
Data units and conversion utilities.
"""
from __future__ import annotations
import re
import math

def bytes_to_human(size_bytes: int) -> str:
    """Convert bytes to human-readable format matching zramctl output."""
    if size_bytes <= 0:
        return "0B"
    
    units = ("B", "K", "M", "G", "T", "P")
    i = min(int(math.log(size_bytes, 1024)), len(units) - 1)
    size = size_bytes / pow(1024, i)
    
    return f"{int(size) if size.is_integer() else round(size, 1)}{units[i]}"

def parse_size_to_bytes(size_str: str) -> int:
    """
    Converts a size string like '4G', '512M', '1GiB' to bytes.
    Handles B, K, M, G, T, P suffixes (and their iB/B variants).
    """
    if not isinstance(size_str, str) or not (s := size_str.strip().upper()):
        return 0

    # Match number and optional unit (e.g., 4G, 4GiB, 4GB)
    if not (match := re.match(r"^(\d+(?:\.\d+)?)\s*([A-Z]+)?$", s)):
        return 0
    
    number_str, unit_str = match.groups()
    try:
        value = float(number_str)
    except ValueError:
        return 0
        
    if not unit_str:
        return int(value)

    # Normalize unit: K, KB, KIB -> K
    unit = unit_str[0]
    multipliers = {
        'B': 1,
        'K': 1024,
        'M': 1024**2,
        'G': 1024**3,
        'T': 1024**4,
        'P': 1024**5
    }
    
    if unit not in multipliers:
        return 0
        
    return int(value * multipliers[unit])

def calculate_compression_ratio(data_size_str: str | None, compr_size_str: str | None) -> float | None:
    """Calculates compression ratio from human-readable strings."""
    if not data_size_str or not compr_size_str or "-" in (data_size_str, compr_size_str):
        return None
    
    data_bytes = parse_size_to_bytes(data_size_str)
    compr_bytes = parse_size_to_bytes(compr_size_str)
    
    if compr_bytes == 0:
        return None if data_bytes == 0 else float('inf')
    
    return round(data_bytes / compr_bytes, 2)
