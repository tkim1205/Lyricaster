"""
Song Order Parser - Parse song order format like "V1-V2-C-V3-C-Va"
"""

import re
from typing import List, Dict, Tuple


def parse_song_order_line(line: str) -> Tuple[str, List[str]]:
    """
    Parse a single line from song_order.md
    Input: "Trading My Sorrows: C-Va-C-Va-V-C-Va-V-C-Va-Va"
    Output: ("Trading My Sorrows", ["C", "Va", "C", "Va", "V", "C", "Va", "V", "C", "Va", "Va"])
    """
    line = line.strip()
    if not line or line.startswith('#'):
        return None, []
    
    # Split on colon or dash after song name
    # Handle formats like:
    # - "Song Name: V1-V2-C"
    # - "Song Name - V1-V2-C" 
    # - "Song Name V1-V2-C"
    
    # Try colon first
    if ':' in line:
        parts = line.split(':', 1)
        song_name = parts[0].strip()
        order_str = parts[1].strip()
    else:
        # Try to find where the order starts (first section marker)
        match = re.search(r'\s+(V\d*|C|B|Va|PC|Intro|Outro|Tag)[-\s]', line, re.IGNORECASE)
        if match:
            song_name = line[:match.start()].strip()
            order_str = line[match.start():].strip()
        else:
            return line, []
    
    # Parse the order string
    # Split by dash, handling spaces
    order_str = order_str.strip(' -')
    sections = re.split(r'[-\s]+', order_str)
    
    # Clean and normalize section names
    cleaned_sections = []
    for s in sections:
        s = s.strip()
        if s:
            # Normalize common formats
            s_upper = s.upper()
            if s_upper == 'VERSE' or s_upper == 'V':
                s = 'V'
            elif s_upper == 'CHORUS':
                s = 'C'
            elif s_upper == 'BRIDGE':
                s = 'B'
            elif s_upper == 'VAMP':
                s = 'Va'
            elif s_upper.startswith('VERSE'):
                num = re.search(r'\d+', s)
                s = f"V{num.group() if num else ''}"
            cleaned_sections.append(s)
    
    return song_name, cleaned_sections


def parse_song_order_file(content: str) -> Dict[str, List[str]]:
    """
    Parse entire song_order.md content.
    Returns dict: {"Song Name": ["V1", "C", "V2", "C", ...], ...}
    """
    result = {}
    
    for line in content.strip().split('\n'):
        song_name, order = parse_song_order_line(line)
        if song_name and order:
            result[song_name] = order
    
    return result


def match_song_to_order(song_name: str, order_dict: Dict[str, List[str]]) -> List[str]:
    """
    Find matching order for a song name (fuzzy matching).
    """
    song_name_lower = song_name.lower().strip()
    
    # Exact match first
    for name, order in order_dict.items():
        if name.lower().strip() == song_name_lower:
            return order
    
    # Partial match (song name contains or is contained)
    for name, order in order_dict.items():
        name_lower = name.lower().strip()
        if name_lower in song_name_lower or song_name_lower in name_lower:
            return order
    
    # Word-based matching
    song_words = set(song_name_lower.split())
    best_match = None
    best_score = 0
    
    for name, order in order_dict.items():
        name_words = set(name.lower().split())
        common = len(song_words & name_words)
        if common > best_score:
            best_score = common
            best_match = order
    
    if best_score >= 2:  # At least 2 words match
        return best_match
    
    return None


def validate_order_against_sections(order: List[str], available_sections: Dict[str, str]) -> List[str]:
    """
    Check which sections in the order are missing from available sections.
    Returns list of missing section keys.
    """
    missing = []
    for section in order:
        # Handle sections without numbers that might need matching
        if section not in available_sections:
            # Try to find a match (e.g., 'V' might match 'V1')
            found = False
            for key in available_sections:
                if key.startswith(section) or section.startswith(key.rstrip('0123456789')):
                    found = True
                    break
            if not found:
                missing.append(section)
    return missing


def create_default_order(sections: Dict[str, str]) -> List[str]:
    """
    Create a default order from available sections.
    Typically: V1, C, V2, C, V3, C, etc.
    """
    verses = sorted([k for k in sections if k.startswith('V') and k != 'Va'])
    choruses = [k for k in sections if k == 'C']
    bridges = [k for k in sections if k.startswith('B')]
    vamps = [k for k in sections if k == 'Va']
    others = [k for k in sections if k not in verses + choruses + bridges + vamps]
    
    order = []
    
    # Interleave verses and choruses
    for i, verse in enumerate(verses):
        order.append(verse)
        if choruses:
            order.append('C')
    
    # Add remaining sections
    order.extend(bridges)
    order.extend(vamps)
    order.extend(others)
    
    return order

