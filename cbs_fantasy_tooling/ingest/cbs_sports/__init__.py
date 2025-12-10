"""Ingest layer for CBS Sports data sources."""

from .scrape import ingest_pickem_results, PickemIngestParams

__all__ = ["ingest_pickem_results", "PickemIngestParams"]
