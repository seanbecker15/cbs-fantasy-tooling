import os
import base64
from typing import Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from . import Publisher
from cbs_fantasy_tooling.models import PickemResults

class GmailPublisher(Publisher):
    name = "gmail"
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.readonly'
    ]
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.service = None
    
    def validate_config(self) -> bool:
        required_keys = ['credentials_file', 'from', 'to']
        return all(key in self.config and self.config[key] for key in required_keys)
    
    def authenticate(self):
        creds = None
        credentials_file = os.path.abspath(self.config.get("credentials_file", "credentials.json"))
        token_file = os.path.abspath(self.config.get("token_file", "token.json"))
        
        # Check if credentials.json exists
        if not os.path.exists(credentials_file):
            print(f"Error: {credentials_file} not found!")
            print("Please download your OAuth 2.0 credentials from Google Cloud Console")
            return False
        
        # Load existing token if available
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, self.SCOPES)
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
                    flow = InstalledAppFlow.from_client_secrets_file(credentials_file, self.SCOPES)
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
            self.service = build('gmail', 'v1', credentials=creds)
            profile = self.service.users().getProfile(userId='me').execute()
            print(f"✓ Successfully connected to Gmail for: {profile['emailAddress']}")
            return True
        except Exception as e:
            print(f"Failed to connect to Gmail API: {e}")
            return False
        
    def _create_message(self, results_data: PickemResults) -> str:
        """Create email message with CSV attachment"""
        msg = MIMEMultipart()
        msg['from'] = self.config['from']
        msg['to'] = ', '.join(self.config['to'])
        msg['subject'] = "3GS Results"
        
        # Create HTML body
        wins_data = results_data.get_max_wins_data()
        points_data = results_data.get_max_points_data()
        
        html_body = self._generate_email_template(
            wins_data['max_wins'], wins_data['players'],
            points_data['max_points'], points_data['players']
        )
        
        msg.attach(MIMEText(html_body, 'html'))
        
        # Add CSV attachment
        csv_data = results_data.to_csv()
        attachment = MIMEBase('text', 'csv')
        attachment.set_payload(csv_data.encode())
        encoders.encode_base64(attachment)
        attachment.add_header(
            'Content-Disposition',
            'attachment; filename="results.csv"'
        )
        msg.attach(attachment)
        
        return {'raw': base64.urlsafe_b64encode(msg.as_bytes()).decode()}
    
    def _generate_email_template(self, num_wins, players_with_most_wins, points, players_with_most_points):
        """Generate HTML email template"""
        return f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .content {{
                    padding: 20px;
                    border: 1px solid #ccc;
                    margin: 10px;
                    background-color: #f9f9f9;
                }}
            </style>
        </head>
        <body>
            <div class="content">
                <h3>The 3GS automation ran successfully.</h3>
                <p>Here are the results:</p>
                <ul>
                    <li><strong>Highest number of wins for the week:</strong> {num_wins}</li>
                    <li><strong>Player(s) with the most wins:</strong> {players_with_most_wins}</li>
                    <li><strong>Highest point total for the week:</strong> {points}</li>
                    <li><strong>Player(s) with the most points:</strong> {players_with_most_points}</li>
                </ul>
                <p>CSV is attached.</p>
            </div>
        </body>
        </html>
        """
    
    def publish_pickem_results(self, results_data: PickemResults) -> bool:
        """Send email via Gmail API"""
        try:
            if not self.service:
                self._authenticate()
            
            message = self._create_message(results_data)
            result = self.service.users().messages().send(
                userId='me', body=message).execute()
            
            print(f"Gmail email sent successfully. Message ID: {result['id']}")
            return True
            
        except HttpError as error:
            print(f"Gmail API error: {error}")
            return False
        except Exception as error:
            print(f"Gmail publisher error: {error}")
            return False
