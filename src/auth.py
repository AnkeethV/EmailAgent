import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from src.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN

GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
# Combine scopes for the single refresh token
SCOPES = GMAIL_SCOPES + DRIVE_SCOPES

def get_google_credentials() -> Credentials:
    """
    Constructs and returns Google OAuth 2.0 Credentials using the refresh token.
    The google-auth library will automatically handle refreshing the access token
    when it expires, using the provided refresh token.
    """
    # The token_uri for Google's OAuth 2.0 implementation
    TOKEN_URI = "https://oauth2.googleapis.com/token"

    creds = Credentials(
        token=None, # access token will be fetched automatically via refresh token
        refresh_token=GOOGLE_REFRESH_TOKEN,
        token_uri=TOKEN_URI,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=SCOPES
    )
    return creds

def get_gmail_service():
    """Builds and returns the Gmail API service client."""
    creds = get_google_credentials()
    return build('gmail', 'v1', credentials=creds)

def get_drive_service():
    """Builds and returns the Google Drive API service client."""
    creds = get_google_credentials()
    return build('drive', 'v3', credentials=creds)
