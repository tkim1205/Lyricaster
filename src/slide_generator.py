"""
Google Slides Generator - Create slides with specific formatting.

Formatting specs:
- Black background
- Title: Calibri 40pt, #4a86e8, UPPERCASE, underlined, centered
- Body: Calibri 40pt, white, centered
- Max 4 lines per slide
"""

import os
from datetime import datetime
from typing import List, Tuple, Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Google Slides API scope + Drive for moving files
SCOPES = [
    'https://www.googleapis.com/auth/presentations',
    'https://www.googleapis.com/auth/drive.file'
]

# Default folder ID for saving presentations
DEFAULT_FOLDER_ID = '1KdrZ4MvpyJziT74aAtWkWcKOgtVClpLh'

# Slide dimensions (in EMU - English Metric Units, 914400 EMU = 1 inch)
# Standard 16:9 slide: 10 inches x 5.625 inches
SLIDE_WIDTH = 9144000  # 10 inches in EMU
SLIDE_HEIGHT = 5143500  # 5.625 inches in EMU

# Colors
BLACK_RGB = {'red': 0, 'green': 0, 'blue': 0}
TITLE_COLOR_RGB = {'red': 0.29, 'green': 0.525, 'blue': 0.91}  # #4a86e8
WHITE_RGB = {'red': 1, 'green': 1, 'blue': 1}

# Font settings
FONT_FAMILY = 'Calibri'
FONT_SIZE_PT = 40


def get_credentials(credentials_path: str = 'credentials.json', token_path: str = 'token.json') -> Credentials:
    """
    Get Google API credentials.
    Will prompt for OAuth if needed.
    """
    creds = None
    
    # Check for existing token
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # If no valid creds, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(
                    f"Credentials file not found: {credentials_path}\n"
                    "Please download OAuth credentials from Google Cloud Console.\n"
                    "See README.md for setup instructions."
                )
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for next time
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    
    return creds


def create_presentation(title: str, creds: Credentials) -> str:
    """
    Create a new Google Slides presentation.
    Returns the presentation ID.
    """
    service = build('slides', 'v1', credentials=creds)
    
    presentation = {
        'title': title
    }
    
    presentation = service.presentations().create(body=presentation).execute()
    return presentation.get('presentationId')


def add_song_slides(
    presentation_id: str,
    slides_data: List[Tuple[str, str, str]],
    creds: Credentials
) -> None:
    """
    Add slides to an existing presentation.
    
    Args:
        presentation_id: The Google Slides presentation ID
        slides_data: List of (title, body, footer) tuples
        creds: Google API credentials
    """
    service = build('slides', 'v1', credentials=creds)
    
    requests = []
    
    for i, slide_tuple in enumerate(slides_data):
        # Handle both (title, body) and (title, body, footer) formats
        if len(slide_tuple) == 3:
            title, body, footer = slide_tuple
        else:
            title, body = slide_tuple
            footer = ''
        
        slide_id = f'slide_{i}'
        title_id = f'title_{i}'
        body_id = f'body_{i}'
        footer_id = f'footer_{i}'
        
        # Create slide
        requests.append({
            'createSlide': {
                'objectId': slide_id,
                'insertionIndex': i,
                'slideLayoutReference': {
                    'predefinedLayout': 'BLANK'
                }
            }
        })
        
        # Set background to black
        requests.append({
            'updatePageProperties': {
                'objectId': slide_id,
                'pageProperties': {
                    'pageBackgroundFill': {
                        'solidFill': {
                            'color': {
                                'rgbColor': BLACK_RGB
                            }
                        }
                    }
                },
                'fields': 'pageBackgroundFill'
            }
        })
        
        # Only create title text box if there's title text
        if title and title.strip():
            # For title-only slides (no body), center vertically
            is_title_only = not (body and body.strip())
            title_y = (SLIDE_HEIGHT - 800000) // 2 if is_title_only else 300000
            
            # Create title text box
            requests.append({
                'createShape': {
                    'objectId': title_id,
                    'shapeType': 'TEXT_BOX',
                    'elementProperties': {
                        'pageObjectId': slide_id,
                        'size': {
                            'width': {'magnitude': SLIDE_WIDTH - 914400, 'unit': 'EMU'},  # 0.5" padding each side
                            'height': {'magnitude': 800000, 'unit': 'EMU'}
                        },
                        'transform': {
                            'scaleX': 1,
                            'scaleY': 1,
                            'translateX': 457200,  # 0.5" from left
                            'translateY': title_y,
                            'unit': 'EMU'
                        }
                    }
                }
            })
            
            # Insert title text (UPPERCASE)
            requests.append({
                'insertText': {
                    'objectId': title_id,
                    'text': title.upper(),
                    'insertionIndex': 0
                }
            })
            
            # Style title: Calibri 40pt, #4a86e8, underlined, centered
            requests.append({
                'updateTextStyle': {
                    'objectId': title_id,
                    'style': {
                        'fontFamily': FONT_FAMILY,
                        'fontSize': {
                            'magnitude': FONT_SIZE_PT,
                            'unit': 'PT'
                        },
                        'foregroundColor': {
                            'opaqueColor': {
                                'rgbColor': TITLE_COLOR_RGB
                            }
                        },
                        'underline': True,
                        'bold': False
                    },
                    'fields': 'fontFamily,fontSize,foregroundColor,underline,bold'
                }
            })
            
            # Center title
            requests.append({
                'updateParagraphStyle': {
                    'objectId': title_id,
                    'style': {
                        'alignment': 'CENTER'
                    },
                    'fields': 'alignment'
                }
            })
        
        # Only create body text box if there's body text
        if body and body.strip():
            # Create body text box
            requests.append({
                'createShape': {
                    'objectId': body_id,
                    'shapeType': 'TEXT_BOX',
                    'elementProperties': {
                        'pageObjectId': slide_id,
                        'size': {
                            'width': {'magnitude': SLIDE_WIDTH - 457200, 'unit': 'EMU'},  # 0.25" padding each side
                            'height': {'magnitude': 3700000, 'unit': 'EMU'}  # Touches/slightly exceeds footer
                        },
                        'transform': {
                            'scaleX': 1,
                            'scaleY': 1,
                            'translateX': 228600,  # 0.25" from left
                            'translateY': 1000000,  # Start higher
                            'unit': 'EMU'
                        }
                    }
                }
            })
            
            # Insert body text
            requests.append({
                'insertText': {
                    'objectId': body_id,
                    'text': body,
                    'insertionIndex': 0
                }
            })
            
            # Style body: Calibri 40pt, white, centered
            requests.append({
                'updateTextStyle': {
                    'objectId': body_id,
                    'style': {
                        'fontFamily': FONT_FAMILY,
                        'fontSize': {
                            'magnitude': FONT_SIZE_PT,
                            'unit': 'PT'
                        },
                        'foregroundColor': {
                            'opaqueColor': {
                                'rgbColor': WHITE_RGB
                            }
                        },
                        'bold': False
                    },
                    'fields': 'fontFamily,fontSize,foregroundColor,bold'
                }
            })
            
            # Center body
            requests.append({
                'updateParagraphStyle': {
                    'objectId': body_id,
                    'style': {
                        'alignment': 'CENTER'
                    },
                    'fields': 'alignment'
                }
            })
        
        # Add footer (song title) - bottom right, italic, blue
        if footer and footer.strip():
            # Create footer text box
            requests.append({
                'createShape': {
                    'objectId': footer_id,
                    'shapeType': 'TEXT_BOX',
                    'elementProperties': {
                        'pageObjectId': slide_id,
                        'size': {
                            'width': {'magnitude': SLIDE_WIDTH - 914400, 'unit': 'EMU'},  # 0.5" padding each side
                            'height': {'magnitude': 400000, 'unit': 'EMU'}
                        },
                        'transform': {
                            'scaleX': 1,
                            'scaleY': 1,
                            'translateX': 457200,  # 0.5" from left
                            'translateY': SLIDE_HEIGHT - 500000,  # Near bottom
                            'unit': 'EMU'
                        }
                    }
                }
            })
            
            # Insert footer text
            requests.append({
                'insertText': {
                    'objectId': footer_id,
                    'text': footer,
                    'insertionIndex': 0
                }
            })
            
            # Style footer: Calibri 20pt, blue, italic
            requests.append({
                'updateTextStyle': {
                    'objectId': footer_id,
                    'style': {
                        'fontFamily': FONT_FAMILY,
                        'fontSize': {
                            'magnitude': 20,
                            'unit': 'PT'
                        },
                        'foregroundColor': {
                            'opaqueColor': {
                                'rgbColor': TITLE_COLOR_RGB
                            }
                        },
                        'italic': True
                    },
                    'fields': 'fontFamily,fontSize,foregroundColor,italic'
                }
            })
            
            # Right-align footer
            requests.append({
                'updateParagraphStyle': {
                    'objectId': footer_id,
                    'style': {
                        'alignment': 'END'  # Right align
                    },
                    'fields': 'alignment'
                }
            })
    
    # Execute all requests
    if requests:
        body = {'requests': requests}
        service.presentations().batchUpdate(
            presentationId=presentation_id,
            body=body
        ).execute()


def delete_default_slide(presentation_id: str, creds: Credentials) -> None:
    """Delete the default blank slide created with new presentations."""
    service = build('slides', 'v1', credentials=creds)
    
    # Get the presentation to find the default slide
    presentation = service.presentations().get(presentationId=presentation_id).execute()
    slides = presentation.get('slides', [])
    
    if slides:
        # Delete the first slide (default blank slide)
        requests = [{
            'deleteObject': {
                'objectId': slides[0].get('objectId')
            }
        }]
        
        service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={'requests': requests}
        ).execute()


def move_to_folder(file_id: str, folder_id: str, creds: Credentials) -> None:
    """Move a file to a specific Google Drive folder."""
    drive_service = build('drive', 'v3', credentials=creds)
    
    # Get current parents
    file = drive_service.files().get(fileId=file_id, fields='parents').execute()
    previous_parents = ",".join(file.get('parents', []))
    
    # Move to new folder
    drive_service.files().update(
        fileId=file_id,
        addParents=folder_id,
        removeParents=previous_parents,
        fields='id, parents'
    ).execute()


def get_default_title() -> str:
    """Generate default presentation title with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"Lyricaster - {timestamp}"


def generate_slides(
    presentation_title: Optional[str],
    slides_data: List[Tuple[str, str]],
    credentials_path: str = 'credentials.json',
    token_path: str = 'token.json',
    folder_id: str = DEFAULT_FOLDER_ID
) -> str:
    """
    Main function to generate a Google Slides presentation.
    
    Args:
        presentation_title: Title for the presentation (None for auto-generated)
        slides_data: List of (title, body) or (title, body, footer) tuples
        credentials_path: Path to OAuth credentials JSON
        token_path: Path to save/load token
        folder_id: Google Drive folder ID to save to
    
    Returns:
        URL to the created presentation
    """
    creds = get_credentials(credentials_path, token_path)
    
    # Use default title if not provided
    if not presentation_title:
        presentation_title = get_default_title()
    
    # Create presentation
    presentation_id = create_presentation(presentation_title, creds)
    
    # Delete default slide
    delete_default_slide(presentation_id, creds)
    
    # Add our slides
    add_song_slides(presentation_id, slides_data, creds)
    
    # Move to folder
    if folder_id:
        try:
            move_to_folder(presentation_id, folder_id, creds)
            print(f"Moved presentation to folder: {folder_id}")
        except Exception as e:
            # Log error but don't fail - presentation was still created
            print(f"Warning: Could not move to folder {folder_id}: {e}")
            import traceback
            traceback.print_exc()
    
    # Return the URL
    return f"https://docs.google.com/presentation/d/{presentation_id}/edit"


def get_presentation_url(presentation_id: str) -> str:
    """Get the edit URL for a presentation."""
    return f"https://docs.google.com/presentation/d/{presentation_id}/edit"

