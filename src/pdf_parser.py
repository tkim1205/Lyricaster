"""
PDF Parser - Extract lyrics and sections from song PDFs.
Handles two-column layouts, filters out chords, instrumentals, and legal footers.
"""

import re
from typing import Dict, List, Tuple, Optional
import pdfplumber


# Sections we want to extract (case insensitive)
VALID_SECTIONS = {'VERSE', 'CHORUS', 'VAMP', 'BRIDGE', 'PRE-CHORUS', 'TAG'}

# Sections to IGNORE
IGNORED_SECTIONS = {'INSTRUMENTAL', 'INTERLUDE', 'INTRO', 'OUTRO', 'ENDING', 'TURNAROUND'}

# Navigation/direction markers to filter out
NAVIGATION_PATTERNS = [
    r'\(To\s+\w+.*?\)',  # (To Turnaround), (To Instrumental), (To Chorus 1b)
    r'\(\d+\.\)',  # (1.), (2.), (3.)
    r'^To\s+(Turnaround|Instrumental|Chorus|Verse|Bridge|Vamp|Coda|Intro|Outro|Ending|Tag)\b',  # Navigation markers only
    r'Grace Praise',  # Publisher credit
    r'Praise Charts',  # Publisher credit
]


def normalize_section_key(section_type: str, section_num: str = '') -> str:
    """Normalize section to standard key format."""
    section_type = section_type.upper().strip()
    section_num = section_num.strip() if section_num else ''
    
    type_map = {
        'VERSE': 'V',
        'CHORUS': 'C',
        'BRIDGE': 'B',
        'VAMP': 'Va',
        'PRE-CHORUS': 'PC',
        'TAG': 'Tag',
    }
    
    abbrev = type_map.get(section_type, section_type[0])
    return f"{abbrev}{section_num}"


def get_display_name(section_key: str) -> str:
    """Convert section key to display name for slide titles."""
    # Match patterns like V1, C, C1A, C1B, Va, etc.
    # Note: Va must come before V in alternation to match correctly
    match = re.match(r'^(Va|PC|Tag|V|C|B)(\d*[AB]?)$', section_key, re.IGNORECASE)
    if not match:
        return section_key.upper()
    
    abbrev, num = match.groups()
    
    name_map = {
        'V': 'VERSE',
        'C': 'CHORUS',
        'B': 'BRIDGE',
        'Va': 'VAMP',
        'PC': 'PRE-CHORUS',
        'Tag': 'TAG',
    }
    
    full_name = name_map.get(abbrev, abbrev.upper())
    if num:
        return f"{full_name} {num}"
    return full_name


def is_chord(word: str) -> bool:
    """
    Check if a word is a chord symbol.
    Matches: A, Am, Am7, G(4), F2, F/C, Gsus4, Bb, C#m, Dm7/F, etc.
    """
    word = word.strip()
    if not word:
        return False
    
    # Comprehensive chord pattern
    chord_pattern = re.compile(
        r'^[A-G][#b]?'  # Root note (A-G with optional sharp/flat)
        r'(?:m|maj|min|dim|aug|sus|add)?'  # Quality (optional)
        r'[0-9]*'  # Extension like 7, 9, 11, 13 (optional)
        r'(?:\([0-9]+\))?'  # Parenthetical extension like (4) (optional)
        r'(?:/[A-G][#b]?)?$'  # Bass note like /E (optional)
    )
    
    return bool(chord_pattern.match(word))


def is_chord_line(line: str) -> bool:
    """Check if a line consists only of chord symbols and separators."""
    line = line.strip()
    if not line:
        return False
    
    # Check for chord chart patterns like "| C | Am7 | F2 |"
    if '|' in line:
        # Remove pipes and check what's left
        parts = re.split(r'[\s|]+', line)
        parts = [p for p in parts if p and p not in ['x2', 'x3', 'x4']]
        if parts and all(is_chord(p) for p in parts):
            return True
    
    # Split by spaces
    parts = re.split(r'\s+', line)
    parts = [p for p in parts if p]
    
    if not parts:
        return False
    
    # Check if all parts are chords
    return all(is_chord(p) for p in parts)


def is_footer_line(line: str) -> bool:
    """Check if line is part of footer/legal content."""
    line_lower = line.lower()
    footer_indicators = [
        'ccli', 'license', 'copyright', '©', 'www.', '.com', '.org',
        'all rights reserved', 'used by permission', 'terms of use',
        'songselect', 'integrity', 'hosanna', '# ', 'based on the recording'
    ]
    return any(ind in line_lower for ind in footer_indicators)


def is_metadata_line(line: str) -> bool:
    """Check if line is metadata (key, tempo, time signature, etc.)."""
    line_stripped = line.strip()
    # Match lines like "Key - C | Tempo - 72 | Time - 3/4"
    if re.match(r'^Key\s*[-–]', line_stripped, re.IGNORECASE):
        return True
    if re.match(r'^Tempo\s*[-–]', line_stripped, re.IGNORECASE):
        return True
    return False


def is_ignored_section_header(line: str) -> bool:
    """Check if line is header of a section to ignore."""
    line_upper = line.upper().strip()
    # Remove brackets if present
    line_upper = re.sub(r'[\[\]]', '', line_upper).strip()
    
    for ignored in IGNORED_SECTIONS:
        if line_upper == ignored or line_upper.startswith(ignored + ' '):
            return True
    return False


def is_section_header(line: str) -> Optional[Tuple[str, str]]:
    """Check if line is a section header. Returns (section_type, section_num) or None."""
    line_stripped = line.strip()
    
    # Handle [Verse 1] format
    bracket_match = re.match(r'^\[(?P<type>Verse|Chorus|Vamp|Bridge|Pre-Chorus|Tag)\s*(?P<num>\d*[AB]?)\]', 
                              line_stripped, re.IGNORECASE)
    if bracket_match:
        return (bracket_match.group('type').upper(), bracket_match.group('num'))
    
    # Handle VERSE 1, CHORUS, CHORUS 1A, CHORUS 1B, etc. (standalone)
    line_upper = line_stripped.upper()
    for section in VALID_SECTIONS:
        if line_upper == section:
            return (section, '')
        # Match "CHORUS 1A", "VERSE 2", etc.
        match = re.match(rf'^{section}\s*(\d*[AB]?)$', line_upper)
        if match:
            return (section, match.group(1))
    
    return None


def clean_lyrics_line(line: str) -> Optional[str]:
    """Clean a single line of lyrics. Returns None if line should be skipped."""
    line = line.strip()
    
    if not line:
        return None
    
    # Skip chord-only lines
    if is_chord_line(line):
        return None
    
    # Skip footer lines
    if is_footer_line(line):
        return None
    
    # Skip metadata lines
    if is_metadata_line(line):
        return None
    
    # Skip lines that are just "Lai, lai" or similar
    if re.match(r'^[Ll]ai[\s,lai-]+$', line, re.IGNORECASE):
        return None
    
    # Skip section headers (they'll be handled separately)
    if is_section_header(line):
        return None
    if is_ignored_section_header(line):
        return None
    
    # Skip navigation/direction markers
    for nav_pattern in NAVIGATION_PATTERNS:
        if re.search(nav_pattern, line, re.IGNORECASE):
            return None
    
    # Split line into words
    words = line.split()
    cleaned_words = []
    
    for word in words:
        # Strip whitespace from word (sometimes embedded in PDF extraction)
        word = word.strip()
        
        if not word:
            continue
            
        # Skip standalone chord symbols
        if is_chord(word):
            continue
        
        # Skip chord fragments like "/E", "/G#"
        if re.match(r'^/[A-G][#b]?$', word):
            continue
        
        # Keep the word
        cleaned_words.append(word)
    
    # Reconstruct the line
    cleaned = ' '.join(cleaned_words)
    
    # Fix split words like "sor - rows" -> "sorrows", "per - sisted" -> "persisted"
    cleaned = re.sub(r'(\w)\s+-\s+(\w)', r'\1\2', cleaned)
    
    # Fix "A - men" -> "Amen"
    cleaned = re.sub(r'^-\s*men$', 'Amen', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bA\s*-\s*men\b', 'Amen', cleaned, flags=re.IGNORECASE)
    
    # Fix words stuck together like "joy'sgonna" -> "joy's gonna"
    cleaned = re.sub(r"'s(?=[a-z])", "'s ", cleaned)
    
    # Fix "de - stroyed" -> "destroyed" (remaining dashes between word parts)
    cleaned = re.sub(r'\s+-\s+', '', cleaned)
    
    # Fix common merged word patterns (PDF extraction issues)
    # Add space before comma-joined words: "everlasting,You" -> "everlasting, You"
    cleaned = re.sub(r',([A-Z])', r', \1', cleaned)
    cleaned = re.sub(r',([a-z])', r', \1', cleaned)  # Also lowercase
    
    # camelCase splits
    cleaned = re.sub(r'([a-z])([A-Z])', r'\1 \2', cleaned)
    
    # Fix common merged word patterns (lowercase)
    # Words ending in common suffixes that get merged with next word
    common_word_endings = [
        (r'Jesus([a-z])', r'Jesus \1'),  # Jesuswalked -> Jesus walked
        (r'wondrous([a-z])', r'wondrous \1'),  # wondrousfaith -> wondrous faith
        (r'daily([a-z])', r'daily \1'),  # dailyin -> daily in
        (r'never([a-z])', r'never \1'),  # neverfully -> never fully
        (r'unchanging([a-z])', r'unchanging \1'),  # unchanginglove -> unchanging love
        (r'Saviour([a-z])', r'Saviour \1'),  # Saviourprayed -> Saviour prayed
        (r'Savior([a-z])', r'Savior \1'),  # American spelling
        (r'glory([a-z])', r'glory \1'),  # gloryat -> glory at
        (r'lifted([a-z])', r'lifted \1'),  # liftedhigh -> lifted high
        (r'everlasting([a-z])', r'everlasting \1'),  # everlastingYou -> everlasting You
        (r'heaven([a-z])', r'heaven \1'),  # heavenso -> heaven so
        (r'kingdom([a-z])', r'kingdom \1'),  # kingdomfirst -> kingdom first
        (r'summer([a-z])', r'summer \1'),  # summerfilled -> summer filled
        (r'thousand([a-z])', r'thousand \1'),
        (r'ransomed([a-z])', r'ransomed \1'),  # ransomedglory -> ransomed glory
    ]
    
    for pattern, replacement in common_word_endings:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    
    # Fix missing ligatures (fi, fl, ff, etc.) - common PDF extraction issue
    # These often appear as missing characters
    ligature_fixes = [
        (r'\brst\b', 'first'),  # rst -> first
        (r'  ght\b', ' fight'),  # "  ght" -> " fight" (with double space before)
        (r'\bght\b', 'fight'),  # ght -> fight (when standalone)
        (r'lled\b', 'filled'),  # lled -> filled
        (r'\bnd\b', 'find'),  # nd -> find (when standalone)
        (r'ful lled', 'fulfilled'),  # ful lled -> fulfilled
        (r'\beort\b', 'effort'),  # eort -> effort (missing ff)
        (r'\becting\b', 'effecting'),  # ecting -> effecting
        (r'\bects\b', 'effects'),  # ects -> effects
    ]
    
    for pattern, replacement in ligature_fixes:
        cleaned = re.sub(pattern, replacement, cleaned)
    
    # Clean up any double spaces that may have been introduced
    cleaned = re.sub(r'\s{2,}', ' ', cleaned)
    
    # Clean up extra spaces
    cleaned = re.sub(r'\s{2,}', ' ', cleaned)
    cleaned = cleaned.strip()
    
    # Skip if line is too short after cleaning
    if len(cleaned) < 2:
        return None
    
    return cleaned


def extract_columns_from_page(page) -> Tuple[List[str], List[str]]:
    """Extract text from page as two columns based on position."""
    width = page.width
    mid = width / 2
    
    words = page.extract_words()
    if not words:
        return [], []
    
    # Separate into left and right columns
    left_words = [w for w in words if w['x0'] < mid]
    right_words = [w for w in words if w['x0'] >= mid]
    
    def group_into_lines(words, threshold=5):
        if not words:
            return []
        
        words = sorted(words, key=lambda w: (w['top'], w['x0']))
        
        lines = []
        current_line = [words[0]]
        
        for w in words[1:]:
            if abs(w['top'] - current_line[-1]['top']) < threshold:
                current_line.append(w)
            else:
                # Strip each word and remove null/control characters
                line_text = ' '.join(
                    word['text'].strip().replace('\x00', '') 
                    for word in sorted(current_line, key=lambda x: x['x0'])
                )
                lines.append(line_text)
                current_line = [w]
        
        if current_line:
            # Strip each word and remove null/control characters
            line_text = ' '.join(
                word['text'].strip().replace('\x00', '') 
                for word in sorted(current_line, key=lambda x: x['x0'])
            )
            lines.append(line_text)
        
        return lines
    
    left_lines = group_into_lines(left_words)
    right_lines = group_into_lines(right_words)
    
    return left_lines, right_lines


def parse_lines_for_sections(lines: List[str]) -> Dict[str, str]:
    """Parse a list of lines to extract sections."""
    sections = {}
    current_section = None
    current_lyrics = []
    in_ignored_section = False
    
    for line in lines:
        # Check if this is an ignored section header
        if is_ignored_section_header(line):
            if current_section and current_lyrics:
                lyrics_text = '\n'.join(current_lyrics)
                if lyrics_text.strip():
                    sections[current_section] = lyrics_text
            current_section = None
            current_lyrics = []
            in_ignored_section = True
            continue
        
        # Check if this is a valid section header
        section_info = is_section_header(line)
        if section_info:
            if current_section and current_lyrics:
                lyrics_text = '\n'.join(current_lyrics)
                if lyrics_text.strip():
                    sections[current_section] = lyrics_text
            
            section_type, section_num = section_info
            current_section = normalize_section_key(section_type, section_num)
            current_lyrics = []
            in_ignored_section = False
            continue
        
        # Skip if in ignored section
        if in_ignored_section:
            continue
        
        # If we're in a valid section, try to add this line
        if current_section:
            cleaned = clean_lyrics_line(line)
            if cleaned:
                current_lyrics.append(cleaned)
    
    # Save the last section
    if current_section and current_lyrics:
        lyrics_text = '\n'.join(current_lyrics)
        if lyrics_text.strip():
            sections[current_section] = lyrics_text
    
    return sections


def parse_pdf(pdf_path: str) -> Dict[str, str]:
    """
    Main function to parse a PDF and extract sections.
    Handles two-column layouts by parsing columns separately.
    """
    all_sections = {}
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # Extract both columns
            left_lines, right_lines = extract_columns_from_page(page)
            
            # Parse each column for sections
            left_sections = parse_lines_for_sections(left_lines)
            right_sections = parse_lines_for_sections(right_lines)
            
            # Merge sections
            for key, lyrics in left_sections.items():
                if key not in all_sections:
                    all_sections[key] = lyrics
            
            for key, lyrics in right_sections.items():
                if key not in all_sections:
                    all_sections[key] = lyrics
    
    return all_sections


def get_song_title_from_filename(filename: str) -> str:
    """Extract song title from filename, removing number prefix and key suffix."""
    import os
    name = os.path.splitext(os.path.basename(filename))[0]
    
    # Remove leading number and dot
    name = re.sub(r'^\d+\.\s*', '', name)
    
    # Remove key suffix
    name = re.sub(r'\s*-\s*[A-G][#b]?(?:~[A-G][#b]?)?\s*$', '', name)
    
    return name.strip()
