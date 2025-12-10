"""
Win Scenario Analyzer for Confidence Pool.

Analyzes which combinations of remaining game outcomes would result in winning
the week, and calculates the probability of winning (assuming 50/50 game outcomes).

Usage:
    python app/win_scenario_analyzer.py --week 12 --player "Your Name"
    python app/win_scenario_analyzer.py --week 12 --player "Your Name" --detailed
"""

import argparse
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

from dotenv import load_dotenv
from supabase import create_client, Client


@dataclass
class Pick:
    """Represents a single player's pick for a game."""

    player_name: str
    team: str
    confidence_points: int
    is_correct: Optional[bool]
    opponent_team: Optional[str]


@dataclass
class PlayerScore:
    """Current and potential score for a player."""

    player_name: str
    current_points: int
    pending_picks: List[Pick]

    def calculate_total(self, outcome_map: Dict[str, bool]) -> int:
        """
        Calculate total points given outcomes for pending games.

        Args:
            outcome_map: Dict mapping team -> is_correct for pending games

        Returns:
            Total points if outcomes occur
        """
        total = self.current_points
        for pick in self.pending_picks:
            if pick.team in outcome_map and outcome_map[pick.team]:
                total += pick.confidence_points
        return total


class WinScenarioAnalyzer:
    """Analyzes win scenarios from Supabase data."""

    def __init__(self, supabase_url: str, supabase_key: str, season: int = None):
        """
        Initialize analyzer with Supabase connection.

        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase anon/service key
            season: NFL season year (default: current year)
        """
        self.client: Client = create_client(supabase_url, supabase_key)
        self.season = season or datetime.now().year
        self.picks_table = "player_picks"
        self.results_table = "player_results"

    def get_player_picks(self, week: int, player_name: Optional[str] = None) -> List[Pick]:
        """
        Get picks for a specific week, optionally filtered by player.

        Args:
            week: Week number
            player_name: Optional player name filter

        Returns:
            List of Pick objects
        """
        query = (
            self.client.table(self.picks_table)
            .select("*")
            .eq("season", self.season)
            .eq("week_number", week)
        )

        if player_name:
            query = query.eq("player_name", player_name)

        response = query.execute()

        picks = []
        for row in response.data:
            pick = Pick(
                player_name=row["player_name"],
                team=row["team"],
                confidence_points=row["confidence_points"],
                is_correct=row.get("is_correct"),
                opponent_team=row.get("opponent_team"),
            )
            picks.append(pick)

        return picks

    def get_player_scores(self, week: int) -> Dict[str, PlayerScore]:
        """
        Get current scores and pending picks for all players.

        Args:
            week: Week number

        Returns:
            Dict mapping player_name -> PlayerScore
        """
        all_picks = self.get_player_picks(week)

        # Group by player
        picks_by_player: Dict[str, List[Pick]] = {}
        for pick in all_picks:
            if pick.player_name not in picks_by_player:
                picks_by_player[pick.player_name] = []
            picks_by_player[pick.player_name].append(pick)

        # Calculate current scores and pending picks
        player_scores: Dict[str, PlayerScore] = {}

        for player_name, picks in picks_by_player.items():
            current_points = 0
            pending_picks = []

            for pick in picks:
                if pick.is_correct is True:
                    current_points += pick.confidence_points
                elif pick.is_correct is None:
                    pending_picks.append(pick)
                # is_correct = False contributes 0 points

            player_scores[player_name] = PlayerScore(
                player_name=player_name, current_points=current_points, pending_picks=pending_picks
            )

        return player_scores

    def get_pending_games(self, week: int) -> List[Tuple[str, str]]:
        """
        Get list of pending games (both teams involved).

        Args:
            week: Week number

        Returns:
            List of (team, opponent_team) tuples for pending games
        """
        all_picks = self.get_player_picks(week)

        pending_games: Set[Tuple[str, str]] = set()

        for pick in all_picks:
            if pick.is_correct is None and pick.opponent_team:
                # Store as sorted tuple to avoid duplicates
                game = tuple(sorted([pick.team, pick.opponent_team]))
                pending_games.add(game)

        return list(pending_games)

    def get_game_probabilities(self, week: int) -> Dict[Tuple[str, str], float]:
        """
        Get win probabilities for pending games from latest predictions.

        Args:
            week: Week number

        Returns:
            Dict mapping (team, opponent) -> probability that team wins
        """
        # Try to load from latest prediction files
        import glob
        import json

        output_dir = os.getenv("OUTPUT_DIR", "out")
        pattern = f"{output_dir}/week_{week}_predictions_chalk_*.json"
        files = glob.glob(pattern)

        if not files:
            # No prediction files, return empty dict (will use 50/50)
            return {}

        # Use most recent file
        latest_file = max(files, key=os.path.getmtime)

        try:
            with open(latest_file, "r") as f:
                predictions = json.load(f)

            probabilities = {}
            for game in predictions.get("games", []):
                favorite = game.get("favorite")
                dog = game.get("dog")
                fav_prob = game.get("favorite_prob", 0.5)

                if favorite and dog:
                    # Store probability for both perspectives
                    probabilities[(favorite, dog)] = fav_prob
                    probabilities[(dog, favorite)] = 1.0 - fav_prob

            return probabilities

        except Exception as e:
            print(f"Warning: Could not load game probabilities: {e}")
            return {}

    def analyze_win_scenarios(
        self,
        week: int,
        target_player: str,
        detailed: bool = False,
        use_actual_probabilities: bool = True,
    ) -> Dict:
        """
        Analyze all possible win scenarios for a player.

        Args:
            week: Week number
            target_player: Player name to analyze
            detailed: Whether to show detailed winning combinations
            use_actual_probabilities: Use real game odds vs 50/50 assumption

        Returns:
            Dictionary with analysis results
        """
        # Get all player scores
        player_scores = self.get_player_scores(week)

        if target_player not in player_scores:
            return {"error": f"Player '{target_player}' not found in week {week} data"}

        target_score = player_scores[target_player]
        other_scores = {
            name: score for name, score in player_scores.items() if name != target_player
        }

        # Get pending games
        pending_games = self.get_pending_games(week)

        # Get all teams involved in pending games
        pending_teams = set()
        for team1, team2 in pending_games:
            pending_teams.add(team1)
            pending_teams.add(team2)

        # Filter target's pending picks to only those in pending games
        relevant_pending_picks = [
            pick for pick in target_score.pending_picks if pick.team in pending_teams
        ]

        if not pending_games:
            # No pending games - winner is determined
            current_winner = max(player_scores.items(), key=lambda x: x[1].current_points)
            is_winning = current_winner[0] == target_player

            return {
                "week": week,
                "player": target_player,
                "current_points": target_score.current_points,
                "pending_games": 0,
                "total_scenarios": 1,
                "winning_scenarios": 1 if is_winning else 0,
                "win_probability": 1.0 if is_winning else 0.0,
                "status": "Week is complete",
                "current_winner": current_winner[0],
            }

        # Load game probabilities if available
        game_probabilities = {}
        if use_actual_probabilities:
            game_probabilities = self.get_game_probabilities(week)

        # Generate all possible outcomes (each game has 2 outcomes)
        num_scenarios = 2 ** len(pending_games)
        winning_scenarios = []
        weighted_win_probability = 0.0

        for outcome_idx in range(num_scenarios):
            # Create outcome map for this scenario
            outcome_map: Dict[str, bool] = {}

            # Calculate probability of this specific scenario occurring
            scenario_probability = 1.0

            for game_idx, (team1, team2) in enumerate(pending_games):
                # Use bit at position game_idx to determine winner
                team1_wins = bool(outcome_idx & (1 << game_idx))
                outcome_map[team1] = team1_wins
                outcome_map[team2] = not team1_wins

                # Calculate probability of this outcome
                if use_actual_probabilities and game_probabilities:
                    if team1_wins:
                        # team1 wins - look up its probability
                        prob = game_probabilities.get((team1, team2), 0.5)
                    else:
                        # team2 wins - look up its probability
                        prob = game_probabilities.get((team2, team1), 0.5)
                    scenario_probability *= prob
                else:
                    # 50/50 assumption
                    scenario_probability *= 0.5

            # Calculate target player's total
            target_total = target_score.calculate_total(outcome_map)

            # Calculate all other players' totals
            other_totals = {
                name: score.calculate_total(outcome_map) for name, score in other_scores.items()
            }

            # Check if target wins (ties count as losses)
            max_other_total = max(other_totals.values()) if other_totals else 0

            if target_total > max_other_total:
                winning_scenarios.append(
                    {
                        "outcome_map": outcome_map.copy(),
                        "target_total": target_total,
                        "max_opponent_total": max_other_total,
                        "probability": scenario_probability,
                    }
                )
                weighted_win_probability += scenario_probability

        # Naive probability (count-based, assumes 50/50)
        naive_win_probability = len(winning_scenarios) / num_scenarios if num_scenarios > 0 else 0.0

        # Format pending games with pick information
        pending_games_formatted = []
        for team1, team2 in sorted(pending_games):
            # Find which team (if any) the target player picked
            picked_team1 = any(pick.team == team1 for pick in relevant_pending_picks)
            picked_team2 = any(pick.team == team2 for pick in relevant_pending_picks)

            # Find confidence points for the picked team
            confidence = None
            if picked_team1:
                pick = next(p for p in relevant_pending_picks if p.team == team1)
                confidence = pick.confidence_points
                game_str = f"({team1} vs. {team2} - {team1})"
            elif picked_team2:
                pick = next(p for p in relevant_pending_picks if p.team == team2)
                confidence = pick.confidence_points
                game_str = f"({team1} vs. {team2} - {team2})"
            else:
                game_str = f"({team1} vs. {team2} - any)"

            if confidence:
                game_str += f" [{confidence} pts]"

            pending_games_formatted.append(game_str)

        # Determine which probability to use as primary
        primary_probability = (
            weighted_win_probability
            if (use_actual_probabilities and game_probabilities)
            else naive_win_probability
        )

        result = {
            "week": week,
            "season": self.season,
            "player": target_player,
            "current_points": target_score.current_points,
            "pending_games": len(pending_games),
            "pending_picks": len(relevant_pending_picks),
            "pending_games_formatted": pending_games_formatted,
            "total_scenarios": num_scenarios,
            "winning_scenarios": len(winning_scenarios),
            "win_probability": primary_probability,
            "win_percentage": f"{primary_probability * 100:.2f}%",
            "naive_win_probability": naive_win_probability,
            "naive_win_percentage": f"{naive_win_probability * 100:.2f}%",
            "weighted_win_probability": weighted_win_probability,
            "weighted_win_percentage": f"{weighted_win_probability * 100:.2f}%",
            "using_actual_odds": use_actual_probabilities and bool(game_probabilities),
        }

        if detailed and winning_scenarios:
            # Meta-analysis: Track how each game appears across ALL winning scenarios
            game_stats = {}  # game_str -> {'must_win': count, 'must_lose': count, 'any': count}

            # Process ALL winning scenarios for meta-analysis
            for scenario in winning_scenarios:
                processed_games = set()

                # Track picks
                for pick in relevant_pending_picks:
                    team = pick.team
                    opponent = pick.opponent_team

                    if not opponent:
                        continue

                    game_tuple = tuple(sorted([team, opponent]))
                    processed_games.add(game_tuple)

                    pick_wins = scenario["outcome_map"].get(team, False)
                    team1, team2 = sorted([team, opponent])
                    game_str = f"({team1} vs. {team2} - {team}) [{pick.confidence_points} pts]"

                    if game_str not in game_stats:
                        game_stats[game_str] = {
                            "must_win": 0,
                            "must_lose": 0,
                            "any": 0,
                            "confidence": pick.confidence_points,
                        }

                    if pick_wins:
                        game_stats[game_str]["must_win"] += 1
                    else:
                        game_stats[game_str]["must_lose"] += 1

                # Track unpicked games
                for team1, team2 in pending_games:
                    game_tuple = tuple(sorted([team1, team2]))
                    if game_tuple not in processed_games:
                        game_str = f"({team1} vs. {team2} - any)"
                        if game_str not in game_stats:
                            game_stats[game_str] = {
                                "must_win": 0,
                                "must_lose": 0,
                                "any": 0,
                                "confidence": 0,
                            }
                        game_stats[game_str]["any"] += 1

            # Generate meta-analysis summary
            total_winning_scenarios = len(winning_scenarios)
            meta_analysis = {
                "always_win": [],  # 100% of scenarios require win
                "usually_win": [],  # 75-99% require win
                "sometimes_win": [],  # 25-74% require win
                "rarely_win": [],  # 1-24% require win
                "always_lose": [],  # 100% require loss
                "usually_lose": [],  # 75-99% require loss
                "sometimes_lose": [],  # 25-74% require loss
                "rarely_lose": [],  # 1-24% require loss
                "always_any": [],  # 100% are "any"
            }

            for game_str, stats in game_stats.items():
                win_pct = (
                    (stats["must_win"] / total_winning_scenarios * 100)
                    if total_winning_scenarios > 0
                    else 0
                )
                lose_pct = (
                    (stats["must_lose"] / total_winning_scenarios * 100)
                    if total_winning_scenarios > 0
                    else 0
                )
                any_pct = (
                    (stats["any"] / total_winning_scenarios * 100)
                    if total_winning_scenarios > 0
                    else 0
                )

                game_info = {
                    "game": game_str,
                    "win_pct": win_pct,
                    "lose_pct": lose_pct,
                    "any_pct": any_pct,
                    "confidence": stats.get("confidence", 0),
                }

                # Categorize based on win percentage
                if win_pct == 100:
                    meta_analysis["always_win"].append(game_info)
                elif win_pct >= 75:
                    meta_analysis["usually_win"].append(game_info)
                elif win_pct >= 25:
                    meta_analysis["sometimes_win"].append(game_info)
                elif win_pct > 0:
                    meta_analysis["rarely_win"].append(game_info)

                # Categorize based on lose percentage
                if lose_pct == 100:
                    meta_analysis["always_lose"].append(game_info)
                elif lose_pct >= 75:
                    meta_analysis["usually_lose"].append(game_info)
                elif lose_pct >= 25:
                    meta_analysis["sometimes_lose"].append(game_info)
                elif lose_pct > 0:
                    meta_analysis["rarely_lose"].append(game_info)

                # Categorize "any" games
                if any_pct == 100:
                    meta_analysis["always_any"].append(game_info)

            # Sort each category by confidence points (descending)
            for category in meta_analysis.values():
                category.sort(key=lambda x: x["confidence"], reverse=True)

            result["meta_analysis"] = meta_analysis

            # Generate detailed winning combinations (first 20 only)
            result["winning_combinations"] = []
            for scenario in winning_scenarios[:20]:  # Limit to first 20
                # Build game outcomes categorized by result type
                must_win = []
                can_lose = []
                any_outcome = []

                # Track which games we've processed (to identify "any" games)
                processed_games = set()

                # Iterate through all picks to categorize outcomes
                for pick in relevant_pending_picks:
                    team = pick.team
                    opponent = pick.opponent_team

                    if not opponent:
                        continue

                    # Create sorted game tuple for tracking
                    game_tuple = tuple(sorted([team, opponent]))
                    processed_games.add(game_tuple)

                    # Check if this pick wins or loses in this scenario
                    pick_wins = scenario["outcome_map"].get(team, False)

                    # Format the game string
                    team1, team2 = sorted([team, opponent])
                    game_str = f"({team1} vs. {team2} - {team}) [{pick.confidence_points} pts]"

                    if pick_wins:
                        must_win.append(game_str)
                    else:
                        can_lose.append(game_str)

                # Find games where you have no pick (any outcome)
                for team1, team2 in pending_games:
                    game_tuple = tuple(sorted([team1, team2]))
                    if game_tuple not in processed_games:
                        game_str = f"({team1} vs. {team2} - any)"
                        any_outcome.append(game_str)

                # Sort all lists for consistency
                must_win.sort()
                can_lose.sort()
                any_outcome.sort()

                combo = {
                    "target_total": scenario["target_total"],
                    "max_opponent_total": scenario["max_opponent_total"],
                    "must_win": must_win,
                    "can_lose": can_lose,
                    "any_outcome": any_outcome,
                }
                result["winning_combinations"].append(combo)

            if len(winning_scenarios) > 20:
                result["winning_combinations_note"] = (
                    f"Showing 20 of {len(winning_scenarios)} winning combinations"
                )

        return result

    def analyze_all_players_leaderboard(self, week: int) -> Dict:
        """
        Analyze win scenarios for ALL players and return leaderboard.

        Args:
            week: Week number

        Returns:
            Dictionary with leaderboard and metadata
        """
        # Get all player scores
        player_scores = self.get_player_scores(week)

        if not player_scores:
            return {"error": f"No players found in week {week} data"}

        # Get pending games for metadata
        pending_games = self.get_pending_games(week)

        # Analyze each player
        leaderboard = []

        print(f"Analyzing {len(player_scores)} players...")
        for idx, player_name in enumerate(sorted(player_scores.keys()), 1):
            print(f"  [{idx}/{len(player_scores)}] {player_name}...", end="\r")

            # Run lightweight analysis (no detailed scenarios)
            result = self.analyze_win_scenarios(
                week=week, target_player=player_name, detailed=False
            )

            if "error" not in result:
                leaderboard.append(
                    {
                        "player": player_name,
                        "current_points": result["current_points"],
                        "pending_picks": result["pending_picks"],
                        "total_scenarios": result["total_scenarios"],
                        "winning_scenarios": result["winning_scenarios"],
                        "win_probability": result["win_probability"],
                        "win_percentage": result["win_percentage"],
                    }
                )

        print()  # Clear progress line

        # Sort by win probability (descending)
        leaderboard.sort(key=lambda x: x["win_probability"], reverse=True)

        return {
            "week": week,
            "season": self.season,
            "pending_games": len(pending_games),
            "total_players": len(leaderboard),
            "leaderboard": leaderboard,
        }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Analyze win scenarios for confidence pool")
    parser.add_argument("--week", type=int, required=True, help="Week number to analyze")
    parser.add_argument(
        "--player", type=str, help="Player name to analyze (defaults to USER_NAME from .env)"
    )
    parser.add_argument(
        "--detailed", action="store_true", help="Show detailed winning combinations"
    )
    parser.add_argument(
        "--all-players",
        action="store_true",
        help="Analyze all players and show leaderboard (ignores --player flag)",
    )
    parser.add_argument("--season", type=int, help="Season year (defaults to current year)")

    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_KEY must be set in .env file")
        sys.exit(1)

    # Create analyzer
    analyzer = WinScenarioAnalyzer(
        supabase_url=supabase_url, supabase_key=supabase_key, season=args.season
    )

    # Handle all-players mode
    if args.all_players:
        result = analyzer.analyze_all_players_leaderboard(week=args.week)

        if "error" in result:
            print(f"Error: {result['error']}")
            sys.exit(1)

        # Display leaderboard
        print("=" * 70)
        print(f"WIN PROBABILITY LEADERBOARD - Week {result['week']}")
        print("=" * 70)
        print(f"Season: {result['season']}")
        print(f"Pending Games: {result['pending_games']}")
        print(f"Total Players: {result['total_players']}")
        print()
        print(f"{'Rank':<6}{'Player':<25}{'Current':<10}{'Win Scenarios':<20}{'Probability':<12}")
        print("-" * 70)

        for idx, entry in enumerate(result["leaderboard"], 1):
            scenarios = f"{entry['winning_scenarios']:,} / {entry['total_scenarios']:,}"
            print(
                f"{idx:<6}{entry['player']:<25}{entry['current_points']:<10}{scenarios:<20}{entry['win_percentage']:<12}"
            )

        print("=" * 70)
        sys.exit(0)

    # Single-player mode
    player_name = args.player or os.getenv("USER_NAME")
    if not player_name:
        print("Error: --player must be specified or USER_NAME must be set in .env")
        sys.exit(1)

    # Run analysis
    result = analyzer.analyze_win_scenarios(
        week=args.week, target_player=player_name, detailed=args.detailed
    )

    # Display results
    if "error" in result:
        print(f"Error: {result['error']}")
        sys.exit(1)

    print("=" * 60)
    print(f"WIN SCENARIO ANALYSIS - Week {result['week']}")
    print("=" * 60)
    print(f"Player: {result['player']}")
    print(f"Current Points: {result['current_points']}")
    print()

    # Display pending games with formatted picks
    if "pending_games_formatted" in result and result["pending_games_formatted"]:
        print(f"Remaining Games ({result['pending_games']}):")
        for game in result["pending_games_formatted"]:
            print(f"  {game}")
        print()

    print(f"Total Possible Scenarios: {result['total_scenarios']:,}")
    print(f"Winning Scenarios: {result['winning_scenarios']:,}")
    print()

    # Display probability metrics
    if result.get("using_actual_odds"):
        print(f"Win Probability (Weighted by Odds): {result['weighted_win_percentage']}")
        print(f"Win Probability (Naive 50/50):      {result['naive_win_percentage']}")
        print()
        print("NOTE: Using actual game probabilities from odds data")
    else:
        print(f"Win Probability (50/50 Assumption): {result['win_percentage']}")
        print()
        print("NOTE: Assuming all games are 50/50 coin flips")

    print("=" * 60)

    if args.detailed and "winning_combinations" in result:
        print()
        print("SAMPLE WINNING COMBINATIONS:")
        print("-" * 60)
        for idx, combo in enumerate(result["winning_combinations"], 1):
            print(
                f"\n#{idx}: You score {combo['target_total']} pts, opponents max {combo['max_opponent_total']} pts"
            )

            if combo["must_win"]:
                print("  Must win:")
                for win in combo["must_win"]:
                    print(f"    - {win}")

            if combo["can_lose"]:
                print("  Must lose:")
                for loss in combo["can_lose"]:
                    print(f"    - {loss}")

            if combo["any_outcome"]:
                print("  Any outcome:")
                for any_game in combo["any_outcome"]:
                    print(f"    - {any_game}")

        if "winning_combinations_note" in result:
            print(f"\n{result['winning_combinations_note']}")

        print("-" * 60)

    # Display meta-analysis TL;DR
    if args.detailed and "meta_analysis" in result:
        meta = result["meta_analysis"]
        print()
        print("=" * 60)
        print("TL;DR - META-ANALYSIS ACROSS ALL WINNING SCENARIOS")
        print("=" * 60)
        print()

        # Critical wins
        if meta["always_win"]:
            print("🎯 CRITICAL - Must ALWAYS win these:")
            for game_info in meta["always_win"]:
                print(f"   {game_info['game']} (100% of winning scenarios)")
            print()

        if meta["usually_win"]:
            print("⭐ IMPORTANT - Should win these (75%+):")
            for game_info in meta["usually_win"]:
                print(f"   {game_info['game']} ({game_info['win_pct']:.0f}% need win)")
            print()

        # Critical losses
        if meta["always_lose"]:
            print("❌ CRITICAL - Must ALWAYS lose these:")
            for game_info in meta["always_lose"]:
                print(f"   {game_info['game']} (100% of winning scenarios)")
            print()

        if meta["usually_lose"]:
            print("⚠️  IMPORTANT - Should lose these (75%+):")
            for game_info in meta["usually_lose"]:
                print(f"   {game_info['game']} ({game_info['lose_pct']:.0f}% need loss)")
            print()

        # Variable outcomes
        if meta["sometimes_win"] or meta["sometimes_lose"]:
            print("🔀 VARIABLE - Mixed outcomes:")
            # Combine and show win/lose percentages
            variable_games = {}
            for game_info in meta["sometimes_win"] + meta["sometimes_lose"]:
                game = game_info["game"]
                if game not in variable_games:
                    variable_games[game] = game_info

            for game, info in variable_games.items():
                if info["win_pct"] > 0 and info["lose_pct"] > 0:
                    print(f"   {game}")
                    print(f"      Win: {info['win_pct']:.0f}% | Lose: {info['lose_pct']:.0f}%")
            print()

        # Irrelevant games
        if meta["always_any"]:
            print("💤 IRRELEVANT - Outcome doesn't matter:")
            for game_info in meta["always_any"]:
                print(f"   {game_info['game']}")
            print()

        print("=" * 60)


if __name__ == "__main__":
    main()
