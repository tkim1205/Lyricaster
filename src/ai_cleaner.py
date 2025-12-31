"""
AI Lyrics Cleaner - Use OpenAI to fix OCR errors and clean up lyrics.
"""

import os
from typing import Dict, Optional
from openai import OpenAI


def get_openai_client(api_key: Optional[str] = None) -> Optional[OpenAI]:
    """Get OpenAI client with API key from parameter or environment."""
    key = api_key or os.environ.get('OPENAI_API_KEY')
    if not key:
        return None
    return OpenAI(api_key=key)


def clean_lyrics_with_ai(
    song_title: str,
    section_name: str,
    lyrics: str,
    client: OpenAI,
    format_for_slides: bool = True
) -> str:
    """
    Use GPT-4o-mini to clean up and format lyrics for worship slides.
    
    Args:
        song_title: Name of the song (helps AI identify correct lyrics)
        section_name: Section name (VERSE 1, CHORUS, etc.)
        lyrics: Raw extracted lyrics text
        client: OpenAI client
        format_for_slides: Whether to also format for slide readability
    
    Returns:
        Cleaned and formatted lyrics text
    """
    if format_for_slides:
        prompt = f"""You are a worship lyrics formatter. Clean and format these lyrics for projection slides.

Song: "{song_title}"
Section: {section_name}

Extracted lyrics:
{lyrics}

Instructions:
1. Fix any OCR errors (merged words like "Jesuswalked" → "Jesus walked", missing letters like "lled" → "filled")
2. Fix obvious spelling errors
3. FORMAT FOR READABILITY on worship slides:
   - Split repeated phrases onto separate lines (e.g., "Crown Him King forever, crown Him King forever" → two lines)
   - Each line should be comfortable to read at a glance (aim for 6-10 words max per line)
   - Keep natural phrase breaks - don't split mid-phrase
   - Repeated refrains like "Yes Lord, yes Lord, yes yes Lord" should be one phrase per line
4. Capitalize reverent pronouns: He, Him, His, You, Your (referring to God)
5. Do NOT change the meaning or wording
6. Return ONLY the formatted lyrics, nothing else

Formatted lyrics:"""
    else:
        prompt = f"""You are a lyrics proofreader. Fix any OCR/extraction errors in these lyrics.

Song: "{song_title}"
Section: {section_name}

Extracted lyrics:
{lyrics}

Instructions:
1. Fix any merged words (e.g., "Jesuswalked" → "Jesus walked")
2. Fix any missing letters from ligatures (e.g., "rst" → "first", "lled" → "filled")
3. Fix obvious spelling errors
4. Keep the original line breaks and structure
5. Do NOT add or remove lines
6. Do NOT change the meaning or wording (unless it's clearly an error)
7. Return ONLY the corrected lyrics, nothing else

Corrected lyrics:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low temperature for consistent corrections
            max_tokens=1000
        )
        
        cleaned = response.choices[0].message.content.strip()
        return cleaned
        
    except Exception as e:
        print(f"AI cleaning error: {e}")
        return lyrics  # Return original on error


def clean_all_sections(
    song_title: str,
    sections: Dict[str, str],
    client: OpenAI,
    progress_callback=None
) -> Dict[str, str]:
    """
    Clean all sections of a song with AI.
    
    Args:
        song_title: Name of the song
        sections: Dict of section_key -> lyrics
        client: OpenAI client
        progress_callback: Optional callback(section_name, index, total) for progress updates
    
    Returns:
        Dict of section_key -> cleaned lyrics
    """
    from src.pdf_parser import get_display_name
    
    cleaned_sections = {}
    total = len(sections)
    
    for i, (key, lyrics) in enumerate(sections.items()):
        section_name = get_display_name(key)
        
        if progress_callback:
            progress_callback(section_name, i, total)
        
        cleaned_sections[key] = clean_lyrics_with_ai(
            song_title, 
            section_name, 
            lyrics, 
            client
        )
    
    return cleaned_sections

