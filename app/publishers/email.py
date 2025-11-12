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

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, Attachment, FileContent, FileName,
    FileType, Disposition)

from . import Publisher
from storage import ResultsData


class GmailPublisher(Publisher):
    SCOPES = ['https://www.googleapis.com/auth/gmail.send']
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.service = None
    
    def validate_config(self) -> bool:
        required_keys = ['credentials_file', 'from', 'to']
        return all(key in self.config and self.config[key] for key in required_keys)
    
    def _authenticate(self):
        """Authenticate with Gmail API using OAuth 2.0"""
        creds = None
        token_file = self.config.get('token_file', 'token.json')
        
        # Load existing token
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, self.SCOPES)
        
        # If no valid credentials, let user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.config['credentials_file'], self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=creds)

    def test_authentication(self) -> bool:
        """Test Gmail API authentication before scraping"""
        try:
            if not self.service:
                self._authenticate()

            # Test that we can access the API
            self.service.users().getProfile(userId='me').execute()
            print("✓ Gmail authentication successful")
            return True

        except HttpError as error:
            print(f"✗ Gmail authentication failed: {error}")
            return False
        except Exception as error:
            print(f"✗ Gmail authentication error: {error}")
            return False

    def _create_message(self, results_data: ResultsData) -> str:
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
    
    def publish(self, results_data: ResultsData) -> bool:
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


class SendGridPublisher(Publisher):
    """Legacy SendGrid publisher for backward compatibility"""
    
    def validate_config(self) -> bool:
        required_keys = ['api_key', 'from', 'to']
        return all(key in self.config and self.config[key] for key in required_keys)
    
    def publish(self, results_data: ResultsData) -> bool:
        """Send email via SendGrid"""
        try:
            # Create CSV attachment
            csv_data = results_data.to_csv()
            encoded_csv = base64.b64encode(csv_data.encode()).decode()
            csv_attachment = Attachment()
            csv_attachment.file_content = FileContent(encoded_csv)
            csv_attachment.file_type = FileType('text/csv')
            csv_attachment.file_name = FileName('results.csv')
            csv_attachment.disposition = Disposition('attachment')
            
            # Get summary data
            wins_data = results_data.get_max_wins_data()
            points_data = results_data.get_max_points_data()
            
            # Generate email body
            email_body = self._generate_email_template(
                wins_data['max_wins'], wins_data['players'],
                points_data['max_points'], points_data['players']
            )
            
            # Create and send message
            message = Mail(
                from_email=self.config['from'],
                to_emails=self.config['to'],
                subject="3GS Results",
                html_content=email_body
            )
            message.attachment = csv_attachment
            
            sg = SendGridAPIClient(self.config['api_key'])
            response = sg.send(message)
            
            if response.status_code >= 400:
                print(f"SendGrid email failed with status code: {response.status_code}")
                print(response.body)
                return False
            else:
                print(f"SendGrid email sent with status code: {response.status_code}")
                return True
                
        except Exception as error:
            print(f"SendGrid publisher error: {error}")
            return False
    
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