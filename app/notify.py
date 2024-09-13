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
        print(response.status_code)
        print(response.body)
        print(response.headers)
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

    email_body = "The 3GS Scraper ran successfully. Here are the results:\n"

    max_wins = 0
    for row in results:
        if row.results[1] > max_wins:
            max_wins = row.results[1]
    players_with_max_wins = [
        row.name for row in results if row.results[1] == max_wins]
    email_body += f"Most wins for the week: {max_wins}\n"
    email_body += f"Players with the most wins: {', '.join(players_with_max_wins)}\n"

    max_points = 0
    for row in results:
        curr_row_points = int(row.results[0])
        if curr_row_points > max_points:
            max_points = curr_row_points
    players_with_max_points = [
        row.name for row in results if int(row.results[0]) == max_points]
    email_body += f"Most points for the week: {max_points}\n"
    email_body += f"Players with the most points: {', '.join(players_with_max_points)}\n"

    email_body += "\nThe CSV file for this week is attached."

    send_email("3GS Results", email_body, csv_attachment)

    pass


def send_failure_notification():
    send_email("3GS Automation Failure",
               "The 3GS automation failed to run. Please check the logs for more information.")
