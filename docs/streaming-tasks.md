# Streaming Overlay Tasks

Goal: populate `game_status` so overlays can show “key games to watch” and live standings deltas.

## Prerequisite (do first)
- **Ingest schedules/scores** from ESPN: adapt `ingest/espn/api.py` to also write `game_status` records (home/away, start time, scores, is_finished). Without this, nothing else matters.

## Phase 1 — Game Status Population
1) After each CBS scrape, infer opponent team for every pick and create/update `game_status` rows (home/away/time from ESPN, fallback to inferred pairs).  
2) Add viewer interest + importance scores: count how many players picked each side and weight by confidence.  
3) Persist `is_finished`, `home_score`, `away_score` from ESPN so pick correctness can be computed later.

## Phase 2 — Pick Correctness + Live Ranks
4) When `game_status.is_finished` flips, mark related `player_picks.is_correct` and recalc `player_results` ranks/points_from_leader on save.  
5) Expose a lightweight read API (or SQL view) for overlays: top 5 leaderboard, top 3 important games with viewer interest.

## Phase 3 — Polish
6) Add RLS policies appropriate for public read / private write.  
7) Optional websocket push (Supabase realtime or custom) instead of polling.  
8) Add basic monitoring: log last successful poll time and last change detected.

## Nice-to-Haves
- Backfill historical weeks with ESPN data for year-over-year visuals.  
- Small CLI wrapper: `python -m cbs_fantasy_tooling.ingest.stream` to run ESPN poll + CBS scrape together.
