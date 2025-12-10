"""Ingest layer for ESPN data sources."""

from .api import ingest_game_outcomes, GameOutcomeIngestParams, fetch_game_results

__all__ = ["ingest_game_outcomes", "GameOutcomeIngestParams", "fetch_game_results"]
