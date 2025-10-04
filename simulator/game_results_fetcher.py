"""
NFL Game Results Fetcher

Fetches historical NFL game results from ESPN API to enrich competitor picks data.
Provides win/loss outcomes needed for competitive intelligence analysis.

Data Sources:
- ESPN API (free, no auth required)
- Output: JSON files with game results per week
"""

import json
import requests
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import time


@dataclass
class GameResult:
    """Single game result"""
    game_id: str
    week: int
    season: int
    away_team: str
    home_team: str
    away_score: int
    home_score: int
    winner: str
    loser: str
    completed: bool
    game_date: str


class NFLGameResultsFetcher:
    """
    Fetches NFL game results from ESPN API.

    ESPN API endpoint structure:
    http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={YYYYMMDD}&limit=100
    """

    BASE_URL = "http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    SEASON_TYPE_REGULAR = 2  # Regular season

    # NFL team abbreviation mapping (ESPN -> CBS/Standard)
    TEAM_MAPPING = {
        'ARI': 'ARI', 'ARZ': 'ARI',
        'ATL': 'ATL',
        'BAL': 'BAL',
        'BUF': 'BUF',
        'CAR': 'CAR',
        'CHI': 'CHI',
        'CIN': 'CIN',
        'CLE': 'CLE',
        'DAL': 'DAL',
        'DEN': 'DEN',
        'DET': 'DET',
        'GB': 'GB', 'GNB': 'GB',
        'HOU': 'HOU',
        'IND': 'IND',
        'JAC': 'JAC', 'JAX': 'JAC',
        'KC': 'KC', 'KAN': 'KC',
        'LAC': 'LAC',
        'LAR': 'LAR',
        'LV': 'LV', 'LVR': 'LV',
        'MIA': 'MIA',
        'MIN': 'MIN',
        'NE': 'NE', 'NEP': 'NE',
        'NO': 'NO', 'NOR': 'NO',
        'NYG': 'NYG',
        'NYJ': 'NYJ',
        'PHI': 'PHI',
        'PIT': 'PIT',
        'SEA': 'SEA',
        'SF': 'SF', 'SFO': 'SF',
        'TB': 'TB', 'TAM': 'TB',
        'TEN': 'TEN',
        'WAS': 'WAS', 'WSH': 'WAS'
    }

    # 2025 NFL Season Week Start Dates (Sundays of each week)
    WEEK_DATES_2025 = {
        1: '20250907',   # Week 1: Sept 7, 2025
        2: '20250914',   # Week 2: Sept 14, 2025
        3: '20250921',   # Week 3: Sept 21, 2025
        4: '20250928',   # Week 4: Sept 28, 2025
        5: '20251005',   # Week 5: Oct 5, 2025
        6: '20251012',   # Week 6: Oct 12, 2025
        7: '20251019',   # Week 7: Oct 19, 2025
        8: '20251026',   # Week 8: Oct 26, 2025
        9: '20251102',   # Week 9: Nov 2, 2025
        10: '20251109',  # Week 10: Nov 9, 2025
        11: '20251116',  # Week 11: Nov 16, 2025
        12: '20251123',  # Week 12: Nov 23, 2025
        13: '20251130',  # Week 13: Nov 30, 2025
        14: '20251207',  # Week 14: Dec 7, 2025
        15: '20251214',  # Week 15: Dec 14, 2025
        16: '20251221',  # Week 16: Dec 21, 2025
        17: '20251228',  # Week 17: Dec 28, 2025
        18: '20260104',  # Week 18: Jan 4, 2026
    }

    def __init__(self, season: int = 2025):
        """
        Initialize fetcher.

        Args:
            season: NFL season year (default: 2025)
        """
        self.season = season
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def normalize_team_abbrev(self, espn_abbrev: str) -> str:
        """
        Normalize ESPN team abbreviation to standard format.

        Args:
            espn_abbrev: ESPN team abbreviation

        Returns:
            Normalized 2-3 letter abbreviation
        """
        return self.TEAM_MAPPING.get(espn_abbrev.upper(), espn_abbrev.upper())

    def fetch_week_results(self, week: int, max_retries: int = 3) -> List[GameResult]:
        """
        Fetch all game results for a specific week.

        Args:
            week: NFL week number (1-18)
            max_retries: Maximum retry attempts for API calls

        Returns:
            List of GameResult objects
        """
        if week < 1 or week > 18:
            raise ValueError(f"Invalid week number: {week}. Must be 1-18.")

        # ESPN API parameters - use week and seasontype instead of dates
        params = {
            'seasontype': self.SEASON_TYPE_REGULAR,
            'week': week,
            'limit': 100
        }

        for attempt in range(max_retries):
            try:
                response = self.session.get(self.BASE_URL, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                games = self._parse_espn_response(data, week)
                print(f"✓ Fetched Week {week}: {len(games)} games")
                return games

            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"  Retry {attempt + 1}/{max_retries} after {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    print(f"✗ Failed to fetch Week {week} after {max_retries} attempts: {e}")
                    raise

        return []

    def _parse_espn_response(self, data: Dict, week: int) -> List[GameResult]:
        """
        Parse ESPN API response into GameResult objects.

        Args:
            data: ESPN API JSON response
            week: Week number

        Returns:
            List of GameResult objects
        """
        games = []

        if 'events' not in data:
            return games

        for event in data['events']:
            try:
                game_id = event['id']
                game_date = event.get('date', '')
                status = event.get('status', {})
                completed = status.get('type', {}).get('completed', False)

                competitions = event.get('competitions', [])
                if not competitions:
                    continue

                competition = competitions[0]
                competitors = competition.get('competitors', [])

                if len(competitors) != 2:
                    continue

                # ESPN returns home team first, away team second (usually)
                home_team = None
                away_team = None

                for competitor in competitors:
                    team_abbrev = competitor.get('team', {}).get('abbreviation', '')
                    team_abbrev = self.normalize_team_abbrev(team_abbrev)
                    score = int(competitor.get('score', 0))
                    is_home = competitor.get('homeAway') == 'home'

                    if is_home:
                        home_team = {'abbrev': team_abbrev, 'score': score}
                    else:
                        away_team = {'abbrev': team_abbrev, 'score': score}

                if not home_team or not away_team:
                    continue

                # Determine winner/loser
                if home_team['score'] > away_team['score']:
                    winner = home_team['abbrev']
                    loser = away_team['abbrev']
                elif away_team['score'] > home_team['score']:
                    winner = away_team['abbrev']
                    loser = home_team['abbrev']
                else:
                    # Tie game (rare in NFL, but possible in regular season before OT rule changes)
                    winner = 'TIE'
                    loser = 'TIE'

                game_result = GameResult(
                    game_id=game_id,
                    week=week,
                    season=self.season,
                    away_team=away_team['abbrev'],
                    home_team=home_team['abbrev'],
                    away_score=away_team['score'],
                    home_score=home_team['score'],
                    winner=winner,
                    loser=loser,
                    completed=completed,
                    game_date=game_date
                )

                games.append(game_result)

            except (KeyError, ValueError, TypeError) as e:
                print(f"  Warning: Failed to parse game {event.get('id', 'unknown')}: {e}")
                continue

        return games

    def fetch_multiple_weeks(self, weeks: List[int]) -> Dict[int, List[GameResult]]:
        """
        Fetch results for multiple weeks.

        Args:
            weeks: List of week numbers to fetch

        Returns:
            Dictionary mapping week number to list of GameResults
        """
        results = {}

        for week in weeks:
            try:
                week_games = self.fetch_week_results(week)
                results[week] = week_games
                time.sleep(0.5)  # Be nice to ESPN API
            except Exception as e:
                print(f"Error fetching week {week}: {e}")
                results[week] = []

        return results

    def save_results_to_json(self, results: Dict[int, List[GameResult]], output_dir: str = "out"):
        """
        Save game results to JSON files.

        Args:
            results: Dictionary of week -> GameResults
            output_dir: Output directory for JSON files
        """
        import os
        os.makedirs(output_dir, exist_ok=True)

        for week, games in results.items():
            filename = f"{output_dir}/week_{week}_game_results.json"

            data = {
                'week': week,
                'season': self.season,
                'num_games': len(games),
                'games': [asdict(game) for game in games]
            }

            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)

            print(f"✓ Saved Week {week} results to {filename}")


def fetch_game_results(weeks: List[int], season: int = 2025, save_json: bool = True) -> Dict[int, List[GameResult]]:
    """
    Convenience function to fetch game results for multiple weeks.

    Args:
        weeks: List of week numbers to fetch
        season: NFL season year
        save_json: Whether to save results to JSON files

    Returns:
        Dictionary mapping week number to list of GameResults
    """
    fetcher = NFLGameResultsFetcher(season=season)
    results = fetcher.fetch_multiple_weeks(weeks)

    if save_json:
        fetcher.save_results_to_json(results)

    return results


if __name__ == "__main__":
    print("=" * 60)
    print("NFL GAME RESULTS FETCHER - ESPN API")
    print("=" * 60)

    # Fetch Weeks 1-4 for 2025 season
    weeks_to_fetch = [1, 2, 3, 4]

    print(f"\nFetching game results for Weeks {weeks_to_fetch}...")
    print("-" * 60)

    results = fetch_game_results(weeks=weeks_to_fetch, season=2025)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for week, games in sorted(results.items()):
        print(f"\nWeek {week}: {len(games)} games")
        for game in games[:3]:  # Show first 3 games
            print(f"  {game.away_team} @ {game.home_team}: {game.away_score}-{game.home_score} (Winner: {game.winner})")
        if len(games) > 3:
            print(f"  ... and {len(games) - 3} more")
