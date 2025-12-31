"""
Google Slides Generator - Create slides with specific formatting.

Formatting specs:
- Black background
- Title: Calibri 40pt, #4a86e8, UPPERCASE, underlined, centered
- Body: Calibri 40pt, white, centered
- Max 4 lines per slide
"""

import os
from typing import List, Tuple, Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Google Slides API scope
SCOPES = ['https://www.googleapis.com/auth/presentations']

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
    slides_data: List[Tuple[str, str]],
    creds: Credentials
) -> None:
    """
    Add slides to an existing presentation.
    
    Args:
        presentation_id: The Google Slides presentation ID
        slides_data: List of (title, body) tuples
        creds: Google API credentials
    """
    service = build('slides', 'v1', credentials=creds)
    
    requests = []
    
    for i, (title, body) in enumerate(slides_data):
        slide_id = f'slide_{i}'
        title_id = f'title_{i}'
        body_id = f'body_{i}'
        
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
        
        # Create title text box
        requests.append({
            'createShape': {
                'objectId': title_id,
                'shapeType': 'TEXT_BOX',
                'elementProperties': {
                    'pageObjectId': slide_id,
                    'size': {
                        'width': {'magnitude': SLIDE_WIDTH - 400000, 'unit': 'EMU'},
                        'height': {'magnitude': 800000, 'unit': 'EMU'}
                    },
                    'transform': {
                        'scaleX': 1,
                        'scaleY': 1,
                        'translateX': 200000,
                        'translateY': 300000,
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
        
        # Create body text box
        requests.append({
            'createShape': {
                'objectId': body_id,
                'shapeType': 'TEXT_BOX',
                'elementProperties': {
                    'pageObjectId': slide_id,
                    'size': {
                        'width': {'magnitude': SLIDE_WIDTH - 400000, 'unit': 'EMU'},
                        'height': {'magnitude': 3500000, 'unit': 'EMU'}
                    },
                    'transform': {
                        'scaleX': 1,
                        'scaleY': 1,
                        'translateX': 200000,
                        'translateY': 1200000,
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


def generate_slides(
    presentation_title: str,
    slides_data: List[Tuple[str, str]],
    credentials_path: str = 'credentials.json',
    token_path: str = 'token.json'
) -> str:
    """
    Main function to generate a Google Slides presentation.
    
    Args:
        presentation_title: Title for the presentation
        slides_data: List of (title, body) tuples
        credentials_path: Path to OAuth credentials JSON
        token_path: Path to save/load token
    
    Returns:
        URL to the created presentation
    """
    creds = get_credentials(credentials_path, token_path)
    
    # Create presentation
    presentation_id = create_presentation(presentation_title, creds)
    
    # Delete default slide
    delete_default_slide(presentation_id, creds)
    
    # Add our slides
    add_song_slides(presentation_id, slides_data, creds)
    
    # Return the URL
    return f"https://docs.google.com/presentation/d/{presentation_id}/edit"


def get_presentation_url(presentation_id: str) -> str:
    """Get the edit URL for a presentation."""
    return f"https://docs.google.com/presentation/d/{presentation_id}/edit"

