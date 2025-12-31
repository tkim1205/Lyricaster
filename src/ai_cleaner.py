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
        prompt = f"""You are a worship lyrics proofreader. Fix typos and adjust spacing for projection slides.

Song: "{song_title}"
Section: {section_name}

Extracted lyrics:
{lyrics}

STRICT RULES:
1. DO NOT add new words or remove existing words
2. DO NOT change the meaning or rewrite lyrics
3. ONLY fix these issues:
   - Typos and spelling errors (e.g., "kingdom s" → "kingdoms")
   - Merged words (e.g., "Jesuswalked" → "Jesus walked")
   - Split words (e.g., "for ever" → "forever")
   - Missing spaces or extra spaces

4. FORMAT for readability (max 4 slides worth, consolidate lines):
   - Keep lines readable but CONSOLIDATED (don't over-split)
   - Short repeated phrases can stay on ONE line:
     GOOD: "Yes Lord, yes Lord, yes yes Lord"
     BAD: splitting into 3+ separate lines
   - Longer repeated phrases split into 2-3 lines max:
     "Crown Him King forever, crown Him King forever, crown Him King forevermore"
     becomes 2-3 lines, not more
   - Aim for 8-12 words per line when possible

5. Capitalize reverent pronouns: He, Him, His, You, Your (referring to God)

Return ONLY the cleaned lyrics:"""
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
        print(f"AI cleaned '{section_name}': {len(lyrics)} chars -> {len(cleaned)} chars")
        return cleaned
        
    except Exception as e:
        print(f"AI cleaning error for {section_name}: {e}")
        import traceback
        traceback.print_exc()
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

