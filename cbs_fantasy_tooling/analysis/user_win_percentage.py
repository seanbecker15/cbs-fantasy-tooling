"""User win percentage trend analysis."""

import os
import re
from typing import Dict, List, Optional

from matplotlib import pyplot as plt
from supabase import create_client

from cbs_fantasy_tooling.config import config
from cbs_fantasy_tooling.publishers.file import CHART_FILENAMES


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    return slug or "player"


def analyze_user_win_percentage(player_name: Optional[str] = None) -> Optional[str]:
    """
    Plot a user's win% across the season and print summary metrics.

    Returns path to the saved chart, or None on error.
    """
    target = player_name or config.user_name
    if not target:
        print("Error: player_name is required (or set USER_NAME in .env).")
        return None

    if not config.validate_database_config():
        print("Error: SUPABASE_URL and SUPABASE_KEY must be set in .env")
        return None

    client = create_client(config.supabase_url, config.supabase_key)
    response = (
        client.table("player_results")
        .select("week_number,wins,losses")
        .eq("season", config.season)
        .eq("player_name", target)
        .order("week_number", desc=False)
        .execute()
    )

    rows: List[Dict] = response.data or []
    if not rows:
        print(f"No results found for {target} in season {config.season}.")
        return None

    weeks: List[int] = []
    win_pcts: List[float] = []
    total_wins = 0
    total_losses = 0

    for row in rows:
        wins = row.get("wins", 0) or 0
        losses = row.get("losses", 0) or 0
        total = wins + losses
        weeks.append(row["week_number"])
        pct = (wins / total * 100) if total else 0.0
        win_pcts.append(pct)
        total_wins += wins
        total_losses += losses

    overall_pct = (total_wins / (total_wins + total_losses) * 100) if (total_wins + total_losses) else 0
    best_idx = max(range(len(win_pcts)), key=lambda i: win_pcts[i])
    best_week = weeks[best_idx]
    best_pct = win_pcts[best_idx]
    latest_week = weeks[-1]
    latest_pct = win_pcts[-1]

    print("=" * 70)
    print(f"{target} — Season {config.season} Win% Trend")
    print("=" * 70)
    print(f"Weeks tracked: {len(weeks)}")
    print(f"Total wins/losses: {total_wins}/{total_losses}")
    print(f"Overall win%: {overall_pct:.2f}%")
    print(f"Best week: {best_week} ({best_pct:.2f}%)")
    print(f"Latest week: {latest_week} ({latest_pct:.2f}%)")
    print("=" * 70)

    # Plot
    plt.figure(figsize=(9, 4.5))
    plt.plot(weeks, win_pcts, marker="o", color="#4B9CD3", linewidth=2)
    plt.fill_between(weeks, win_pcts, alpha=0.1, color="#4B9CD3")
    plt.title(f"{target} Win% by Week (Season {config.season})")
    plt.xlabel("Week")
    plt.ylabel("Win Percentage")
    plt.ylim(0, 100)
    plt.grid(alpha=0.3, linestyle="--")
    plt.tight_layout()

    player_slug = _slugify(target)
    filename = CHART_FILENAMES["user_win_pct"](player_slug)
    os.makedirs(config.output_dir, exist_ok=True)
    chart_path = os.path.join(config.output_dir, filename)
    plt.savefig(chart_path, dpi=200, bbox_inches="tight")
    plt.close()

    print(f"Win% chart saved to: {chart_path}")
    return chart_path
