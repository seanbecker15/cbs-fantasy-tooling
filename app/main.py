from datetime import datetime
from scrape import run_scraper
from config import Config
from storage import ResultsData, print_results_summary
from publishers.email import GmailPublisher, SendGridPublisher
from publishers.file import FilePublisher, DropboxPublisher
from publishers.web import WebPublisher

override_target_week = None
override_curr_week = None


def __get_weeks_since_start(start_date: str):
    now = datetime.now()
    return (now - datetime.strptime(start_date, '%Y-%m-%d')).days // 7


def create_publishers(config: Config):
    """Create and return list of enabled publishers"""
    publishers = []
    
    # File publisher (always safe to include)
    if config.is_publisher_enabled('file'):
        file_pub = FilePublisher(config.get_publisher_config('file'))
        if file_pub.validate_config():
            publishers.append(('file', file_pub))
        else:
            print("File publisher configuration invalid")
    
    # Gmail publisher
    if config.is_publisher_enabled('gmail'):
        gmail_pub = GmailPublisher(config.get_publisher_config('gmail'))
        if gmail_pub.validate_config():
            publishers.append(('gmail', gmail_pub))
        else:
            print("Gmail publisher configuration invalid - check credentials file and recipients")
    
    # SendGrid publisher (legacy)
    if config.is_publisher_enabled('sendgrid'):
        sendgrid_pub = SendGridPublisher(config.get_publisher_config('sendgrid'))
        if sendgrid_pub.validate_config():
            publishers.append(('sendgrid', sendgrid_pub))
        else:
            print("SendGrid publisher configuration invalid")
    
    # Web publisher
    if config.is_publisher_enabled('web'):
        web_pub = WebPublisher(config.get_publisher_config('web'))
        if web_pub.validate_config():
            publishers.append(('web', web_pub))
        else:
            print("Web publisher configuration invalid")
    
    # Dropbox publisher
    if config.is_publisher_enabled('dropbox'):
        try:
            dropbox_pub = DropboxPublisher(config.get_publisher_config('dropbox'))
            if dropbox_pub.validate_config():
                publishers.append(('dropbox', dropbox_pub))
            else:
                print("Dropbox publisher configuration invalid")
        except ImportError:
            print("Dropbox publisher not available - install dropbox package")
    
    return publishers


def publish_results(results_data: ResultsData, publishers):
    """Publish results using all configured publishers"""
    success_count = 0
    failure_notifications = []
    
    for name, publisher in publishers:
        print(f"\nPublishing via {name}...")
        try:
            if publisher.publish(results_data):
                print(f"✓ {name} publisher succeeded")
                success_count += 1
            else:
                print(f"✗ {name} publisher failed")
                failure_notifications.append(name)
        except Exception as e:
            print(f"✗ {name} publisher error: {e}")
            failure_notifications.append(name)
    
    print(f"\nPublication summary: {success_count}/{len(publishers)} publishers succeeded")
    if failure_notifications:
        print(f"Failed publishers: {', '.join(failure_notifications)}")
    
    return success_count > 0, failure_notifications


def send_failure_notification(config: Config, error_msg: str):
    """Send failure notification using available email publishers"""
    print(f"Sending failure notification: {error_msg}")
    
    # Try Gmail first, then SendGrid as fallback
    email_publishers = []
    
    if config.is_publisher_enabled('gmail') and config.validate_gmail_config():
        gmail_pub = GmailPublisher(config.get_publisher_config('gmail'))
        email_publishers.append(('gmail', gmail_pub))
    
    if config.is_publisher_enabled('sendgrid') and config.validate_sendgrid_config():
        sendgrid_pub = SendGridPublisher(config.get_publisher_config('sendgrid'))
        email_publishers.append(('sendgrid', sendgrid_pub))
    
    if not email_publishers:
        print("No email publishers configured for failure notifications")
        return
    
    # Create minimal failure data structure
    failure_data = {
        'subject': '3GS Automation Failure',
        'message': f'The 3GS automation failed to run. Error: {error_msg}',
        'timestamp': datetime.now()
    }
    
    for name, publisher in email_publishers:
        try:
            # For failure notifications, we need to send a simple email
            # This would need custom implementation in each email publisher
            print(f"Would send failure notification via {name}")
            # TODO: Implement simple text email method for failures
        except Exception as e:
            print(f"Failed to send failure notification via {name}: {e}")


def main():
    config = Config()
    
    if not config.validate_scraping_config():
        print("Scraping configuration invalid - check EMAIL and PASSWORD")
        return

    prev_week_no = override_target_week if override_target_week else __get_weeks_since_start(config.week_one_start_date)
    curr_week_no = override_curr_week if override_curr_week else __get_weeks_since_start(config.week_one_start_date) + 1

    print(f"Current week number: {curr_week_no}")
    print(f"Running scraper for week {prev_week_no}...")
    
    # Create publishers
    publishers = create_publishers(config)
    if not publishers:
        print("No publishers configured! Check ENABLED_PUBLISHERS setting.")
        return
    
    print(f"Enabled publishers: {', '.join([name for name, _ in publishers])}")
    
    try:
        # Run scraper
        raw_results = run_scraper(curr_week_no, prev_week_no)
        
        # Convert to new data structure
        results_data = ResultsData(raw_results, prev_week_no)
        
        # Print summary to console
        print_results_summary(results_data)
        
        # Publish results
        success, failures = publish_results(results_data, publishers)
        
        if not success:
            print("All publishers failed!")
            send_failure_notification(config, "All publishing methods failed")
        elif failures:
            print(f"Some publishers failed: {failures}")
            
    except Exception as e:
        print(f"Error occurred: {e}")
        send_failure_notification(config, str(e))
        return

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()
