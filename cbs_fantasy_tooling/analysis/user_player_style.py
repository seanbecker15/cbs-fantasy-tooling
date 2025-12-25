"""Player contrarian/aggressiveness style over the season."""

import glob
import json
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import ticker

from cbs_fantasy_tooling.config import config
from cbs_fantasy_tooling.analysis.data.loader import CompetitorDataLoader
from cbs_fantasy_tooling.publishers.file import CHART_FILENAMES, JSON_FILENAMES


def _slugify(name: str) -> str:
    return "".join(c.lower() if c.isalnum() else "_" for c in name).strip("_") or "player"


def _load_game_winners(data_dir: str) -> dict[int, dict[str, bool]]:
    """Build a lookup of winning/losing teams per week to tag pick correctness."""
    winners_by_week: dict[int, dict[str, bool]] = {}
    pattern = os.path.join(data_dir, JSON_FILENAMES["game_results"]("*"))

    for path in glob.glob(pattern):
        try:
            with open(path, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            continue

        week = data.get("week")
        week_map: dict[str, bool] = {}
        for game in data.get("games", []):
            winning_team = game.get("winning_team")
            losing_team = game.get("losing_team")
            if winning_team:
                week_map[winning_team] = True
            if losing_team:
                week_map[losing_team] = False

        if week is not None and week_map:
            winners_by_week[week] = week_map

    return winners_by_week


def _compute_player_weekly_profiles(
    players: list[str] | None,
    data_dir: str,
    game_winners: dict[int, dict[str, bool]],
    contrarian_threshold: float,
):
    """
    Compute weekly aggressiveness/contrarian profiles. If players is None, returns all players.
    """
    loader = CompetitorDataLoader(data_dir=data_dir)
    picks_df, _, _ = loader.load_and_build_all()

    weeks = sorted(picks_df["week"].unique())
    records = []

    for week in weeks:
        week_picks = picks_df[picks_df["week"] == week].copy()
        winners_map = game_winners.get(week, {})
        if winners_map:
            week_picks["is_correct"] = week_picks["team"].map(winners_map)
            week_picks["is_correct"] = week_picks["is_correct"].where(
                week_picks["is_correct"].notna(), None
            )
        else:
            week_picks["is_correct"] = None
        consensus = loader.get_field_consensus(week=week)
        week_picks = week_picks.merge(
            consensus[["team", "pick_percentage"]], on="team", how="left"
        )
        week_picks["pick_percentage"] = week_picks["pick_percentage"].fillna(0)
        week_picks["risk"] = 1 - week_picks["pick_percentage"]
        week_picks["pick_aggressiveness"] = week_picks["risk"] * week_picks["confidence"]

        for player in week_picks["player_name"].unique():
            if players and player not in players:
                continue

            player_picks = week_picks[week_picks["player_name"] == player].copy()
            total_aggr = player_picks["pick_aggressiveness"].sum()
            avg_aggr = player_picks["pick_aggressiveness"].mean()
            leverage = player_picks["risk"].mean()

            top4 = player_picks.nlargest(4, "confidence")
            chalk = (top4["pick_percentage"] >= 0.6).sum()
            contrarian = (top4["pick_percentage"] <= contrarian_threshold).sum()

            wins = player_picks["total_player_wins"].iloc[0]
            losses = player_picks["total_player_losses"].iloc[0]
            total_games = wins + losses
            win_pct = wins / total_games if total_games else 0

            contrarian_mask = player_picks["pick_percentage"] <= contrarian_threshold
            contrarian_share = contrarian_mask.mean()
            contrarian_points = player_picks.loc[contrarian_mask, "confidence"].sum()
            contrarian_attempts = contrarian_mask.sum()
            contrarian_wins = player_picks.loc[
                contrarian_mask & (player_picks["is_correct"] == True)
            ]
            contrarian_win_count = len(contrarian_wins)
            contrarian_win_rate = contrarian_win_count / contrarian_attempts if contrarian_attempts else 0
            total_conf_points = player_picks["confidence"].sum()

            records.append(
                {
                    "week": week,
                    "player": player,
                    "total_aggr": total_aggr,
                    "avg_aggr": avg_aggr,
                    "leverage": leverage,
                    "win_pct": win_pct,
                    "chalk_top4": chalk,
                    "contrarian_top4": contrarian,
                    "contrarian_share": contrarian_share,
                    "contrarian_points": contrarian_points,
                    "contrarian_attempts": contrarian_attempts,
                    "contrarian_wins": contrarian_win_count,
                    "contrarian_win_rate": contrarian_win_rate,
                    "total_conf_points": total_conf_points,
                }
            )

    profile_df = pd.DataFrame(records)
    return profile_df, weeks


def analyze_player_style(players: list[str] | None = None, contrarian_pct: float = 40):
    """
    Generate static charts for player aggressiveness/contrarian style across the season.

    If multiple players are provided, charts only include those players.
    If a single player (or None) is provided, include league median/IQR band on aggressiveness.
    """
    data_dir = config.output_dir
    output_dir = config.output_dir
    threshold = contrarian_pct / 100.0
    threshold_text = f"≤ {contrarian_pct:.0f}%"

    # Compute full league profiles for baselines
    game_winners = _load_game_winners(data_dir)
    profile_all, weeks = _compute_player_weekly_profiles(None, data_dir, game_winners, threshold)
    if profile_all.empty:
        print("No player/week data found for the requested players.")
        return None

    # Filter to requested players (if provided)
    if players:
        profile_df = profile_all[profile_all["player"].isin(players)].copy()
    else:
        profile_df = profile_all.copy()

    if profile_df.empty:
        print("No player/week data found for the requested players.")
        return None

    all_players = profile_df["player"].unique().tolist()
    if players:
        focus_players = [p for p in players if p in all_players]
    else:
        focus_players = all_players

    if not focus_players:
        print("No matching players found for the requested list.")
        return None

    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    plt.subplots_adjust(hspace=0.35, wspace=0.25)

    # Aggressiveness delta vs league median (more contrast than raw totals)
    ax = axes[0, 0]
    league_stats = (
        profile_all.groupby("week")["total_aggr"]
        .agg(["median", lambda x: np.percentile(x, 25), lambda x: np.percentile(x, 75)])
        .reset_index()
    )
    league_stats.columns = ["week", "median", "p25", "p75"]
    league_median_map = dict(zip(league_stats["week"], league_stats["median"]))
    ax.axhline(0, color="gray", linestyle="--", alpha=0.6, linewidth=1)
    ax.fill_between(
        league_stats["week"], league_stats["p25"] - league_stats["median"], league_stats["p75"] - league_stats["median"],
        color="#e0e0e0", alpha=0.6, label="League IQR (vs median)"
    )
    colors = plt.cm.tab20.colors
    for idx, player in enumerate(focus_players):
        data = profile_df[profile_df["player"] == player].sort_values("week")
        delta = [row["total_aggr"] - league_median_map.get(row["week"], 0) for _, row in data.iterrows()]
        ax.plot(data["week"], delta, marker="o", label=player, color=colors[idx % 20])

    ax.set_title("Aggressiveness vs League Median (Δ Risk×Conf)")
    ax.set_xlabel("Week")
    ax.set_ylabel("Aggressiveness Δ vs Median")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)

    # Contrarian pick value per week (sum of confidence points on contrarian picks)
    ax = axes[0, 1]
    # League baseline from full profile
    league_points = (
        profile_all.groupby("week")["contrarian_points"]
        .agg(["median", lambda x: np.percentile(x, 25), lambda x: np.percentile(x, 75)])
        .reset_index()
    )
    league_points.columns = ["week", "median", "p25", "p75"]
    ax.fill_between(
        league_points["week"],
        league_points["p25"],
        league_points["p75"],
        color="#e0e0e0",
        alpha=0.5,
        label="League IQR",
    )
    ax.plot(
        league_points["week"],
        league_points["median"],
        color="gray",
        linestyle="--",
        label="League Median",
    )
    for idx, player in enumerate(focus_players):
        data = profile_df[profile_df["player"] == player].sort_values("week")
        ax.plot(
            data["week"],
            data["contrarian_points"],
            marker="o",
            label=player,
            color=colors[idx % 20],
        )
    ax.set_title(f"Contrarian Pick Value per Week (≤ {contrarian_pct:.0f}% field share)")
    ax.set_xlabel("Week")
    ax.set_ylabel("Points on Contrarian Picks")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)

    # Leverage vs Outcome scatter
    ax = axes[1, 0]
    for idx, player in enumerate(focus_players):
        data = profile_df[profile_df["player"] == player]
        ax.scatter(
            data["leverage"] * 100,
            data["win_pct"] * 100,
            label=player,
            s=60,
            alpha=0.8,
            color=colors[idx % 20],
            edgecolors="black",
        )
        # Annotate each point with week number for clarity
        for _, row in data.iterrows():
            ax.annotate(
                int(row["week"]),
                (row["leverage"] * 100, row["win_pct"] * 100),
                textcoords="offset points",
                xytext=(4, 4),
                ha="left",
                fontsize=7,
                color="dimgray",
            )
    ax.set_xlabel("Average Leverage (% off field)")
    ax.set_ylabel("Weekly Win%")
    ax.set_title("Leverage vs Outcome by Week")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)

    # Contrarian share per week
    ax = axes[1, 1]
    for idx, player in enumerate(focus_players):
        data = profile_df[profile_df["player"] == player].sort_values("week")
        ax.plot(
            data["week"],
            data["contrarian_share"] * 100,
            marker="o",
            label=player,
            color=colors[idx % 20],
        )
    ax.set_title("Contrarian Pick Share per Week")
    ax.set_xlabel("Week")
    ax.set_ylabel("Contrarian Picks (% of card)")
    ax.set_ylim(0, 100)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)

    plt.tight_layout()
    suffix = "multi_players" if len(focus_players) > 1 else _slugify(focus_players[0])
    output_file = os.path.join(output_dir, CHART_FILENAMES["player_style"](suffix))
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close()

    # Upset-focused charts
    fig2 = plt.figure(figsize=(20, 8))
    gs = fig2.add_gridspec(2, 2, height_ratios=[1, 1], hspace=0.35, wspace=0.25)
    ax_top_left = fig2.add_subplot(gs[0, 0])
    ax_top_right = fig2.add_subplot(gs[0, 1])
    ax_bottom = fig2.add_subplot(gs[1, :])

    # Contrarian wins per week (count) with league band
    ax = ax_top_left
    league_contr_wins = (
        profile_all.groupby("week")["contrarian_wins"]
        .agg(["median", lambda x: np.percentile(x, 25), lambda x: np.percentile(x, 75)])
        .reset_index()
    )
    league_contr_wins.columns = ["week", "median", "p25", "p75"]
    ax.fill_between(
        league_contr_wins["week"], league_contr_wins["p25"], league_contr_wins["p75"], color="#e0e0e0", alpha=0.6, label="League IQR"
    )
    ax.plot(
        league_contr_wins["week"],
        league_contr_wins["median"],
        color="gray",
        linestyle="--",
        label="League Median",
    )
    for idx, player in enumerate(focus_players):
        data = profile_df[profile_df["player"] == player].sort_values("week")
        ax.plot(
            data["week"],
            data["contrarian_wins"],
            marker="o",
            label=player,
            color=colors[idx % 20],
        )
    ax.set_title(f"Contrarian Wins per Week (Field {threshold_text})")
    ax.set_xlabel("Week")
    ax.set_ylabel("Contrarian Wins")
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)

    # Season contrarian wins (count) with win rate annotation
    ax = ax_top_right
    season_contr = (
        profile_df.groupby("player")[["contrarian_wins", "contrarian_attempts"]]
        .sum()
        .reindex(focus_players)
    )
    season_contr["win_rate"] = season_contr.apply(
        lambda r: (r["contrarian_wins"] / r["contrarian_attempts"]) if r["contrarian_attempts"] else 0,
        axis=1,
    )
    ax.barh(season_contr.index, season_contr["contrarian_wins"], color="#f16913")
    for y, (wins, attempts, rate) in enumerate(
        zip(season_contr["contrarian_wins"], season_contr["contrarian_attempts"], season_contr["win_rate"])
    ):
        ax.text(
            wins + 0.2,
            y,
            f"{wins} / {attempts} ({rate*100:.1f}%)",
            va="center",
            fontsize=9,
        )
    ax.set_title(f"Season Contrarian Wins (Field {threshold_text})")
    ax.set_xlabel("Contrarian Wins")
    ax.grid(axis="x", alpha=0.3)

    # Season contrarian points wagered with % of total points annotation
    ax = ax_bottom
    season_points = (
        profile_df.groupby("player")[["contrarian_points", "total_conf_points"]]
        .sum()
        .reindex(focus_players)
    )
    season_points["pct_of_points"] = season_points.apply(
        lambda r: (r["contrarian_points"] / r["total_conf_points"]) if r["total_conf_points"] else 0,
        axis=1,
    )
    ax.barh(season_points.index, season_points["contrarian_points"], color="#6baed6")
    for y, (pts, pct) in enumerate(zip(season_points["contrarian_points"], season_points["pct_of_points"])):
        ax.text(
            pts + 0.3,
            y,
            f"{pts:.0f} ({pct*100:.1f}%)",
            va="center",
            fontsize=9,
        )
    ax.set_title("Contrarian Points Wagered (Season)")
    ax.set_xlabel("Confidence Points on Contrarian Picks")
    ax.grid(axis="x", alpha=0.3)

    upset_file = os.path.join(output_dir, CHART_FILENAMES["player_upset"](suffix))
    plt.savefig(upset_file, dpi=300, bbox_inches="tight")
    plt.close()

    # Team-level contrarian charts (single PNG with three panels)
    loader_team = CompetitorDataLoader(data_dir=data_dir)
    picks_df_team, _, _ = loader_team.load_and_build_all()
    team_records = []
    weeks_team = sorted(picks_df_team["week"].unique())
    for week in weeks_team:
        week_picks = picks_df_team[picks_df_team["week"] == week].copy()
        winners_map = game_winners.get(week, {})
        if winners_map:
            week_picks["is_correct"] = week_picks["team"].map(winners_map)
            week_picks["is_correct"] = week_picks["is_correct"].where(
                week_picks["is_correct"].notna(), None
            )
        else:
            week_picks["is_correct"] = None
        consensus = loader_team.get_field_consensus(week=week)
        week_picks = week_picks.merge(
            consensus[["team", "pick_percentage"]], on="team", how="left"
        )
        week_picks["pick_percentage"] = week_picks["pick_percentage"].fillna(0)
        week_picks["contrarian"] = week_picks["pick_percentage"] <= threshold
        week_picks["contrarian_win"] = week_picks["contrarian"] & (
            week_picks["is_correct"] == True
        )
        week_picks["contrarian_loss"] = week_picks["contrarian"] & (
            week_picks["is_correct"] == False
        )
        week_picks["contrarian_points"] = week_picks.apply(
            lambda r: r["confidence"] if r["contrarian"] else 0, axis=1
        )
        week_picks["contrarian_points_win"] = week_picks.apply(
            lambda r: r["confidence"] if r["contrarian_win"] else 0, axis=1
        )
        week_picks["contrarian_points_loss"] = week_picks.apply(
            lambda r: r["confidence"] if r["contrarian_loss"] else 0, axis=1
        )

        grouped = (
            week_picks.groupby("team")
            .agg(
                contrarian_attempts=("contrarian", "sum"),
                contrarian_wins=("contrarian_win", "sum"),
                contrarian_losses=("contrarian_loss", "sum"),
                contrarian_points=("contrarian_points", "sum"),
                contrarian_points_win=("contrarian_points_win", "sum"),
                contrarian_points_loss=("contrarian_points_loss", "sum"),
                total_conf_points=("confidence", "sum"),
            )
            .reset_index()
        )
        grouped["week"] = week
        team_records.append(grouped)

    if team_records:
        team_week_df = pd.concat(team_records, ignore_index=True)
        season_team = (
            team_week_df.groupby("team")[
                [
                    "contrarian_wins",
                    "contrarian_losses",
                    "contrarian_attempts",
                    "contrarian_points",
                    "contrarian_points_win",
                    "contrarian_points_loss",
                    "total_conf_points",
                ]
            ]
            .sum()
            .reset_index()
        )
        top_teams = (
            season_team.sort_values(["contrarian_wins", "contrarian_points"], ascending=False)
            .head(10)
        )
        focus_teams = top_teams["team"].tolist()

        fig3 = plt.figure(figsize=(20, 8))
        gs3 = fig3.add_gridspec(2, 2, height_ratios=[1, 1], hspace=0.35, wspace=0.25)
        ax_tl = fig3.add_subplot(gs3[0, 0])
        ax_tr = fig3.add_subplot(gs3[0, 1])
        ax_bottom = fig3.add_subplot(gs3[1, :])

        # Team contrarian wins per week
        for idx, team in enumerate(focus_teams):
            data = team_week_df[team_week_df["team"] == team].sort_values("week")
            ax_tl.plot(
                data["week"],
                data["contrarian_wins"],
                marker="o",
                label=team,
                color=colors[idx % 20],
            )
        ax_tl.set_title(f"Team Contrarian Wins per Week (Field {threshold_text})")
        ax_tl.set_xlabel("Week")
        ax_tl.set_ylabel("Contrarian Wins")
        ax_tl.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax_tl.grid(alpha=0.3)
        ax_tl.legend(fontsize=8)

        # Season team contrarian wins
        season_team = season_team.set_index("team").loc[focus_teams]
        season_team["win_rate"] = season_team.apply(
            lambda r: (r["contrarian_wins"] / r["contrarian_attempts"]) if r["contrarian_attempts"] else 0,
            axis=1,
        )
        ax_tr.barh(season_team.index, season_team["contrarian_wins"], color="#f16913")
        for y, (wins, attempts, rate) in enumerate(
            zip(season_team["contrarian_wins"], season_team["contrarian_attempts"], season_team["win_rate"])
        ):
            ax_tr.text(
                wins + 0.2,
                y,
                f"{wins} / {attempts} ({rate*100:.1f}%)",
                va="center",
                fontsize=9,
            )
        ax_tr.set_title(f"Team Contrarian Wins (Season, {threshold_text})")
        ax_tr.set_xlabel("Contrarian Wins")
        ax_tr.grid(axis="x", alpha=0.3)

        # Season team contrarian points
        season_team["pct_of_points"] = season_team.apply(
            lambda r: (r["contrarian_points"] / r["total_conf_points"]) if r["total_conf_points"] else 0,
            axis=1,
        )
        ax_bottom.barh(season_team.index, season_team["contrarian_points"], color="#6baed6")
        for y, (pts, pct) in enumerate(
            zip(season_team["contrarian_points"], season_team["pct_of_points"])
        ):
            ax_bottom.text(
                pts + 0.3,
                y,
                f"{pts:.0f} ({pct*100:.1f}%)",
                va="center",
                fontsize=9,
            )
        ax_bottom.set_title("Team Contrarian Points Wagered (Season)")
        ax_bottom.set_xlabel("Confidence Points on Contrarian Picks")
        ax_bottom.grid(axis="x", alpha=0.3)

        team_file = os.path.join(output_dir, CHART_FILENAMES["team_contrarian_wins"]("league"))
        plt.savefig(team_file, dpi=300, bbox_inches="tight")
        plt.close()
        print(f"✓ Team contrarian analysis saved to: {team_file}")

        # Team contrarian losses figure (mirror of wins)
        focus_losses = (
            season_team.sort_values(["contrarian_losses", "contrarian_points_loss"], ascending=False)
            .head(10)
            .index.tolist()
        )
        fig4 = plt.figure(figsize=(20, 8))
        gs4 = fig4.add_gridspec(2, 2, height_ratios=[1, 1], hspace=0.35, wspace=0.25)
        ax4_tl = fig4.add_subplot(gs4[0, 0])
        ax4_tr = fig4.add_subplot(gs4[0, 1])
        ax4_bottom = fig4.add_subplot(gs4[1, :])

        # Losses per week
        for idx, team in enumerate(focus_losses):
            data = team_week_df[team_week_df["team"] == team].sort_values("week")
            data["contrarian_losses"] = data["contrarian_attempts"] - data["contrarian_wins"]
            ax4_tl.plot(
                data["week"],
                data["contrarian_losses"],
                marker="o",
                label=team,
                color=colors[idx % 20],
            )
        ax4_tl.set_title(f"Team Contrarian Losses per Week (Field {threshold_text})")
        ax4_tl.set_xlabel("Week")
        ax4_tl.set_ylabel("Contrarian Losses")
        ax4_tl.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax4_tl.grid(alpha=0.3)
        ax4_tl.legend(fontsize=8)

        # Season losses
        season_losses = season_team.loc[focus_losses]
        season_losses["loss_rate"] = season_losses.apply(
            lambda r: (r["contrarian_losses"] / r["contrarian_attempts"]) if r["contrarian_attempts"] else 0,
            axis=1,
        )
        ax4_tr.barh(season_losses.index, season_losses["contrarian_losses"], color="#cb181d")
        for y, (losses, attempts, rate) in enumerate(
            zip(season_losses["contrarian_losses"], season_losses["contrarian_attempts"], season_losses["loss_rate"])
        ):
            ax4_tr.text(
                losses + 0.2,
                y,
                f"{losses} / {attempts} ({rate*100:.1f}%)",
                va="center",
                fontsize=9,
            )
        ax4_tr.set_title(f"Team Contrarian Losses (Season, {threshold_text})")
        ax4_tr.set_xlabel("Contrarian Losses")
        ax4_tr.grid(axis="x", alpha=0.3)

        # Season contrarian points on losses
        season_losses["pct_of_points_loss"] = season_losses.apply(
            lambda r: (r["contrarian_points_loss"] / r["total_conf_points"]) if r["total_conf_points"] else 0,
            axis=1,
        )
        ax4_bottom.barh(season_losses.index, season_losses["contrarian_points_loss"], color="#fb6a4a")
        for y, (pts, pct) in enumerate(
            zip(season_losses["contrarian_points_loss"], season_losses["pct_of_points_loss"])
        ):
            ax4_bottom.text(
                pts + 0.3,
                y,
                f"{pts:.0f} ({pct*100:.1f}%)",
                va="center",
                fontsize=9,
            )
        ax4_bottom.set_title("Contrarian Points Lost (Season)")
        ax4_bottom.set_xlabel("Confidence Points on Losing Contrarian Picks")
        ax4_bottom.grid(axis="x", alpha=0.3)

        team_loss_file = os.path.join(output_dir, CHART_FILENAMES["team_contrarian_losses"]("league"))
        plt.savefig(team_loss_file, dpi=300, bbox_inches="tight")
        plt.close()
        print(f"✓ Team contrarian losses analysis saved to: {team_loss_file}")

    print(f"✓ Player style report saved to: {output_file}")
    print(f"✓ Upset analysis saved to: {upset_file}")
    return output_file
