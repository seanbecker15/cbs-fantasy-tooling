"""Win Scenario Analyzer for Confidence Pool.

Analyzes which combinations of remaining game outcomes would result in winning
the week, and calculates the probability of winning.
"""

import glob
import json
import os
from dataclasses import dataclass

import squarify
from matplotlib import pyplot as plt
from supabase import Client, create_client

from cbs_fantasy_tooling.analysis.core.config import SHARP_BOOKS, SHARP_WEIGHT
from cbs_fantasy_tooling.analysis.odds.converter import (
    consensus_moneyline_probs,
    rows_to_game_probs,
)
from cbs_fantasy_tooling.analysis.team_normalization import normalize_team_name
from cbs_fantasy_tooling.config import config
from cbs_fantasy_tooling.ingest.the_odds_api.api import fetch_odds
from cbs_fantasy_tooling.publishers.file import CHART_FILENAMES
from cbs_fantasy_tooling.utils.date import get_commence_time_from, get_commence_time_to


@dataclass
class Pick:
    """Represents a single player's pick for a game."""

    player_name: str
    team: str
    confidence_points: int
    is_correct: bool | None
    opponent_team: str | None


@dataclass
class PlayerScore:
    """Current and potential score for a player."""

    player_name: str
    current_points: int
    pending_picks: list[Pick]

    def calculate_total(self, outcome_map: dict[str, bool]) -> int:
        """Calculate total points given outcomes for pending games."""
        total = self.current_points
        for pick in self.pending_picks:
            if outcome_map.get(pick.team):
                total += pick.confidence_points
        return total


class WinScenarioAnalyzer:
    """Analyzes win scenarios from Supabase data."""

    def __init__(self, client: Client, season: int):
        self.client = client
        self.season = season

    def get_player_picks(self, week: int, player_name: str | None = None) -> list[Pick]:
        """Get picks for a specific week, optionally filtered by player."""
        query = (
            self.client.table("player_picks")
            .select("*")
            .eq("season", self.season)
            .eq("week_number", week)
        )

        if player_name:
            query = query.eq("player_name", player_name)

        response = query.execute()
        return [
            Pick(
                player_name=row["player_name"],
                team=row["team"],
                confidence_points=row["confidence_points"],
                is_correct=row.get("is_correct"),
                opponent_team=row.get("opponent_team"),
            )
            for row in response.data
        ]

    def get_player_scores(self, week: int) -> dict[str, PlayerScore]:
        """Get current scores and pending picks for all players."""
        all_picks = self.get_player_picks(week)

        # Group by player
        picks_by_player: dict[str, list[Pick]] = {}
        for pick in all_picks:
            picks_by_player.setdefault(pick.player_name, []).append(pick)

        # Calculate current scores and pending picks
        player_scores = {}
        for player_name, picks in picks_by_player.items():
            current_points = sum(p.confidence_points for p in picks if p.is_correct is True)
            pending_picks = [p for p in picks if p.is_correct is None]

            player_scores[player_name] = PlayerScore(
                player_name=player_name,
                current_points=current_points,
                pending_picks=pending_picks,
            )

        return player_scores

    def get_pending_games(self, week: int) -> list[tuple[str, str]]:
        """Get list of pending games (both teams involved)."""
        all_picks = self.get_player_picks(week)

        pending_games: set[tuple[str, str]] = set()
        for pick in all_picks:
            if pick.is_correct is None and pick.opponent_team:
                # Store as sorted tuple to avoid duplicates
                game = tuple(sorted([pick.team, pick.opponent_team]))
                pending_games.add(game)

        return list(pending_games)

    def get_game_probabilities(self, week: int) -> dict[tuple[str, str], float]:
        """Get win probabilities for pending games from latest predictions."""
        pattern = f"{config.output_dir}/week_{week}_predictions_chalk_*.json"
        files = glob.glob(pattern)

        if not files:
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
                    probabilities[(favorite, dog)] = fav_prob
                    probabilities[(dog, favorite)] = 1.0 - fav_prob

            return probabilities
        except Exception as e:
            print(f"Warning: Could not load game probabilities: {e}")
            return {}

    def _build_game_probabilities_from_odds(
        self, pending_games: list[tuple[str, str]]
    ) -> dict[tuple[str, str], float]:
        """Fetch odds once and build a team-pair -> win prob map, normalized to pending teams."""
        try:
            events = fetch_odds(get_commence_time_from(), get_commence_time_to())
            rows = consensus_moneyline_probs(events, SHARP_BOOKS, SHARP_WEIGHT)
            _, mapping = rows_to_game_probs(rows)
            # Build available teams from pending games (abbreviations)
            available_teams = list({team for game in pending_games for team in game})
            game_probs: dict[tuple[str, str], float] = {}
            matched = 0
            mismatched = 0
            for m in mapping:
                try:
                    fav = normalize_team_name(m["favorite"], available_teams)
                    dog = normalize_team_name(m["dog"], available_teams)
                except Exception as e:
                    print(f"Warning: could not normalize teams from odds data: {e}")
                    mismatched += 1
                    continue
                p = m["p_fav"]
                game_probs[(fav, dog)] = p
                game_probs[(dog, fav)] = 1.0 - p
                matched += 1

            print(
                f"Odds coverage: matched {matched} games from odds feed; mismatched={mismatched}; pending_games={len(pending_games)}"
            )
            return game_probs
        except Exception as e:
            print(f"Warning: could not fetch odds-based probabilities: {e}")
            return {}

    def analyze_win_scenarios(
        self,
        week: int,
        target_player: str,
        detailed: bool = False,
        game_probabilities: dict[tuple[str, str], float] | None = None,
        use_actual_probabilities: bool = True,
    ) -> dict:
        """Analyze all possible win scenarios for a player."""
        player_scores = self.get_player_scores(week)

        if target_player not in player_scores:
            return {"error": f"Player '{target_player}' not found in week {week} data"}

        target_score = player_scores[target_player]
        other_scores = {k: v for k, v in player_scores.items() if k != target_player}

        pending_games = self.get_pending_games(week)
        pending_teams = {team for game in pending_games for team in game}

        # Filter target's pending picks to only those in pending games
        relevant_picks = [p for p in target_score.pending_picks if p.team in pending_teams]

        # Handle case where all games are complete
        if not pending_games:
            winner = max(player_scores.items(), key=lambda x: x[1].current_points)
            is_winning = winner[0] == target_player
            return {
                "week": week,
                "player": target_player,
                "current_points": target_score.current_points,
                "pending_games": 0,
                "total_scenarios": 1,
                "winning_scenarios": 1 if is_winning else 0,
                "win_probability": 1.0 if is_winning else 0.0,
                "status": "Week is complete",
                "current_winner": winner[0],
            }

        # Load game probabilities
        if game_probabilities is not None:
            game_probs = game_probabilities
        elif use_actual_probabilities:
            game_probs = self.get_game_probabilities(week)
        else:
            game_probs = {}

        # Generate all possible outcomes
        num_scenarios = 2 ** len(pending_games)
        winning_scenarios = []
        weighted_win_prob = 0.0
        target_player_picks = self.get_player_picks(week, target_player)

        for outcome_idx in range(num_scenarios):
            outcome_map: dict[str, bool] = {}
            scenario_prob = 1.0

            for game_idx, (team1, team2) in enumerate(pending_games):
                team1_wins = bool(outcome_idx & (1 << game_idx))
                outcome_map[team1] = team1_wins
                outcome_map[team2] = not team1_wins

                # Calculate probability of this outcome
                if game_probs:
                    prob = (
                        game_probs.get((team1, team2), 0.5)
                        if team1_wins
                        else game_probs.get((team2, team1), 0.5)
                    )
                    scenario_prob *= prob
                else:
                    scenario_prob *= 0.5

            # Calculate scores
            target_total = target_score.calculate_total(outcome_map)
            max_other = max(
                (score.calculate_total(outcome_map) for score in other_scores.values()),
                default=0,
            )

            # Check if target wins (ties count as losses)
            if target_total > max_other:
                winning_scenarios.append(
                    {
                        "outcome_map": outcome_map.copy(),
                        "target_total": target_total,
                        "max_opponent_total": max_other,
                        "probability": scenario_prob,
                    }
                )
                weighted_win_prob += scenario_prob

        naive_win_prob = len(winning_scenarios) / num_scenarios if num_scenarios > 0 else 0.0
        primary_prob = weighted_win_prob if game_probs else naive_win_prob

        # Format pending games
        pending_games_formatted = []
        for team1, team2 in sorted(pending_games):
            pick = next((p for p in relevant_picks if p.team in (team1, team2)), None)
            if pick:
                game_str = f"({team1} vs. {team2} - {pick.team}) [{pick.confidence_points} pts]"
            else:
                game_str = f"({team1} vs. {team2} - any)"
            pending_games_formatted.append(game_str)

        # Build per-game status for target player
        game_statuses = []
        for pick in sorted(
            target_player_picks,
            key=lambda p: p.confidence_points if p.confidence_points else 0,
            reverse=True,
        ):
            status = "Pending"
            if pick.is_correct is True:
                status = "Win"
            elif pick.is_correct is False:
                status = "Loss"
            game_statuses.append(
                {
                    "team": pick.team,
                    "opponent": pick.opponent_team,
                    "confidence": pick.confidence_points,
                    "status": status,
                }
            )

        result = {
            "week": week,
            "season": self.season,
            "player": target_player,
            "current_points": target_score.current_points,
            "pending_games": len(pending_games),
            "pending_picks": len(relevant_picks),
            "pending_games_formatted": pending_games_formatted,
            "total_scenarios": num_scenarios,
            "winning_scenarios": len(winning_scenarios),
            "win_probability": primary_prob,
            "win_percentage": f"{primary_prob * 100:.2f}%",
            "using_actual_odds": bool(game_probs),
            "game_statuses": game_statuses,
        }

        if detailed and winning_scenarios:
            result["winning_combinations"] = self._build_winning_combinations(
                winning_scenarios[:20], relevant_picks, pending_games
            )
            if len(winning_scenarios) > 20:
                result["note"] = f"Showing 20 of {len(winning_scenarios)} winning combinations"

            result["meta_analysis"] = self._build_meta_analysis(
                winning_scenarios, relevant_picks, pending_games
            )

        return result

    def _build_winning_combinations(
        self,
        scenarios: list[dict],
        relevant_picks: list[Pick],
        pending_games: list[tuple[str, str]],
    ) -> list[dict]:
        """Build detailed winning combinations."""
        combinations = []
        for scenario in scenarios:
            must_win = []
            can_lose = []
            any_outcome = []
            processed_games = set()

            for pick in relevant_picks:
                if not pick.opponent_team:
                    continue

                game_tuple = tuple(sorted([pick.team, pick.opponent_team]))
                processed_games.add(game_tuple)
                pick_wins = scenario["outcome_map"].get(pick.team, False)

                team1, team2 = sorted([pick.team, pick.opponent_team])
                game_str = f"({team1} vs. {team2} - {pick.team}) [{pick.confidence_points} pts]"

                if pick_wins:
                    must_win.append(game_str)
                else:
                    can_lose.append(game_str)

            # Find unpicked games
            for team1, team2 in pending_games:
                game_tuple = tuple(sorted([team1, team2]))
                if game_tuple not in processed_games:
                    any_outcome.append(f"({team1} vs. {team2} - any)")

            combinations.append(
                {
                    "target_total": scenario["target_total"],
                    "max_opponent_total": scenario["max_opponent_total"],
                    "must_win": sorted(must_win),
                    "can_lose": sorted(can_lose),
                    "any_outcome": sorted(any_outcome),
                }
            )

        return combinations

    def _build_meta_analysis(
        self,
        scenarios: list[dict],
        relevant_picks: list[Pick],
        pending_games: list[tuple[str, str]],
    ) -> dict:
        """Build meta-analysis showing game criticality across all winning scenarios."""
        game_stats = {}
        total_scenarios = len(scenarios)

        for scenario in scenarios:
            processed_games = set()

            # Track picks
            for pick in relevant_picks:
                if not pick.opponent_team:
                    continue

                game_tuple = tuple(sorted([pick.team, pick.opponent_team]))
                processed_games.add(game_tuple)
                pick_wins = scenario["outcome_map"].get(pick.team, False)

                team1, team2 = sorted([pick.team, pick.opponent_team])
                game_str = f"({team1} vs. {team2} - {pick.team}) [{pick.confidence_points} pts]"

                if game_str not in game_stats:
                    game_stats[game_str] = {
                        "must_win": 0,
                        "must_lose": 0,
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
                        game_stats[game_str] = {"must_win": 0, "must_lose": 0, "confidence": 0}

        # Categorize games
        categories = {
            "always_win": [],
            "usually_win": [],
            "sometimes_win": [],
            "always_lose": [],
            "usually_lose": [],
            "irrelevant": [],
        }

        for game_str, stats in game_stats.items():
            win_pct = (stats["must_win"] / total_scenarios * 100) if total_scenarios > 0 else 0
            lose_pct = (stats["must_lose"] / total_scenarios * 100) if total_scenarios > 0 else 0

            game_info = {
                "game": game_str,
                "win_pct": win_pct,
                "lose_pct": lose_pct,
                "confidence": stats["confidence"],
            }

            if win_pct == 100:
                categories["always_win"].append(game_info)
            elif win_pct >= 75:
                categories["usually_win"].append(game_info)
            elif win_pct >= 25:
                categories["sometimes_win"].append(game_info)
            elif lose_pct == 100:
                categories["always_lose"].append(game_info)
            elif lose_pct >= 75:
                categories["usually_lose"].append(game_info)
            else:
                categories["irrelevant"].append(game_info)

        # Sort by confidence
        for category in categories.values():
            category.sort(key=lambda x: x["confidence"], reverse=True)

        return categories

    def analyze_leaderboard(self, week: int) -> dict:
        """Analyze win scenarios for all players and return leaderboard."""
        player_scores = self.get_player_scores(week)
        if not player_scores:
            return {"error": f"No players found in week {week} data"}

        pending_games = self.get_pending_games(week)
        leaderboard_naive = []
        leaderboard_odds = []

        # Fetch odds-based probabilities once (if available)
        odds_probs = (
            self._build_game_probabilities_from_odds(pending_games) if pending_games else {}
        )

        print(f"Analyzing {len(player_scores)} players...")
        for idx, player_name in enumerate(sorted(player_scores.keys()), 1):
            print(f"  [{idx}/{len(player_scores)}] {player_name}...", end="\r")

            result_naive = self.analyze_win_scenarios(
                week=week, target_player=player_name, use_actual_probabilities=False
            )
            if "error" not in result_naive:
                leaderboard_naive.append(
                    {
                        "player": player_name,
                        "current_points": result_naive["current_points"],
                        "pending_picks": result_naive["pending_picks"],
                        "total_scenarios": result_naive["total_scenarios"],
                        "winning_scenarios": result_naive["winning_scenarios"],
                        "win_probability": result_naive["win_probability"],
                        "win_percentage": result_naive["win_percentage"],
                    }
                )

            if odds_probs:
                result_odds = self.analyze_win_scenarios(
                    week=week,
                    target_player=player_name,
                    game_probabilities=odds_probs,
                    use_actual_probabilities=True,
                )
                if "error" not in result_odds:
                    leaderboard_odds.append(
                        {
                            "player": player_name,
                            "win_probability": result_odds["win_probability"],
                            "win_percentage": result_odds["win_percentage"],
                        }
                    )

        print()  # Clear progress line
        leaderboard_naive.sort(key=lambda x: x["win_probability"], reverse=True)
        leaderboard_odds.sort(key=lambda x: x["win_probability"], reverse=True)

        return {
            "week": week,
            "season": self.season,
            "pending_games": len(pending_games),
            "pending_games_list": pending_games,
            "total_players": len(leaderboard_naive),
            "leaderboard": leaderboard_naive,
            "leaderboard_odds": leaderboard_odds,
        }


def _save_win_leaderboard_chart(result: dict) -> str | None:
    """Save win probability charts (50/50 and odds-based if available)."""
    leaderboard_naive = result.get("leaderboard", [])
    leaderboard_odds = result.get("leaderboard_odds", [])

    if not leaderboard_naive:
        return None

    def _sanitize(label: str) -> str:
        return label.replace("$", r"\$")

    def _collapse_small(entries: list[dict]) -> list[dict]:
        """Group players with <=1% win probability into a single 'Other' bucket."""
        main = []
        other_prob = 0.0
        for entry in entries:
            prob = entry["win_probability"]
            if prob <= 0.01:
                other_prob += prob
            else:
                main.append(entry)
        if other_prob > 0:
            main.append(
                {
                    "player": "Other",
                    "win_probability": other_prob,
                    "win_percentage": f"{other_prob*100:.2f}%",
                }
            )
        return sorted(main, key=lambda x: x["win_probability"], reverse=True)

    def _treemap(ax, players, probs, title):
        labels = [f"{p}\n{prob:.1f}%" for p, prob in zip(players[::-1], probs[::-1])]
        sizes = probs[::-1]
        cmap = plt.cm.Blues
        vmin = min(sizes) if sizes else 0
        vmax = max(sizes) if sizes else 1
        norm = plt.Normalize(vmin=vmin, vmax=vmax)
        colors = [cmap(norm(s)) for s in sizes]
        squarify.plot(
            sizes=sizes,
            label=labels,
            color=colors,
            alpha=0.8,
            text_kwargs={"fontsize": 9},
            ax=ax,
        )
        ax.axis("off")
        ax.set_title(title, fontsize=12)

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    plt.subplots_adjust(wspace=0.1)

    # 50/50 treemap
    collapsed_naive = _collapse_small(leaderboard_naive)
    players_naive = [_sanitize(entry["player"]) for entry in collapsed_naive][::-1]
    probs_naive = [entry["win_probability"] * 100 for entry in collapsed_naive][::-1]
    _treemap(
        axes[0],
        players_naive,
        probs_naive,
        f"Win Outcome Probability (50/50 pending games) — Week {result['week']}",
    )

    if leaderboard_odds:
        collapsed_odds = _collapse_small(leaderboard_odds)
        players_odds = [_sanitize(entry["player"]) for entry in collapsed_odds][::-1]
        probs_odds = [entry["win_probability"] * 100 for entry in collapsed_odds][::-1]
        _treemap(
            axes[1],
            players_odds,
            probs_odds,
            f"Win Outcome Probability (Odds-weighted) — Week {result['week']}",
        )
    else:
        axes[1].axis("off")
        axes[1].text(
            0.5,
            0.5,
            "Odds data unavailable",
            ha="center",
            va="center",
            fontsize=12,
        )

    # Pending games status text box
    pending_games = result.get("pending_games_list", [])
    if pending_games:
        games_text = "\n".join([f"{a} vs {b}" for a, b in pending_games])
    else:
        games_text = "No pending games listed."
    fig.text(
        0.99,
        0.02,
        f"Pending Games:\n{games_text}",
        ha="right",
        va="bottom",
        fontsize=9,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.7),
    )

    plt.tight_layout()

    filename = CHART_FILENAMES["win_leaderboard"](result["week"])
    os.makedirs(config.output_dir, exist_ok=True)
    chart_path = os.path.join(config.output_dir, filename)
    plt.savefig(chart_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return chart_path


def analyze_win_scenarios(week: int, player_name: str, detailed: bool = False):
    """Analyze win scenarios for a player.

    Args:
        week: Week number to analyze
        player_name: Player name
        detailed: Show detailed winning combinations
    """
    assert player_name, "player_name must be provided"
    assert config.validate_database_config(), "SUPABASE_URL and SUPABASE_KEY must be set in .env"

    client = create_client(config.supabase_url, config.supabase_key)
    analyzer = WinScenarioAnalyzer(client=client, season=config.season)

    result = analyzer.analyze_win_scenarios(week=week, target_player=player_name, detailed=detailed)

    if "error" in result:
        print(f"Error: {result['error']}")
        return

    # Display results
    print("=" * 60)
    print(f"WIN SCENARIO ANALYSIS - Week {result['week']}")
    print("=" * 60)
    print(f"Player: {result['player']}")
    print(f"Current Points: {result['current_points']}")
    print()

    if result.get("pending_games_formatted"):
        print(f"Remaining Games ({result['pending_games']}):")
        for game in result["pending_games_formatted"]:
            print(f"  {game}")
        print()

    print(f"Total Possible Scenarios: {result['total_scenarios']:,}")
    print(f"Winning Scenarios: {result['winning_scenarios']:,}")
    print(f"Win Probability: {result['win_percentage']}")
    print()

    if result.get("game_statuses"):
        print("GAME STATUS (your picks):")
        for gs in result["game_statuses"]:
            print(
                f"  {gs['team']} vs {gs['opponent']} | Conf: {gs['confidence']} | Status: {gs['status']}"
            )
        print()

    if result.get("using_actual_odds"):
        print("NOTE: Using actual game probabilities from odds data")
    else:
        print("NOTE: Assuming all games are 50/50 coin flips")

    print("=" * 60)

    # Display detailed analysis
    if detailed and "winning_combinations" in result:
        print("\nSAMPLE WINNING COMBINATIONS:")
        print("-" * 60)
        for idx, combo in enumerate(result["winning_combinations"], 1):
            print(
                f"\n#{idx}: You score {combo['target_total']} pts, "
                f"opponents max {combo['max_opponent_total']} pts"
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

        if "note" in result:
            print(f"\n{result['note']}")
        print("-" * 60)

    # Display meta-analysis
    if detailed and "meta_analysis" in result:
        meta = result["meta_analysis"]
        print("\n" + "=" * 60)
        print("META-ANALYSIS - GAME CRITICALITY")
        print("=" * 60)
        print()

        if meta["always_win"]:
            print("🎯 CRITICAL - Must ALWAYS win these:")
            for g in meta["always_win"]:
                print(f"   {g['game']} (100% of winning scenarios)")
            print()

        if meta["usually_win"]:
            print("⭐ IMPORTANT - Should win these (75%+):")
            for g in meta["usually_win"]:
                print(f"   {g['game']} ({g['win_pct']:.0f}% need win)")
            print()

        if meta["always_lose"]:
            print("❌ CRITICAL - Must ALWAYS lose these:")
            for g in meta["always_lose"]:
                print(f"   {g['game']} (100% of winning scenarios)")
            print()

        if meta["usually_lose"]:
            print("⚠️  IMPORTANT - Should lose these (75%+):")
            for g in meta["usually_lose"]:
                print(f"   {g['game']} ({g['lose_pct']:.0f}% need loss)")
            print()

        if meta["sometimes_win"]:
            print("🔀 VARIABLE - Mixed outcomes:")
            for g in meta["sometimes_win"]:
                print(f"   {g['game']}")
                print(f"      Win: {g['win_pct']:.0f}% | Lose: {g['lose_pct']:.0f}%")
            print()

        if meta["irrelevant"]:
            print("💤 IRRELEVANT - Outcome doesn't matter:")
            for g in meta["irrelevant"]:
                print(f"   {g['game']}")
            print()

        print("=" * 60)


def analyze_win_leaderboard(week: int):
    """Analyze win scenarios for all players and show leaderboard.

    Args:
        week: Week number to analyze
    """
    assert config.validate_database_config(), "SUPABASE_URL and SUPABASE_KEY must be set in .env"

    client = create_client(config.supabase_url, config.supabase_key)
    analyzer = WinScenarioAnalyzer(client=client, season=config.season)

    result = analyzer.analyze_leaderboard(week=week)

    if "error" in result:
        print(f"Error: {result['error']}")
        return

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
            f"{idx:<6}{entry['player']:<25}{entry['current_points']:<10}"
            f"{scenarios:<20}{entry['win_percentage']:<12}"
        )

    chart_path = _save_win_leaderboard_chart(result)
    if chart_path:
        print(f"\nLeaderboard chart saved to: {chart_path}")

    print("=" * 70)
