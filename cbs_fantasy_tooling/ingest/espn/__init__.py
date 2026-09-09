"""Ingest layer for ESPN data sources."""

from .api import GameOutcomeIngestParams, fetch_game_results, ingest_game_outcomes

__all__ = ["GameOutcomeIngestParams", "fetch_game_results", "ingest_game_outcomes"]
