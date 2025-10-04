"""
Tests for Competitor Strategy Classifier

TDD approach for critical business logic that classifies player strategies.
"""

import pandas as pd
import numpy as np
from competitor_classifier import (
    classify_player_strategy,
    calculate_player_metrics,
    build_player_profiles,
    StrategyType
)


def test_classify_pure_chalk_player():
    """Test classification of player who only picks favorites"""
    player_picks = pd.DataFrame({
        'player_name': ['Player1'] * 16,
        'week': [1] * 16,
        'is_contrarian': [False] * 16,
        'confidence': range(16, 0, -1),
        'won': [True] * 10 + [False] * 6
    })

    strategy = classify_player_strategy(player_picks)
    assert strategy == StrategyType.CHALK, "Pure chalk player should be classified as CHALK"


def test_classify_slight_contrarian():
    """Test classification of player with 1-2 contrarian picks per week"""
    player_picks = pd.DataFrame({
        'player_name': ['Player2'] * 16,
        'week': [1] * 16,
        'is_contrarian': [True, True, False, False, False, False, False, False,
                          False, False, False, False, False, False, False, False],
        'confidence': range(16, 0, -1),
        'won': [True] * 10 + [False] * 6
    })

    strategy = classify_player_strategy(player_picks)
    assert strategy == StrategyType.SLIGHT_CONTRARIAN, \
        "Player with 12.5% contrarian rate should be SLIGHT_CONTRARIAN"


def test_classify_aggressive_contrarian():
    """Test classification of player with 4+ contrarian picks per week"""
    player_picks = pd.DataFrame({
        'player_name': ['Player3'] * 16,
        'week': [1] * 16,
        'is_contrarian': [True] * 5 + [False] * 11,
        'confidence': range(16, 0, -1),
        'won': [True] * 8 + [False] * 8
    })

    strategy = classify_player_strategy(player_picks)
    assert strategy == StrategyType.AGGRESSIVE_CONTRARIAN, \
        "Player with 31% contrarian rate should be AGGRESSIVE_CONTRARIAN"


def test_calculate_player_metrics():
    """Test metric calculation for a player"""
    player_picks = pd.DataFrame({
        'player_name': ['TestPlayer'] * 32,
        'week': [1] * 16 + [2] * 16,
        'is_contrarian': [True, False] * 16,
        'confidence': list(range(16, 0, -1)) * 2,
        'won': [True] * 20 + [False] * 12,
        'points_earned': [10] * 20 + [0] * 12
    })

    metrics = calculate_player_metrics(player_picks)

    assert metrics['player_name'] == 'TestPlayer'
    assert metrics['total_picks'] == 32
    assert metrics['contrarian_rate'] == 0.5  # 16/32
    assert metrics['win_rate'] == 20 / 32
    assert metrics['weeks_played'] == 2


def test_build_player_profiles():
    """Test building profiles for multiple players"""
    picks_df = pd.DataFrame({
        'player_name': ['Alice'] * 16 + ['Bob'] * 16,
        'week': [1] * 32,
        'is_contrarian': [False] * 16 + [True] * 6 + [False] * 10,
        'confidence': list(range(16, 0, -1)) * 2,
        'won': [True] * 10 + [False] * 6 + [True] * 8 + [False] * 8,
        'points_earned': [5] * 10 + [0] * 6 + [5] * 8 + [0] * 8
    })

    profiles = build_player_profiles(picks_df)

    assert len(profiles) == 2
    assert 'Alice' in [p['player_name'] for p in profiles]
    assert 'Bob' in [p['player_name'] for p in profiles]

    alice = [p for p in profiles if p['player_name'] == 'Alice'][0]
    assert alice['strategy'] == StrategyType.CHALK

    bob = [p for p in profiles if p['player_name'] == 'Bob'][0]
    assert bob['strategy'] == StrategyType.AGGRESSIVE_CONTRARIAN


if __name__ == "__main__":
    print("Running Competitor Classifier Tests...")
    print("=" * 60)

    tests = [
        test_classify_pure_chalk_player,
        test_classify_slight_contrarian,
        test_classify_aggressive_contrarian,
        test_calculate_player_metrics,
        test_build_player_profiles
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            print(f"✓ {test_func.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {test_func.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__}: Unexpected error: {e}")
            failed += 1

    print("=" * 60)
    print(f"Tests passed: {passed}/{len(tests)}")
    if failed == 0:
        print("All tests passed!")
    else:
        print(f"Tests failed: {failed}")
