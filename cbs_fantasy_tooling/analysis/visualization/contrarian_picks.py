"""
Player Aggressiveness Rankings Chart Generator

Analyzes and visualizes player pick aggressiveness using the Risk×Confidence metric:
  Aggressiveness = (1 - Field%) × Confidence

Where:
  - Field% = Percentage of league that picked the same team
  - Confidence = Player's confidence level (1-14) on that pick
  - Higher score = More aggressive (higher risk, higher confidence commitment)

"""

import sys
import os
import glob

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib

from cbs_fantasy_tooling.config import config
from cbs_fantasy_tooling.analysis.data.loader import CompetitorDataLoader

# ============================================================================
# WEEK UTILITIES
# ============================================================================


def check_week_data_exists(week: int, data_dir: str = "../out") -> bool:
    """
    Check if picks data exists for the specified week.

    Args:
        week: NFL week number
        data_dir: Directory containing week result files

    Returns:
        True if data exists, False otherwise
    """
    pattern = os.path.join(data_dir, f"week_{week}_results_*.json")
    files = glob.glob(pattern)
    return len(files) > 0


def get_scraper_command(week: int) -> str:
    """
    Get the command to run the scraper for a specific week.

    Args:
        week: NFL week number

    Returns:
        Command string to run scraper
    """
    return f"cd ../app && python main.py --week {week}"


# ============================================================================
# DATA PROCESSING
# ============================================================================


def calculate_aggressiveness_metrics(week: int, data_dir: str = "../out") -> pd.DataFrame:
    """
    Calculate Risk×Conf aggressiveness metrics for all players in a given week.

    Args:
        week: NFL week number
        data_dir: Directory containing week result files

    Returns:
        DataFrame with player-level aggressiveness metrics
    """
    # Load data
    loader = CompetitorDataLoader(data_dir=data_dir)
    picks_df, _, _ = loader.load_and_build_all()

    # Filter for specified week
    week_picks = picks_df[picks_df["week"] == week].copy()

    if len(week_picks) == 0:
        raise ValueError(f"No picks found for week {week}")

    # Get field consensus
    consensus = loader.get_field_consensus(week=week)

    # Merge picks with field consensus
    week_picks = week_picks.merge(consensus[["team", "pick_percentage"]], on="team", how="left")

    # Calculate Risk×Conf metric for each pick
    week_picks["risk"] = 1 - week_picks["pick_percentage"]
    week_picks["pick_aggressiveness"] = week_picks["risk"] * week_picks["confidence"]

    # Calculate player-level metrics
    player_metrics = []

    for player in week_picks["player_name"].unique():
        player_picks = week_picks[week_picks["player_name"] == player].copy()

        # Total aggressiveness across all picks
        total_aggressiveness = player_picks["pick_aggressiveness"].sum()

        # Average aggressiveness per pick
        avg_aggressiveness = player_picks["pick_aggressiveness"].mean()

        # Max single pick aggressiveness (boldest move)
        max_pick_aggr = player_picks["pick_aggressiveness"].max()
        boldest_pick = player_picks.loc[player_picks["pick_aggressiveness"].idxmax()]

        # Contrarian picks (field < 50%)
        contrarian = player_picks[player_picks["pick_percentage"] < 0.5]
        num_contrarian = len(contrarian)

        # High-risk picks (field < 30%)
        high_risk = player_picks[player_picks["pick_percentage"] < 0.3]
        num_high_risk = len(high_risk)

        player_metrics.append(
            {
                "player_name": player,
                "total_aggressiveness": total_aggressiveness,
                "avg_aggressiveness": avg_aggressiveness,
                "max_pick_aggressiveness": max_pick_aggr,
                "boldest_team": boldest_pick["team"],
                "boldest_confidence": boldest_pick["confidence"],
                "boldest_field_pct": boldest_pick["pick_percentage"],
                "num_contrarian": num_contrarian,
                "num_high_risk": num_high_risk,
                "total_points": player_picks["total_player_points"].iloc[0],
                "total_wins": player_picks["total_player_wins"].iloc[0],
            }
        )

    return pd.DataFrame(player_metrics).sort_values("total_aggressiveness", ascending=False)


# ============================================================================
# VISUALIZATION
# ============================================================================


def create_chart(metrics_df: pd.DataFrame, week: int, output_dir: str = "../out") -> str:
    """
    Create comprehensive aggressiveness visualization chart.

    Args:
        metrics_df: DataFrame with player aggressiveness metrics
        week: NFL week number
        output_dir: Directory to save chart

    Returns:
        Path to saved chart file
    """
    # Disable mathtext to avoid issues with special characters
    matplotlib.rcParams["text.usetex"] = False

    # Escape special characters in player names
    metrics_df = metrics_df.copy()
    metrics_df["player_name"] = metrics_df["player_name"].str.replace("$", r"\$", regex=False)

    # Sort by total aggressiveness
    metrics_df = metrics_df.sort_values("total_aggressiveness", ascending=True)

    # Create comprehensive visualization
    fig = plt.figure(figsize=(20, 14))
    gs = fig.add_gridspec(3, 2, hspace=0.35, wspace=0.3)

    # Color map based on total aggressiveness
    norm = plt.Normalize(
        vmin=metrics_df["total_aggressiveness"].min(), vmax=metrics_df["total_aggressiveness"].max()
    )
    colors = plt.cm.RdYlGn_r(norm(metrics_df["total_aggressiveness"]))

    # ========== CHART 1: Total Aggressiveness Ranking ==========
    ax1 = fig.add_subplot(gs[0, :])
    ax1.barh(range(len(metrics_df)), metrics_df["total_aggressiveness"], color=colors)
    ax1.set_yticks(range(len(metrics_df)))
    ax1.set_yticklabels(metrics_df["player_name"], fontsize=8)
    ax1.set_xlabel("Total Aggressiveness Score (Risk×Conf)", fontsize=12, fontweight="bold")
    ax1.set_title(
        f"Week {week} Aggressiveness Rankings - Risk×Conf Metric\n"
        f"Formula: Σ(1 - Field%) × Confidence across all 14 picks",
        fontsize=14,
        fontweight="bold",
        pad=15,
    )
    ax1.grid(axis="x", alpha=0.3)
    ax1.set_xlim(0, metrics_df["total_aggressiveness"].max() * 1.15)

    # Add value labels
    for i, (_, row) in enumerate(metrics_df.iterrows()):
        ax1.text(
            row["total_aggressiveness"] + 0.3,
            i,
            f"{row['total_aggressiveness']:.1f}",
            va="center",
            fontsize=7,
        )

    # ========== CHART 2: Boldest Individual Picks ==========
    ax2 = fig.add_subplot(gs[1, 0])

    top_boldest = metrics_df.nlargest(15, "max_pick_aggressiveness").copy()
    top_boldest = top_boldest.sort_values("max_pick_aggressiveness", ascending=True)

    top_boldest["pick_label"] = top_boldest.apply(
        lambda x: f"{x['boldest_team']}({int(x['boldest_confidence'])})@{x['boldest_field_pct']*100:.0f}%",
        axis=1,
    )
    top_boldest["player_pick"] = top_boldest["player_name"] + ": " + top_boldest["pick_label"]

    colors_boldest = plt.cm.Reds(norm(top_boldest["max_pick_aggressiveness"]))
    ax2.barh(range(len(top_boldest)), top_boldest["max_pick_aggressiveness"], color=colors_boldest)
    ax2.set_yticks(range(len(top_boldest)))
    ax2.set_yticklabels(top_boldest["player_pick"], fontsize=8)
    ax2.set_xlabel("Single Pick Aggressiveness", fontsize=11, fontweight="bold")
    ax2.set_title(
        "Top 15 Boldest Individual Picks\n(Team(Confidence)@Field%)",
        fontsize=12,
        fontweight="bold",
        pad=10,
    )
    ax2.grid(axis="x", alpha=0.3)

    for i, (_, row) in enumerate(top_boldest.iterrows()):
        ax2.text(
            row["max_pick_aggressiveness"] + 0.1,
            i,
            f"{row['max_pick_aggressiveness']:.2f}",
            va="center",
            fontsize=7,
        )

    # ========== CHART 3: Strategy Scatter ==========
    ax3 = fig.add_subplot(gs[1, 1])

    scatter = ax3.scatter(
        metrics_df["avg_aggressiveness"],
        metrics_df["max_pick_aggressiveness"],
        s=metrics_df["num_contrarian"] * 150 + 100,
        c=metrics_df["total_aggressiveness"],
        cmap="RdYlGn_r",
        alpha=0.6,
        edgecolors="black",
        linewidth=1.5,
    )

    # Annotate top 5 most aggressive
    top5 = metrics_df.nlargest(5, "total_aggressiveness")
    for _, row in top5.iterrows():
        ax3.annotate(
            row["player_name"],
            (row["avg_aggressiveness"], row["max_pick_aggressiveness"]),
            fontsize=8,
            fontweight="bold",
            xytext=(8, 8),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.5),
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.2", lw=1),
        )

    ax3.set_xlabel("Average Aggressiveness Per Pick", fontsize=11, fontweight="bold")
    ax3.set_ylabel("Boldest Single Pick", fontsize=11, fontweight="bold")
    ax3.set_title(
        "Strategy Profile: Consistent vs Bold\n(Bubble size = # Contrarian Picks)",
        fontsize=12,
        fontweight="bold",
        pad=10,
    )
    ax3.grid(alpha=0.3)

    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax3)
    cbar.set_label("Total Aggressiveness", fontsize=9, fontweight="bold")

    # Add quadrant lines
    median_avg = metrics_df["avg_aggressiveness"].median()
    median_max = metrics_df["max_pick_aggressiveness"].median()
    ax3.axvline(median_avg, color="gray", linestyle="--", alpha=0.3, linewidth=1)
    ax3.axhline(median_max, color="gray", linestyle="--", alpha=0.3, linewidth=1)

    # Add quadrant labels
    ax3.text(
        ax3.get_xlim()[1] * 0.95,
        ax3.get_ylim()[1] * 0.95,
        "Bold + Consistent",
        fontsize=9,
        ha="right",
        va="top",
        bbox=dict(boxstyle="round", facecolor="lightcoral", alpha=0.3),
    )
    ax3.text(
        ax3.get_xlim()[0] * 1.05,
        ax3.get_ylim()[0] * 1.05,
        "Conservative",
        fontsize=9,
        ha="left",
        va="bottom",
        bbox=dict(boxstyle="round", facecolor="lightgreen", alpha=0.3),
    )

    # ========== CHART 4: Distribution Histogram ==========
    ax4 = fig.add_subplot(gs[2, 0])

    ax4.hist(
        metrics_df["total_aggressiveness"],
        bins=12,
        edgecolor="black",
        linewidth=1.2,
        color="steelblue",
    )

    ax4.set_xlabel("Total Aggressiveness Score", fontsize=11, fontweight="bold")
    ax4.set_ylabel("Number of Players", fontsize=11, fontweight="bold")
    ax4.set_title("Distribution of Total Aggressiveness", fontsize=12, fontweight="bold", pad=10)
    ax4.grid(axis="y", alpha=0.3)

    # Add mean and median lines
    mean_val = metrics_df["total_aggressiveness"].mean()
    median_val = metrics_df["total_aggressiveness"].median()
    ax4.axvline(mean_val, color="red", linestyle="--", linewidth=2, label=f"Mean: {mean_val:.1f}")
    ax4.axvline(
        median_val, color="orange", linestyle="--", linewidth=2, label=f"Median: {median_val:.1f}"
    )
    ax4.legend(fontsize=10)

    # ========== CHART 5: Contrarian Analysis ==========
    ax5 = fig.add_subplot(gs[2, 1])

    contrarian_groups = (
        metrics_df.groupby("num_contrarian")
        .agg({"total_aggressiveness": "mean", "player_name": "count"})
        .reset_index()
    )
    contrarian_groups.columns = ["num_contrarian", "avg_aggressiveness", "num_players"]

    ax5.bar(
        contrarian_groups["num_contrarian"],
        contrarian_groups["avg_aggressiveness"],
        color="coral",
        edgecolor="black",
        linewidth=1.2,
    )

    for i, row in contrarian_groups.iterrows():
        ax5.text(
            row["num_contrarian"],
            row["avg_aggressiveness"] + 0.3,
            f"n={int(row['num_players'])}",
            ha="center",
            fontsize=9,
            fontweight="bold",
        )

    ax5.set_xlabel("Number of Contrarian Picks (Field < 50%)", fontsize=11, fontweight="bold")
    ax5.set_ylabel("Average Total Aggressiveness", fontsize=11, fontweight="bold")
    ax5.set_title(
        "Aggressiveness by Contrarian Pick Count\n(n = number of players)",
        fontsize=12,
        fontweight="bold",
        pad=10,
    )
    ax5.grid(axis="y", alpha=0.3)
    ax5.set_xticks(range(int(contrarian_groups["num_contrarian"].max()) + 1))

    # ========== Statistics Box ==========
    stats_text = f"""WEEK {week} RISK×CONF ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Formula: (1 - Field%) × Confidence

Players: {len(metrics_df)}
Mean Score: {metrics_df['total_aggressiveness'].mean():.2f}
Median Score: {metrics_df['total_aggressiveness'].median():.2f}

MOST AGGRESSIVE:
  {metrics_df.iloc[-1]['player_name'].replace(chr(92)+'$', '$')}
  Score: {metrics_df.iloc[-1]['total_aggressiveness']:.2f}
  Boldest: {metrics_df.iloc[-1]['boldest_team']}({int(metrics_df.iloc[-1]['boldest_confidence'])})

MOST CONSERVATIVE:
  {metrics_df.iloc[0]['player_name'].replace(chr(92)+'$', '$')}
  Score: {metrics_df.iloc[0]['total_aggressiveness']:.2f}

Range: {metrics_df['total_aggressiveness'].min():.2f} - {metrics_df['total_aggressiveness'].max():.2f}
Std Dev: {metrics_df['total_aggressiveness'].std():.2f}
"""

    fig.text(
        0.01,
        0.01,
        stats_text,
        fontsize=9,
        family="monospace",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.6),
        verticalalignment="bottom",
    )

    # Save chart
    output_file = os.path.join(output_dir, f"week_{week}_player_aggressiveness_rankings.png")
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close()

    return output_file


# ============================================================================
# MAIN EXECUTION
# ============================================================================
def analyze_contrarian_picks(week: int):
    data_dir = config.output_dir
    output_dir = config.output_dir
    # Check if data exists
    if not check_week_data_exists(week, data_dir):
        print(f"❌ Picks unavailable for week {week}.")
        print(f"\nRun scraper: {get_scraper_command(week)}")
        sys.exit(1)

    # Calculate metrics
    print(f"Analyzing week {week} aggressiveness...")
    try:
        metrics_df = calculate_aggressiveness_metrics(week, data_dir)
    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

    # Print summary table
    print(f"\n{'='*120}")
    print(f"WEEK {week} AGGRESSIVENESS RANKINGS - Risk×Conf Metric")
    print("Formula: Aggressiveness = (1 - Field%) × Confidence")
    print(f"{'='*120}\n")

    print(
        f"{'Rank':<6} {'Player':<25} {'Total':>8} {'Avg':>8} {'MaxPick':>8} {'Boldest Pick':<20} {'Points':>8} {'Wins':>6}"
    )
    print(f"{'-'*120}")

    for i, (_, row) in enumerate(metrics_df.iterrows(), 1):
        boldest = f"{row['boldest_team']}({int(row['boldest_confidence'])})@{row['boldest_field_pct']*100:.0f}%"
        print(
            f"{i:<6} {row['player_name']:<25} "
            f"{row['total_aggressiveness']:>8.2f} "
            f"{row['avg_aggressiveness']:>8.2f} "
            f"{row['max_pick_aggressiveness']:>8.2f} "
            f"{boldest:<20} "
            f"{row['total_points']:>8.0f} "
            f"{row['total_wins']:>6.0f}"
        )

    print(f"{'-'*120}\n")

    # Save metrics CSV
    csv_path = os.path.join(output_dir, f"week_{week}_aggressiveness_metrics.csv")
    metrics_df.to_csv(csv_path, index=False)
    print(f"✓ Metrics saved to: {csv_path}")

    # Create visualization
    print("\nGenerating visualization...")
    chart_path = create_chart(metrics_df, week, output_dir)
    print(f"✓ Chart saved to: {chart_path}")

    # Summary
    print(f"\n{'='*120}")
    print("SUMMARY:")
    print(
        f"  Most Aggressive: {metrics_df.iloc[0]['player_name']} ({metrics_df.iloc[0]['total_aggressiveness']:.2f})"
    )
    print(
        f"  Most Conservative: {metrics_df.iloc[-1]['player_name']} ({metrics_df.iloc[-1]['total_aggressiveness']:.2f})"
    )
    print(f"  Average Score: {metrics_df['total_aggressiveness'].mean():.2f}")
    print(f"{'='*120}\n")
