"""Weekly bonus tie handling.

The league breaks a tie for most points with a Monday-night total guess, so
exactly one player collects each bonus. The simulator previously paid every
tied player in full, which overstated the value of finishing level with the
leader - and flattered strategies that cluster near the field.
"""

import numpy as np
import pytest

from cbs_fantasy_tooling.analysis.core import simulator


def _bonuses(wins, points, rule, seed=0):
    rng = np.random.default_rng(seed)
    return simulator._apply_bonuses(np.array(wins), np.array(points), rule=rule, rng=rng)


class TestSingleWinner:
    """Default rule: one player gets the +10, one gets the +5."""

    def test_no_tie_pays_the_leader(self):
        mw, mp = _bonuses([10, 12, 9], [90, 100, 85], rule="single")
        assert mp.tolist() == [0, 10, 0]
        assert mw.tolist() == [0, 5, 0]

    def test_points_tie_pays_exactly_one_tied_player(self):
        mw, mp = _bonuses([10, 10, 9], [100, 100, 85], rule="single")
        assert mp.sum() == 10
        assert (mp > 0).sum() == 1
        assert np.flatnonzero(mp)[0] in (0, 1)

    def test_wins_tie_pays_exactly_one_tied_player(self):
        mw, mp = _bonuses([12, 12, 12], [100, 95, 90], rule="single")
        assert mw.sum() == 5
        assert (mw > 0).sum() == 1

    def test_tiebreak_is_uniform_over_tied_players(self):
        counts = np.zeros(3)
        for seed in range(3000):
            _, mp = _bonuses([1, 1, 1], [50, 50, 50], rule="single", seed=seed)
            counts += mp > 0
        # each of three tied players should win roughly a third of the time
        assert counts.min() > 800 and counts.max() < 1200

    def test_untied_player_never_paid_on_tie(self):
        for seed in range(200):
            _, mp = _bonuses([1, 1, 1], [50, 50, 40], rule="single", seed=seed)
            assert mp[2] == 0


class TestLegacyRules:
    """Keep the old behaviours reachable for comparison runs."""

    def test_all_pays_every_tied_player_in_full(self):
        mw, mp = _bonuses([10, 10, 9], [100, 100, 85], rule="all")
        assert mp.tolist() == [10, 10, 0]
        assert mw.tolist() == [5, 5, 0]

    def test_split_divides_evenly(self):
        mw, mp = _bonuses([10, 10, 9], [100, 100, 85], rule="split")
        assert mp.tolist() == [5, 5, 0]
        assert mw.tolist() == [2.5, 2.5, 0]

    def test_unknown_rule_rejected(self):
        with pytest.raises(ValueError, match="TIE_RULE"):
            _bonuses([1], [1], rule="lottery")


def test_default_rule_is_single():
    from cbs_fantasy_tooling.analysis.core.config import TIE_RULE

    assert TIE_RULE == "single"


def test_week_simulation_pays_fifteen_total():
    """Whatever the tie situation, exactly 15 bonus points leave the pot."""
    p = np.full(16, 0.5)
    strategies = [simulator.STRATEGIES["Chalk-MaxPoints"]] * 6  # guaranteed ties
    for _ in range(50):
        _, _, total, mw, mp = simulator.simulate_week_once(p, strategies)
        assert mw.sum() + mp.sum() == 15
