#!/usr/bin/env python3
"""
Standalone Gmail API authentication script.
Run this to authenticate and generate token.json without running the main application.
"""

import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail API scopes for sending emails and reading profile
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly'
]

def authenticate_gmail():
    """Authenticate with Gmail API and save token for future use"""
    creds = None
    credentials_file = os.path.abspath("credentials.json")
    token_file = os.path.abspath("token.json")
    
    # Check if credentials.json exists
    if not os.path.exists(credentials_file):
        print(f"Error: {credentials_file} not found!")
        print("Please download your OAuth 2.0 credentials from Google Cloud Console")
        return False
    
    # Load existing token if available
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        print(f"Found existing {token_file}")
    
    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            try:
                creds.refresh(Request())
                print("✓ Token refreshed successfully")
            except Exception as e:
                print(f"Failed to refresh token: {e}")
                print("Re-authenticating...")
                creds = None
        
        if not creds or creds.expired or not creds.valid:
            print("Starting OAuth authentication flow...")
            print("A browser window will open for you to sign in to Google")
            try:
                # Clear any cached browser state by adding prompt parameter
                flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
                # Force account selection to avoid cached auth
                creds = flow.run_local_server(port=8080, prompt='select_account', open_browser=True)
                print("✓ Authentication successful!")
            except Exception as e:
                print(f"Authentication failed: {e}")
                return False
        
        # Save credentials for future use
        try:
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
            print(f"✓ Credentials saved to {token_file}")
        except Exception as e:
            print(f"Failed to save token: {e}")
            return False
    else:
        print("✓ Valid credentials already exist")
    
    # Test the connection
    try:
        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        print(f"✓ Successfully connected to Gmail for: {profile['emailAddress']}")
        return True
    except Exception as e:
        print(f"Failed to connect to Gmail API: {e}")
        return False

if __name__ == "__main__":
    print("Gmail API Authentication")
    print("=" * 30)
    
    success = authenticate_gmail()
    
    if success:
        print("\n✓ Authentication complete! You can now run the main application.")
    else:
        print("\n✗ Authentication failed. Please check your configuration.")