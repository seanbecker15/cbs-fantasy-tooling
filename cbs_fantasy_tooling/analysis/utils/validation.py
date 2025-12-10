"""Slate validation and display utilities."""

import sys
from cbs_fantasy_tooling.analysis.core.config import SLATE_MIN_GAMES, SLATE_MAX_GAMES


def validate_slate(mapping: list[dict], min_g=SLATE_MIN_GAMES, max_g=SLATE_MAX_GAMES):
    """
    Validate the game slate and provide warnings/confirmations.

    Args:
        mapping: Week mapping with game data
        min_g: Minimum expected games
        max_g: Maximum expected games

    Exits:
        If no games found or user declines to continue with partial slate
    """
    n = len(mapping)
    if n == 0:
        print("[ERROR] No games found for the current week window.")
        sys.exit(1)

    # Check for missing games (likely already started or API issues)
    EXPECTED_MIN_GAMES = 14  # Typical NFL week (adjust for bye weeks)
    if n < EXPECTED_MIN_GAMES:
        print(f"[WARNING] Only {n} games found (expected {EXPECTED_MIN_GAMES}+ for typical week)")
        print("          Possible causes:")
        print("          - Some games have already started (excluded from betting markets)")
        print("          - API issues or rate limiting")
        print("          - Bye weeks (Weeks 5-14 typically have 13-14 games)")

        # Interactive confirmation
        response = input(f"\nContinue with only {n} games? (y/n): ").strip().lower()
        if response != "y":
            print("Exiting. Please check game schedule and run simulator before games start.")
            sys.exit(1)

    if not (min_g <= n <= max_g):
        print(f"[WARN] Unexpected number of games returned: {n} (expected {min_g}–{max_g}).")
        print("       Check time window, bye weeks, or API filters.")
    else:
        print(f"[OK] {n} games found within the current NFL week window.")

    # Show a compact slate preview
    print("\nSlate preview (favorite vs dog, p_fav):")
    for i, g in enumerate(mapping, 1):
        fav = g["favorite"]
        dog = g["dog"]
        p = g["p_fav"]
        when = g.get("commence_time")
        print(f" {i:>2}. {fav} vs {dog} | p_fav={p:.3f} | commence={when}")
