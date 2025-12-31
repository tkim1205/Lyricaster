"""
Lyricaster - Streamlit App

Upload song PDFs, define the section order, and generate Google Slides
with proper formatting for church worship.
"""

import os
import tempfile
import streamlit as st
from typing import Dict, List, Tuple

from src.pdf_parser import parse_pdf, get_display_name, get_song_title_from_filename
from src.song_order import parse_song_order_line, create_default_order
from src.text_formatter import format_song_for_slides

# Try to import AI cleaner
try:
    from src.ai_cleaner import get_openai_client, clean_all_sections
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

# Try to import slide generator (may fail if Google API not configured)
try:
    from src.slide_generator import generate_slides, get_credentials
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False


# Page config
st.set_page_config(
    page_title="Lyricaster",
    page_icon="🎤",
    layout="wide"
)

# Custom CSS for dark theme feel
st.markdown("""
<style>
    .stApp {
        background-color: #1a1a2e;
    }
    .song-card {
        background-color: #16213e;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border-left: 4px solid #4a86e8;
    }
    .section-tag {
        background-color: #4a86e8;
        color: white;
        padding: 5px 10px;
        border-radius: 5px;
        margin: 2px;
        display: inline-block;
    }
    .preview-slide {
        background-color: black;
        color: white;
        padding: 40px;
        margin: 10px 0;
        border-radius: 8px;
        text-align: center;
    }
    .preview-title {
        color: #4a86e8;
        font-size: 24px;
        text-decoration: underline;
        margin-bottom: 20px;
    }
    .preview-body {
        color: white;
        font-size: 20px;
        white-space: pre-wrap;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if 'songs' not in st.session_state:
        st.session_state.songs = {}  # {filename: {sections: {}, order: [], title: str}}
    if 'slides_preview' not in st.session_state:
        st.session_state.slides_preview = []
    if 'generated_url' not in st.session_state:
        st.session_state.generated_url = None
    if 'openai_api_key' not in st.session_state:
        st.session_state.openai_api_key = ""


def main():
    init_session_state()
    
    # Header
    st.title("🎤 Lyricaster")
    st.markdown("*Generate worship slides from song PDFs*")
    
    # Sidebar for settings
    with st.sidebar:
        st.header("⚙️ Settings")
        
        max_lines = st.slider(
            "Max lines per slide",
            min_value=2,
            max_value=8,
            value=4,
            help="How many lines of lyrics to show per slide"
        )
        
        st.divider()
        
        st.header("📋 Bulk Song Order")
        st.markdown("Paste your song order file content:")
        bulk_order = st.text_area(
            "Song Order",
            placeholder="Psalm 90: V1-V2-C-V3-C\nTrading My Sorrows: C-Va-C-Va-V",
            height=150,
            label_visibility="collapsed"
        )
        
        if st.button("Apply Bulk Order"):
            if bulk_order:
                for line in bulk_order.strip().split('\n'):
                    song_name, order = parse_song_order_line(line)
                    if song_name and order:
                        # Find matching song in uploaded songs
                        for filename, song_data in st.session_state.songs.items():
                            if song_name.lower() in song_data['title'].lower() or \
                               song_data['title'].lower() in song_name.lower():
                                st.session_state.songs[filename]['order'] = order
                                st.success(f"Applied order to: {song_data['title']}")
                                break
        
        st.divider()
        
        # OpenAI API for lyrics cleanup & formatting
        st.header("🤖 AI Clean & Format")
        if AI_AVAILABLE:
            # Check if key is in secrets first (support both naming conventions)
            secret_key = st.secrets.get("OPENAI_API_KEY", "") or st.secrets.get("OPEN_AI_KEY", "")
            if secret_key and not secret_key.startswith("sk-proj-YOUR"):
                st.session_state.openai_api_key = secret_key
                st.success("✅ API key loaded from secrets")
            else:
                # Manual input fallback
                api_key = st.text_input(
                    "OpenAI API Key",
                    value=st.session_state.openai_api_key,
                    type="password",
                    help="Add to .streamlit/secrets.toml to persist"
                )
                if api_key != st.session_state.openai_api_key:
                    st.session_state.openai_api_key = api_key
                
                if api_key:
                    st.success("✅ API key set")
                else:
                    st.info("💡 Add key to secrets.toml")
        else:
            st.warning("OpenAI not installed")
        
        st.divider()
        
        # Google API status
        st.header("🔑 Google API")
        if GOOGLE_API_AVAILABLE:
            if os.path.exists('credentials.json'):
                st.success("✅ Credentials found")
                if os.path.exists('token.json'):
                    st.success("✅ Authenticated")
                else:
                    st.warning("⚠️ Not authenticated yet")
            else:
                st.error("❌ credentials.json not found")
                st.markdown("See README for setup instructions")
        else:
            st.error("❌ Google API not configured")
    
    # Main content area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📤 Upload Songs")
        
        uploaded_files = st.file_uploader(
            "Upload PDF files",
            type=['pdf'],
            accept_multiple_files=True,
            help="Upload one or more song PDFs"
        )
        
        if uploaded_files:
            for uploaded_file in uploaded_files:
                if uploaded_file.name not in st.session_state.songs:
                    # Save to temp file and parse
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    
                    try:
                        sections = parse_pdf(tmp_path)
                        title = get_song_title_from_filename(uploaded_file.name)
                        default_order = create_default_order(sections)
                        
                        st.session_state.songs[uploaded_file.name] = {
                            'sections': sections,
                            'order': default_order,
                            'title': title,
                            'temp_path': tmp_path
                        }
                        st.success(f"Parsed: {title} ({len(sections)} sections found)")
                    except Exception as e:
                        st.error(f"Error parsing {uploaded_file.name}: {e}")
                    finally:
                        # Clean up temp file
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)
        
        # Display uploaded songs
        if st.session_state.songs:
            st.divider()
            st.subheader("📚 Uploaded Songs")
            
            for filename, song_data in st.session_state.songs.items():
                with st.expander(f"🎵 {song_data['title']}", expanded=True):
                    # Show detected sections
                    st.markdown("**Detected sections:**")
                    section_tags = " ".join([f"`{k}`" for k in song_data['sections'].keys()])
                    st.markdown(section_tags)
                    
                    # Edit order
                    st.markdown("**Section order:**")
                    order_str = "-".join(song_data['order'])
                    new_order_str = st.text_input(
                        "Order",
                        value=order_str,
                        key=f"order_{filename}",
                        label_visibility="collapsed"
                    )
                    
                    # Update order if changed
                    new_order = [s.strip() for s in new_order_str.split('-') if s.strip()]
                    if new_order != song_data['order']:
                        st.session_state.songs[filename]['order'] = new_order
                    
                    # Preview sections
                    if st.checkbox("Show section lyrics", key=f"show_{filename}"):
                        for key, lyrics in song_data['sections'].items():
                            st.markdown(f"**{get_display_name(key)}:**")
                            st.text(lyrics[:500] + "..." if len(lyrics) > 500 else lyrics)
                    
                    # Action buttons row
                    col_clean, col_remove = st.columns(2)
                    
                    # AI Clean button
                    with col_clean:
                        if AI_AVAILABLE and st.session_state.openai_api_key:
                            if st.button("🤖 Clean & Format", key=f"clean_{filename}"):
                                client = get_openai_client(st.session_state.openai_api_key)
                                if client:
                                    with st.spinner(f"Formatting {song_data['title']}..."):
                                        try:
                                            # Store original for comparison
                                            original = song_data['sections'].copy()
                                            
                                            cleaned = clean_all_sections(
                                                song_data['title'],
                                                song_data['sections'],
                                                client
                                            )
                                            st.session_state.songs[filename]['sections'] = cleaned
                                            st.success("✅ Cleaned & Formatted!")
                                            
                                            # Show before/after for debugging
                                            with st.expander("📝 See changes", expanded=True):
                                                for key in cleaned:
                                                    if original.get(key) != cleaned.get(key):
                                                        st.markdown(f"**{key}:**")
                                                        col_before, col_after = st.columns(2)
                                                        with col_before:
                                                            st.markdown("*Before:*")
                                                            st.text(original.get(key, '')[:500])
                                                        with col_after:
                                                            st.markdown("*After:*")
                                                            st.text(cleaned.get(key, '')[:500])
                                                        st.divider()
                                        except Exception as e:
                                            st.error(f"Error: {e}")
                                            import traceback
                                            st.code(traceback.format_exc())
                    
                    # Remove button
                    with col_remove:
                        if st.button("🗑️ Remove", key=f"remove_{filename}"):
                            del st.session_state.songs[filename]
                            st.rerun()
    
    with col2:
        st.header("👁️ Preview & Generate")
        
        if st.session_state.songs:
            # Generate preview
            if st.button("🔄 Generate Preview", type="primary"):
                all_slides = []
                
                for filename, song_data in st.session_state.songs.items():
                    # Add song title slide
                    all_slides.append((song_data['title'].upper(), ""))
                    
                    # Add song slides
                    song_slides = format_song_for_slides(
                        song_data['sections'],
                        song_data['order'],
                        get_display_name,
                        max_lines
                    )
                    all_slides.extend(song_slides)
                
                st.session_state.slides_preview = all_slides
            
            # Show preview
            if st.session_state.slides_preview:
                st.markdown(f"**Preview: {len(st.session_state.slides_preview)} slides**")
                
                # Slide navigation
                slide_idx = st.slider(
                    "Slide",
                    min_value=0,
                    max_value=len(st.session_state.slides_preview) - 1,
                    value=0
                )
                
                title, body = st.session_state.slides_preview[slide_idx]
                
                # Preview container
                st.markdown(f"""
                <div class="preview-slide">
                    <div class="preview-title">{title}</div>
                    <div class="preview-body">{body}</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.caption(f"Slide {slide_idx + 1} of {len(st.session_state.slides_preview)}")
                
                st.divider()
                
                # Generate to Google Slides
                if GOOGLE_API_AVAILABLE and os.path.exists('credentials.json'):
                    presentation_title = st.text_input(
                        "Presentation Title",
                        value="Worship Songs",
                        key="presentation_title"
                    )
                    
                    if st.button("🚀 Generate Google Slides", type="primary"):
                        with st.spinner("Creating presentation..."):
                            try:
                                url = generate_slides(
                                    presentation_title,
                                    st.session_state.slides_preview
                                )
                                st.session_state.generated_url = url
                                st.success("✅ Presentation created!")
                            except FileNotFoundError as e:
                                st.error(str(e))
                            except Exception as e:
                                st.error(f"Error: {e}")
                    
                    if st.session_state.generated_url:
                        st.markdown(f"[📎 Open Presentation]({st.session_state.generated_url})")
                else:
                    st.warning("⚠️ Google API not configured. See README for setup.")
                    st.markdown("You can still preview slides above!")
        else:
            st.info("👈 Upload song PDFs to get started")


if __name__ == "__main__":
    main()

