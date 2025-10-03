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
- **`simulator/`** - NFL confidence pool strategy simulation tools

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

### 5. Confidence Pool Strategy Simulator (`simulator/`)
- **`main.py`** - Comprehensive NFL confidence pool strategy simulation with real-time odds integration
- **`monte.py`** - Standalone Monte Carlo simulation engine for confidence pool strategy analysis
- **`example_result.md`** - Sample output showing simulation results and strategy recommendations

#### Simulator Features:
- **Real-time Odds Integration**: Fetches current week NFL moneylines from The Odds API
- **De-vig Probability Calculation**: Converts betting odds to fair win probabilities using median consensus across multiple sportsbooks
- **Sharp Book Weighting**: Overweights reputable books like Pinnacle and Circa for more accurate probabilities
- **Multiple Strategy Support**: 
  - `Chalk-MaxPoints`: Pure favorite-picking, confidence ordered by probability
  - `Slight-Contrarian`: Strategic contrarian picks on coin-flip games with mid-confidence boosts
  - `Aggressive-Contrarian`: Multiple contrarian picks including moderate underdogs
  - `Random-MidShuffle`: Probability-based ordering with middle-tier shuffling to reduce correlation
- **Monte Carlo Analysis**: Simulates 20,000 weeks to calculate expected values, standard deviations, and percentile distributions
- **Bonus System Modeling**: Accurately models weekly bonuses (+5 for Most Wins, +10 for Most Points)
- **League Field Composition**: Configurable mix of opponent strategies (32-person league simulation)
- **Automatic Week Detection**: Restricts to current NFL week using Tuesday-to-Tuesday time windows
- **Fallback Mode**: Uses synthetic realistic probability slate if API is unavailable
- **Visual Analytics**: Matplotlib charts showing strategy performance comparisons
- **CSV Export**: Exports detailed strategy comparison results for analysis
- **Prediction Storage**: Automatically saves strategy predictions in structured JSON format using standardized file naming
- **Custom Pick Analysis**: Input your own picks for Monte Carlo simulation and performance analysis against the field

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

Simulator configuration:
- `THE_ODDS_API_KEY` - Required API key from The Odds API for real-time NFL moneylines

### Dependencies
Key Python packages from `requirements.txt`:
- `selenium` - Web browser automation for CBS Sports scraping
- `google-auth`, `google-auth-oauthlib`, `google-api-python-client` - Gmail API integration
- `sendgrid` - Legacy SendGrid email support
- `python-dotenv` - Environment variable management
- `dropbox` - Cloud storage integration (optional)
- `requests` - HTTP client library
- `numpy` - Numerical computing for simulations
- `pandas` - Data analysis and CSV handling
- `matplotlib` - Data visualization and plotting

## Scheduling
- Designed to run weekly on Tuesdays at 9 AM via macOS LaunchAgent
- Helper scripts provided for easy scheduling setup
- Logs stored in `/tmp/cbs-sports-scraper/` directory

## Testing and Development
- Manual week overrides available in `main.py` for testing different weeks
- Includes retry logic for handling CBS Sports page loading issues
- Comprehensive error handling and logging throughout

## Data Output

### Main Application
- Generates CSV format with columns: Name, Points, Wins, Losses
- Identifies and reports weekly leaders in both categories
- Results can be stored locally in `out/` directory

### Simulator
- **Strategy Analysis CSV**: Comparative performance metrics across all strategies saved to `./out` directory
- **Weekly Picks Output**: Detailed pick recommendations with confidence levels for chosen strategy
- **Performance Distribution Charts**: Visual comparison of expected total points by strategy
- **Probability Slate Preview**: Current week's games with consensus win probabilities
- **Prediction Files**: JSON files for each strategy with structured predictions
- **Strategy Summary CSV**: Monte Carlo simulation results comparing all strategies

#### Prediction File Structure
The simulator generates JSON prediction files with the following structure:
```json
{
  "metadata": {
    "strategy": "Random-MidShuffle",
    "week": 2,
    "generated_at": "2025-09-10T09:57:05.612402",
    "total_games": 16,
    "simulator_version": "v2"
  },
  "games": [
    {
      "game_id": "unique_game_identifier",
      "away_team": "Team Name",
      "home_team": "Team Name", 
      "favorite": "Team Name",
      "dog": "Team Name",
      "favorite_prob": 0.8587,
      "commence_time": "2025-09-14T17:01:00Z",
      "prediction": {
        "pick_team": "Team Name",
        "pick_is_favorite": true,
        "confidence_level": 16,
        "confidence_rank": 1
      }
    }
  ]
}
```

**Strategy Codes**: 
- `chalk` - Chalk-MaxPoints strategy
- `slight` - Slight-Contrarian strategy  
- `aggress` - Aggressive-Contrarian strategy
- `shuffle` - Random-MidShuffle strategy
- `user` - Custom user picks

#### Output File Naming Patterns
All simulator outputs are saved to the `./out` directory following consistent naming conventions:

- **Strategy Summary**: `week_{N}_strategy_summary_{YYYYMMDD}_{HHMMSS}.csv`
  - Contains Monte Carlo simulation results comparing expected performance across all strategies
  - Includes metrics like expected points, win probability, bonus chances, and percentile distributions

- **Strategy Predictions**: `week_{N}_predictions_{strategy_code}_{YYYYMMDD}_{HHMMSS}.json`  
  - Individual strategy picks and confidence levels for each game
  - Structured JSON format optimized for LLM consumption and analysis
  - Games sorted by confidence level (highest confidence first)

## Usage

### Running the Simulator

#### Basic Usage
```bash
# Set up environment (or use .env file in root of project)
export THE_ODDS_API_KEY="your_key_here"

# Activate virtual python environment and install dependencies
source venv/bin/activate && pip install -r requirements.txt

# Run simulation with real odds (built-in strategies only)
python simulator/main.py

# Or run standalone Monte Carlo with synthetic data
python simulator/monte.py
```

#### Analyzing Your Custom Picks
```bash
# Analyze your picks alongside built-in strategies
python simulator/main.py --user-picks "Ravens,Bills,Cardinals,Cowboys,Lions,Rams,49ers,Bengals,Packers,Vikings,Steelers,Chargers,Texans,Broncos,Dolphins,Eagles"

# Analyze only your picks (skip built-in strategy comparison)
python simulator/main.py --user-picks "Ravens,Bills,Cardinals,..." --analyze-only

# Load picks from JSON file
python simulator/main.py --picks-file picks.json
```

#### Custom Pick Input Formats
- **Team Names**: Use full names ("Baltimore Ravens") or common abbreviations ("Ravens", "BAL")
- **Confidence Order**: List teams from highest confidence (16) to lowest confidence (1)
- **Flexible Matching**: Handles variations like "Ravens", "Baltimore Ravens", "BAL", etc.

#### Command Line Options
- `--user-picks "team1,team2,..."`: Comma-separated list of teams in confidence order
- `--picks-file path/to/file.json`: Load picks from JSON file
- `--analyze-only`: Skip built-in strategies, only analyze your custom picks

#### Usage Examples

**Example 1: Quick Pick Analysis**
```bash
python simulator/main.py --user-picks "BAL,BUF,ARI,DAL,DET,LAR,SF,CIN,GB,MIN,PIT,LAC,HOU,DEN,MIA,PHI" --analyze-only
```
Output:
```
============================================================
ANALYZING YOUR CUSTOM PICKS
============================================================

Your Custom Pick Analysis:
Expected Performance: 96.80 total points
Expected Wins: 10.31
Risk Assessment: Conservative (no contrarian picks)
Contrarian Picks: 0

Analysis complete. Your expected performance: 96.80 points
```

**Example 2: Full Strategy Comparison**
```bash
python simulator/main.py --user-picks "Ravens,Bills,Cardinals,Cowboys,Lions,Rams,49ers,Bengals,Packers,Vikings,Steelers,Chargers,Texans,Broncos,Dolphins,Eagles"
```
Output:
```
Confidence Pool Strategy — Monte Carlo Summary
(Including your custom picks)
             strategy  expected_total_points
      Chalk-MaxPoints                97.36
    Random-MidShuffle                96.93
          Custom-User                96.80
    Slight-Contrarian                95.03
Aggressive-Contrarian                91.72
```

**Example 3: Team Name Flexibility**
All of these work identically:
```bash
# Full team names
python simulator/main.py --user-picks "Baltimore Ravens,Buffalo Bills,Arizona Cardinals,..."

# Common abbreviations
python simulator/main.py --user-picks "Ravens,Bills,Cardinals,..."

# NFL abbreviations
python simulator/main.py --user-picks "BAL,BUF,ARI,DAL,DET,LAR,SF,CIN,GB,MIN,PIT,LAC,HOU,DEN,MIA,PHI"
```

**Example 4: JSON File Input**
Create `my_picks.json`:
```json
{
  "picks": ["Ravens", "Bills", "Cardinals", "Cowboys", "Lions", "Rams", "49ers", "Bengals", "Packers", "Vikings", "Steelers", "Chargers", "Texans", "Broncos", "Dolphins", "Eagles"]
}
```
Then run:
```bash
python simulator/main.py --picks-file my_picks.json
```

**Example 5: Analyzing Contrarian Strategies**
```bash
python simulator/main.py --user-picks "Ravens,Bills,Cardinals,Cowboys,Patriots,Rams,49ers,Jaguars,Packers,Vikings,Seahawks,Chargers,Texans,Colts,Dolphins,Chiefs"
```
Output would show:
```
Risk Assessment: Moderate (limited contrarian picks)
Contrarian Picks: 4

Contrarian Games:
  New England Patriots at Miami Dolphins -> Patriots (Conf: 12, Prob: 48.0%)
  Jacksonville Jaguars at Cincinnati Bengals -> Jaguars (Conf: 8, Prob: 37.8%)
  ...
```

The simulator provides comprehensive strategy analysis for NFL confidence pools, helping optimize weekly performance through data-driven decision making. It integrates real-time betting market data to generate the most accurate probability assessments available.

This tool automates the tedious process of manually checking fantasy football results and ensures all league participants receive timely updates via email with detailed standings data. The simulator component adds advanced analytics for confidence pool strategy optimization.