"""
Text Formatter - Handle text formatting for slides.
- Capitalize reverent pronouns (He, Him, His, God)
- Split long sections into multiple slides (max 4 lines)
"""

import re
from typing import List, Tuple


# Words to capitalize in reverence
REVERENT_WORDS = {
    'he': 'He',
    'him': 'Him', 
    'his': 'His',
    'himself': 'Himself',
    'god': 'God',
    "god's": "God's",
    'lord': 'Lord',
    "lord's": "Lord's",
    'father': 'Father',
    'son': 'Son',
    'spirit': 'Spirit',
    'holy spirit': 'Holy Spirit',
    'jesus': 'Jesus',
    'christ': 'Christ',
    'savior': 'Savior',
    'saviour': 'Saviour',
    'king': 'King',
    'lamb': 'Lamb',
    'thee': 'Thee',
    'thou': 'Thou',
    'thy': 'Thy',
    'thine': 'Thine',
}


def capitalize_reverent_words(text: str) -> str:
    """
    Capitalize words that refer to God in reverence.
    Context-aware to avoid false positives.
    """
    # Process word by word while preserving structure
    def replace_word(match):
        word = match.group(0)
        word_lower = word.lower()
        
        if word_lower in REVERENT_WORDS:
            replacement = REVERENT_WORDS[word_lower]
            # Preserve original case pattern if already capitalized differently
            if word[0].isupper():
                return replacement
            # Only capitalize if it's in a context that likely refers to God
            # (This is a simplified heuristic - lyrics context usually means it's reverent)
            return replacement
        
        return word
    
    # Match words, including contractions
    result = re.sub(r"\b[\w']+\b", replace_word, text)
    
    return result


def split_into_slides(text: str, max_lines: int = 4) -> List[str]:
    """
    Split text into slide-sized chunks.
    Each chunk has at most max_lines lines.
    Tries to break at natural points (empty lines, punctuation).
    """
    lines = [line.strip() for line in text.strip().split('\n')]
    
    # Remove empty lines but remember where they were (natural break points)
    line_data = []  # (line_text, is_after_empty)
    prev_empty = False
    for line in lines:
        if not line:
            prev_empty = True
        else:
            line_data.append((line, prev_empty))
            prev_empty = False
    
    if not line_data:
        return []
    
    slides = []
    current_slide_lines = []
    
    for i, (line, is_after_empty) in enumerate(line_data):
        # Check if we should start a new slide
        should_break = False
        
        if len(current_slide_lines) >= max_lines:
            should_break = True
        elif len(current_slide_lines) > 0 and is_after_empty and len(current_slide_lines) >= max_lines // 2:
            # Break at empty line if we have a reasonable amount of content
            should_break = True
        
        if should_break:
            slides.append('\n'.join(current_slide_lines))
            current_slide_lines = []
        
        current_slide_lines.append(line)
    
    # Don't forget the last slide
    if current_slide_lines:
        slides.append('\n'.join(current_slide_lines))
    
    return slides


def format_section_for_slides(
    section_key: str,
    section_text: str,
    display_name: str,
    max_lines: int = 4
) -> List[Tuple[str, str]]:
    """
    Format a section into slides.
    Returns list of (title, body) tuples.
    
    Args:
        section_key: e.g., "V1"
        section_text: The lyrics text
        display_name: e.g., "VERSE 1"
        max_lines: Maximum lines per slide
    
    Returns:
        List of (title, body) tuples for each slide
    """
    # Apply text formatting
    formatted_text = capitalize_reverent_words(section_text)
    
    # Split into slides
    slide_texts = split_into_slides(formatted_text, max_lines)
    
    # Create slides with titles
    slides = []
    for text in slide_texts:
        # Title is always the same (e.g., all parts of verse 1 titled "VERSE 1")
        slides.append((display_name, text))
    
    return slides


def format_song_for_slides(
    sections: dict,
    order: List[str],
    get_display_name_func,
    max_lines: int = 4
) -> List[Tuple[str, str]]:
    """
    Format an entire song into slides based on order.
    
    Args:
        sections: Dict of section_key -> lyrics
        order: List of section keys in order
        get_display_name_func: Function to convert key to display name
        max_lines: Maximum lines per slide
    
    Returns:
        List of (title, body) tuples for the entire song
    """
    all_slides = []
    
    for section_key in order:
        # Find the section (handle variations like 'V' matching 'V1', 'C' matching 'C1A')
        section_text = None
        matched_key = section_key
        
        # Normalize the search key
        search_key = section_key.upper().strip()
        
        # Get the base type for matching (C, V, Va, B, etc.)
        if search_key.startswith('VA'):
            search_base = 'VA'
        else:
            search_base = search_key.rstrip('0123456789AB')
        
        # Exact match first
        if search_key in sections:
            section_text = sections[search_key]
            matched_key = search_key
        else:
            # Find first matching section by type
            # If order says "C" and we have "C1", use "C1"
            # If order says "C" multiple times and we only have one chorus, reuse it
            candidates = []
            for key in sections:
                key_upper = key.upper()
                if key_upper.startswith('VA'):
                    key_base = 'VA'
                else:
                    key_base = key_upper.rstrip('0123456789AB')
                
                # Match if same base type
                if search_base == key_base:
                    candidates.append(key)
            
            # Pick the first/best match
            if candidates:
                # If exact number match exists, use it (e.g., V2 -> V2)
                for c in candidates:
                    if c.upper() == search_key:
                        matched_key = c
                        section_text = sections[c]
                        break
                # Otherwise use first candidate (e.g., C -> C1)
                if not section_text:
                    matched_key = candidates[0]
                    section_text = sections[matched_key]
        
        if section_text:
            display_name = get_display_name_func(matched_key)
            slides = format_section_for_slides(
                matched_key, 
                section_text, 
                display_name, 
                max_lines
            )
            all_slides.extend(slides)
        else:
            # Section not found - add placeholder
            display_name = get_display_name_func(section_key)
            all_slides.append((display_name, f"[Section '{section_key}' not found]"))
    
    return all_slides

