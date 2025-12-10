<!--
DESIGN PHILOSOPHY:
This file is a high-leverage "constitution" for AI agents, not a manual.
- Keep it <200 lines. If you need more, externalize to docs/
- Focus on guardrails, 80/20 workflows, and pointers
- Replace "never do X" with "avoid X; prefer Y because Z"
- Pitch external docs: explain WHEN to read them and WHY
- Prefer CLI wrappers over documenting complex command chains

To grow this file:
1. Ask: Is this frequently relevant across weeks/tasks?
2. Ask: Does this prevent a repeated, costly mistake?
3. If no to both: put it in docs/ and add a pointer here
-->

# CBS Fantasy Tooling - Agent Constitution

## Global Guardrails

**Safety & Reliability:**
- Never commit secrets (`.env`, `credentials.json`, `token.pickle`). Check `.gitignore` before adding files.
- Avoid breaking idempotency: data ingestion should safely retry without duplicates.
- Prefer explicit types (Pydantic models, type hints) over dynamic dicts. Catch errors at dev time, not runtime.
- For external API calls (ESPN, TheOddsAPI, CBS), implement retries with exponential backoff. APIs are flaky.

**Correctness Over Cleverness:**
- Prioritize readable, boring code over clever optimizations. Other engineers (and future LLMs) need to understand this.
- For critical business logic (scoring, Monte Carlo sim, probability calculations): write tests FIRST to clarify requirements.
- For simple CRUD or API wrappers: write tests after implementation if needed.

**Development Workflow:**
- Use the interactive CLI (`cbs-scrape`) as the entry point, not direct Python module calls.
- Test changes by running CLI in "Once" mode with manual week selection before committing.
- Verify data output in `./out/` directory after ingestion or analysis.

## Tech Stack & Tools

**Core Stack:**
- Python 3.x with virtual environment (`.venv`)
- **Web Scraping**: Selenium WebDriver (CBS login, dynamic content)
- **APIs**: ESPN (game results), TheOddsAPI (moneylines), Google Gmail API (publishing)
- **Data**: Pandas (CSV), JSON (structured output), Supabase (optional DB storage)
- **Analysis**: NumPy (Monte Carlo), Matplotlib (visualization)
- **CLI**: InquirerPy (interactive menus), Typer (planned but not primary)

**Key Commands:**
```bash
# Setup (one-time)
python -m venv .venv && source .venv/bin/activate
pip install -e .

# Primary interface
cbs-scrape                           # Interactive CLI menu

# Validation
pytest                               # Run tests (if present)
python -m cbs_fantasy_tooling.main   # Direct module entry (avoid; use CLI)
```

**Common Workflows:**
1. **Data Ingestion**: CLI → "Ingest Data" → pick source (Pick'em, Games, Odds) → select week
2. **Strategy Analysis**: CLI → "Analyze Data" → "Strategy Simulator" → optionally input picks
3. **Competitor Intel**: CLI → "Analyze Data" → "Competitor Intelligence" → specify week

## Core Architecture (High-Level Only)

**Data Flow:**
```
Ingest (cbs_sports/, espn/, the_odds_api/)
  ↓
Storage (providers/: file, database)
  ↓
Publishers (gmail, file, database - configurable via ENABLED_PUBLISHERS)
  ↓
Analysis (monte_carlo.py, competitor_intelligence.py)
```

**Key Modules:**
- `main.py` - CLI entry point (start here for interactive workflows)
- `ingest/` - Data fetching (Selenium scraping, API calls)
- `storage/` - Persistence layer (file, DB)
- `publishers/` - Output distribution (email, CSV, Supabase)
- `analysis/` - Monte Carlo sim, competitor patterns, contrarian picks

**Critical Files:**
- `.env` - Secrets and config (never commit; check `.env.example` for required vars)
- `out/` - All analysis output (CSVs, JSON predictions, charts)
- `config.py` - Centralized config management

## Anti-Patterns & Gotchas

**Avoid manual data wrangling; use the storage layer:**
- ❌ Don't write ad-hoc CSV parsing in analysis scripts
- ✅ Use `storage.providers` abstractions; they handle formatting and paths

**Avoid hardcoding weeks or seasons:**
- ❌ Don't use `week = 14` in code
- ✅ Use `config.py` to calculate current week from `WEEK_ONE_START_DATE` (Tuesday-to-Tuesday windows)
- **Why**: Prevents stale code as season progresses

**Avoid storing API keys in code:**
- ❌ `api_key = "abc123"` in any module
- ✅ Read from env via `config.py`: `os.getenv("THE_ODDS_API_KEY")`
- **Why**: Prevents credential leaks; enables different keys per environment

**Avoid running scrapers without testing selectors first:**
- ❌ Assume CBS Sports HTML structure is stable
- ✅ Run in "Once" mode first; verify output in `./out/`; CBS often changes their DOM
- **Why**: Selenium scripts are brittle; catch breakage early

**Avoid skipping de-vig for probability calculations:**
- ❌ Using raw betting odds as win probabilities
- ✅ The codebase already implements median consensus de-vig with sharp book weighting
- **Why**: Bookmaker margins skew probabilities; de-vig gives fairer estimates

**Avoid pushing untested Monte Carlo changes:**
- ❌ Modifying `analysis/core/` strategy logic without validation
- ✅ Run full strategy comparison (`cbs-scrape → Analyze → Strategy Simulator`) and sanity-check expected points
- **Why**: Small bugs in probability logic cause huge EV miscalculations

## External Docs & When To Read Them

**Onboarding / setup:**
- `README.md` — Minimal install + `.env` keys; how to run the interactive CLI.

**Core usage:**
- `docs/usage.md` — Confidence pool simulator (odds → strategies → outputs). Use weekly. 
- `docs/win-analyzer.md` — Supabase-driven “can I still win?” analysis; leaderboard mode. Use mid-week/live.
- `docs/realtime.md` — How to run CBS polling loop into Supabase; notes on limitations.

**Data + internals:**
- `docs/data-sources.md` — Where data comes from (CBS, ESPN, The Odds API) and failure modes.
- `docs/monte-carlo.md` — Strategy definitions, tunables (`STRATEGY_MIX`, `N_SIMS`, sharp weighting).

**Outputs & delivery:**
- `docs/publishers.md` — File/Gmail/Supabase publishers and required env/config.
- `docs/schemas.md` — File formats and Supabase table columns for integrating consumers.

**Roadmap:**
- `docs/streaming-tasks.md` — Short task list to populate `game_status` and power overlays.

## Wrapper Opportunities (Future Improvements)

**Instead of documenting complex commands, create wrappers:**

1. **Testing scraper without full ingestion:**
   ```bash
   # Current: long selenium debugging process
   # Proposed: ./scripts/test-scraper.sh --week 14 --dry-run
   ```

2. **Bulk historical data fetch:**
   ```bash
   # Current: manually loop through weeks in CLI
   # Proposed: ./scripts/backfill-weeks.sh 1-17
   ```

3. **Strategy validation:**
   ```bash
   # Current: navigate CLI menus each time
   # Proposed: ./scripts/run-strategy.sh --picks "Ravens,Bills,..." --compare
   ```

**When to add a wrapper:**
- If you document a command >2 lines with complex flags
- If a workflow requires >3 manual CLI menu selections
- If you need to run the same operation across multiple weeks/seasons

---

**Last Updated**: 2025-12-09
**For questions**: Check git history or ask the human (me).
