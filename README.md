# 🎤 Lyricaster

Generate worship slides from song PDFs with proper formatting for church presentations.

## Features

- **Upload PDFs**: Drag and drop song lyrics PDFs
- **Auto-detect sections**: Parses Verse, Chorus, Vamp, Bridge, etc.
- **Custom order**: Define section order like `V1-C-V2-C-Va`
- **AI Clean & Format**: Optional OpenAI integration to fix OCR errors and format lyrics for easy reading on slides
- **Smart formatting**:
  - Capitalizes reverent words (He, Him, God, etc.)
  - Splits long sections into multiple slides (max 4 lines)
- **Google Slides export**: Creates formatted presentations with:
  - Black background
  - Blue underlined section titles (Calibri 40pt, #4a86e8)
  - White centered lyrics (Calibri 40pt)

## Quick Start

### 1. Install Dependencies

```bash
cd lyricaster
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run the App

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Google Slides Setup (Optional)

To enable Google Slides export, you need to set up Google Cloud credentials:

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Name it (e.g., "Lyricaster") and create

### Step 2: Enable the Google Slides API

1. In your project, go to "APIs & Services" → "Library"
2. Search for "Google Slides API"
3. Click "Enable"

### Step 3: Create OAuth Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - Choose "External" (or "Internal" if using Google Workspace)
   - Fill in app name, email, etc.
   - Add yourself as a test user
4. Create OAuth client ID:
   - Application type: "Desktop app"
   - Name: "Lyricaster"
5. Download the JSON file
6. Rename it to `credentials.json` and place it in the project folder

### Step 4: First Authentication

When you first click "Generate Google Slides", a browser window will open asking you to authorize the app. After authorizing, a `token.json` file will be created and you won't need to authorize again.

## Usage

### Song Order Format

Use this format in the sidebar or in a `song_order.md` file:

```
Song Name: V1-V2-C-V3-C
Another Song: C-Va-C-Va-V-C
```

Section abbreviations:
- `V1`, `V2`, `V3`, `V4` - Verse 1, 2, 3, 4
- `V` - Generic verse
- `C` - Chorus
- `B` - Bridge
- `Va` - Vamp
- `PC` - Pre-Chorus
- `Intro`, `Outro`, `Tag` - Other sections

### PDF Format

The app detects sections labeled in various formats:
- `VERSE 1`, `CHORUS`, `VAMP`
- `[Verse 1]`, `[Chorus]`
- `Verse 1:`, `Chorus:`
- And more...

## Deployment to Streamlit Cloud

1. Push this project to a GitHub repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click "New app" and select your repo
4. Set the main file path to `app.py`
5. Deploy!

**Note**: For Google Slides functionality on Streamlit Cloud, you'll need to set up secrets. See [Streamlit Secrets Management](https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app/secrets-management).

## File Structure

```
lyricaster/
├── app.py                 # Streamlit frontend
├── src/
│   ├── __init__.py
│   ├── pdf_parser.py      # Extract lyrics from PDFs
│   ├── song_order.py      # Parse section order
│   ├── text_formatter.py  # Format text (capitalize, split)
│   ├── slide_generator.py # Google Slides API
│   └── ai_cleaner.py      # AI-powered lyrics cleanup
├── .streamlit/
│   ├── config.toml        # Theme configuration
│   └── secrets.toml       # API keys (gitignored)
├── requirements.txt
├── credentials.json       # (You create this - see setup)
├── token.json            # (Auto-created after first auth)
└── README.md
```

## Troubleshooting

### "Section not found" errors
- Check that your PDF has clearly labeled sections
- The section names in your order must match what's detected

### Google API errors
- Make sure `credentials.json` is in the project root
- Delete `token.json` and re-authenticate if you get permission errors

### PDF parsing issues
- Ensure your PDF has selectable text (not scanned images)
- Try PDFs from different sources; some formats work better than others

## License

MIT License - Feel free to use and modify for your church!

