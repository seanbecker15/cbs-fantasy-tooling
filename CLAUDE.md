# CBS Fantasy Tooling

## Overview
This is a Python-based web scraping tool that automatically extracts fantasy sports data from CBS Sports fantasy football pools and sends email notifications with the results. The application is designed to run as a scheduled task to collect weekly fantasy league standings.

## Project Structure

### Core Application (`app/` directory)
- **`main.py`** - Entry point that orchestrates the scraping and publishing process
- **`scrape.py`** - Web scraper using Selenium to extract data from CBS Sports
- **`config.py`** - Configuration management for environment variables and settings
- **`storage.py`** - Data models and CSV handling for scraped results
- **`publishers/`** - Publisher system for sending results via different methods:
  - **`email.py`** - Gmail API and SendGrid email publishers
  - **`file.py`** - File and Dropbox publishers for local/cloud storage
  - **`web.py`** - Web publishing capabilities

### Supporting Files
- **`requirements.txt`** - Python dependencies
- **`schedule/`** - Contains macOS LaunchAgent plist file for scheduling
- **`scripts/`** - Helper scripts for scheduling/unscheduling tasks
- **`out/`** - Output directory for CSV results
- **`simulator/`** - Additional simulation tools (separate from main app)

## Key Features

### 1. Automated Web Scraping (`scrape.py`)
- Uses Selenium WebDriver to automate CBS Sports login
- Navigates to fantasy pool standings for specific weeks
- Extracts player names, points, wins, and losses from weekly standings table
- Handles dynamic content loading and week navigation
- Robust error handling with retry logic for unreliable page loads

### 2. Publisher System (`publishers/`)
- **Gmail API Integration** - Primary email publisher using OAuth 2.0 authentication
- **SendGrid Integration** - Legacy email publisher for backward compatibility
- **File Publishing** - Local CSV file output and Dropbox cloud storage
- **Web Publishing** - Web-based result sharing capabilities
- Modular design allows enabling/disabling specific publishers
- HTML-formatted email reports with CSV attachments
- Highlights weekly winners (most wins and most points)

### 3. Configuration Management (`config.py`)
- Environment variable management via `.env` file
- Publisher configuration and validation
- Flexible settings for different deployment scenarios
- Support for multiple email providers and storage options

### 4. Scheduling Integration (`main.py`)
- Calculates current NFL week automatically based on season start date (September 2, 2025)
- Supports manual week overrides for testing
- Integrates scraping and publishing into single workflow
- Automatic fallback between publishers on failure

## Configuration Requirements

### Environment Variables
Core scraping configuration:
- `EMAIL` - CBS Sports login email
- `PASSWORD` - CBS Sports login password

Publisher configuration (via `ENABLED_PUBLISHERS` setting):
- **Gmail Publisher**: Requires `credentials.json` file for OAuth 2.0
- **SendGrid Publisher**: Requires `SENDGRID_API_KEY` for legacy support
- **File Publisher**: Local output directory configuration
- **Web Publisher**: Web hosting credentials and endpoints
- **Dropbox Publisher**: Dropbox API tokens for cloud storage

### Dependencies
Key Python packages from `requirements.txt`:
- `selenium` - Web browser automation for CBS Sports scraping
- `google-auth`, `google-auth-oauthlib`, `google-api-python-client` - Gmail API integration
- `sendgrid` - Legacy SendGrid email support
- `python-dotenv` - Environment variable management
- `dropbox` - Cloud storage integration (optional)
- `requests` - HTTP client library

## Scheduling
- Designed to run weekly on Tuesdays at 9 AM via macOS LaunchAgent
- Helper scripts provided for easy scheduling setup
- Logs stored in `/tmp/cbs-sports-scraper/` directory

## Testing and Development
- Manual week overrides available in `main.py` for testing different weeks
- Includes retry logic for handling CBS Sports page loading issues
- Comprehensive error handling and logging throughout

## Data Output
- Generates CSV format with columns: Name, Points, Wins, Losses
- Identifies and reports weekly leaders in both categories
- Results can be stored locally in `out/` directory

This tool automates the tedious process of manually checking fantasy football results and ensures all league participants receive timely updates via email with detailed standings data.
- If necessary, update CLAUDE.md