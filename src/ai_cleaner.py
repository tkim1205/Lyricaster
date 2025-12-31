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
    client: OpenAI
) -> str:
    """
    Use GPT-4o-mini to clean up lyrics extracted from PDF.
    
    Args:
        song_title: Name of the song (helps AI identify correct lyrics)
        section_name: Section name (VERSE 1, CHORUS, etc.)
        lyrics: Raw extracted lyrics text
        client: OpenAI client
    
    Returns:
        Cleaned lyrics text
    """
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

