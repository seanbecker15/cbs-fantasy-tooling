"""Ingest layer for CBS Sports data sources."""

from .scrape import PickemIngestParams, ingest_pickem_results

__all__ = ["PickemIngestParams", "ingest_pickem_results"]
