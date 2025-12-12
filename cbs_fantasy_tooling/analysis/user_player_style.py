"""Player contrarian/aggressiveness style over the season."""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from cbs_fantasy_tooling.config import config
from cbs_fantasy_tooling.analysis.data.loader import CompetitorDataLoader
from cbs_fantasy_tooling.publishers.file import CHART_FILENAMES


def _slugify(name: str) -> str:
    return "".join(c.lower() if c.isalnum() else "_" for c in name).strip("_") or "player"


def _compute_player_weekly_profiles(players: list[str] | None, data_dir: str):
    """
    Compute weekly aggressiveness/contrarian profiles. If players is None, returns all players.
    """
    loader = CompetitorDataLoader(data_dir=data_dir)
    picks_df, _, _ = loader.load_and_build_all()

    weeks = sorted(picks_df["week"].unique())
    records = []

    for week in weeks:
        week_picks = picks_df[picks_df["week"] == week].copy()
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
            contrarian = (top4["pick_percentage"] <= 0.4).sum()

            wins = player_picks["total_player_wins"].iloc[0]
            losses = player_picks["total_player_losses"].iloc[0]
            total_games = wins + losses
            win_pct = wins / total_games if total_games else 0

            contrarian_share = (player_picks["pick_percentage"] <= 0.4).mean()
            contrarian_points = player_picks.loc[player_picks["pick_percentage"] <= 0.4, "confidence"].sum()

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
                }
            )

    profile_df = pd.DataFrame(records)
    return profile_df, weeks


def analyze_player_style(players: list[str] | None = None):
    """
    Generate static charts for player aggressiveness/contrarian style across the season.

    If multiple players are provided, charts only include those players.
    If a single player (or None) is provided, include league median/IQR band on aggressiveness.
    """
    data_dir = config.output_dir
    output_dir = config.output_dir

    # Compute full league profiles for baselines
    profile_all, weeks = _compute_player_weekly_profiles(None, data_dir)
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
    ax.set_title("Contrarian Pick Value per Week (Confidence Points)")
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
    print(f"✓ Player style report saved to: {output_file}")
    return output_file
