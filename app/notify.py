import os
import base64
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, Attachment, FileContent, FileName,
    FileType, Disposition)


def send_email(subject, body, attachment=None):
    message = Mail(
        from_email=os.getenv("NOTIFICATION_FROM"),
        to_emails=os.getenv("NOTIFICATION_TO").split(","),
        subject=subject,
        html_content=body
    )
    if attachment:
        message.attachment = attachment
    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        response = sg.send(message)
        if response.status_code >= 400:
            print(f"Email failed with status code: {response.status_code}")
            print(response.body)
            print(response.headers)
        else:
            print(f"Email sent with status code: {response.status_code}")
    except Exception as e:
        print(e)


def send_success_notification(results):
    csv = "Name,Points,Wins,Losses\n"
    for row in results:
        csv += row.csv() + "\n"

    encoded_csv = base64.b64encode(csv.encode()).decode()
    csv_attachment = Attachment()
    csv_attachment.file_content = FileContent(encoded_csv)
    csv_attachment.file_type = FileType('text/csv')
    csv_attachment.file_name = FileName('results.csv')
    csv_attachment.disposition = Disposition('attachment')

    max_wins = 0
    for row in results:
        if row.results[1] > max_wins:
            max_wins = row.results[1]
    players_with_max_wins = [
        row.name for row in results if row.results[1] == max_wins]
    players_with_max_wins = ', '.join(players_with_max_wins)

    max_points = 0
    for row in results:
        curr_row_points = int(row.results[0])
        if curr_row_points > max_points:
            max_points = curr_row_points
    players_with_max_points = [
        row.name for row in results if int(row.results[0]) == max_points]
    players_with_max_points = ', '.join(players_with_max_points)

    email_body = generate_email_template(
        max_wins, players_with_max_wins, max_points, players_with_max_points)

    send_email("3GS Results", email_body, csv_attachment)


def generate_email_template(num_wins, players_with_most_wins, points, players_with_most_points):
    html_template = f"""
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
    return html_template


def send_failure_notification():
    send_email("3GS Automation Failure",
               "The 3GS automation failed to run. Please check the logs for more information.")
