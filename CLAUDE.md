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
- Verify data output in `OUTPUT_DIR` (default `./data/`) after ingestion or analysis.
- Run the CI checks **before every push, not before every commit**: `task check` (format, lint, test).
  Commits are cheap and may be incremental; the push is the gate. CI runs exactly these three checks
  on Python 3.11, so a push that skipped them is a red build.
  - Gate on real exit codes. `ruff check . | tail -1 && git push` masks a failing lint - `tail` exits 0.
    Use `set -o pipefail`, or run each check unpiped.

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
# First-time setup
task setup            # create venv + install deps

# Taskfile shortcuts (agentic dev)
task run              # interactive CLI menu
task check            # format + lint + test
task lint             # ruff --fix .
task format           # black .
task test             # pytest

# Escape hatches
python -m cbs_fantasy_tooling.main      # direct module entry (fallback; prefer task run)
pytest                                  # run tests
ruff check --fix .                      # lint + auto-fix
black .                                 # code formatting
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
- `OUTPUT_DIR` (default `data/`) - All analysis output (CSVs, JSON predictions, charts)
- `config.py` - Centralized config management

## Anti-Patterns & Gotchas

**Avoid manual data wrangling; use the storage layer:**
- ❌ Don't write ad-hoc CSV parsing in analysis scripts
- ✅ Use `storage.providers` abstractions; they handle formatting and paths

**Avoid hard coding file names/paths:**
- ❌ Don't use `./data/week_5_odds.csv` directly
- ✅ Use `publishers.file.JSON_FILENAMES` or `CSV_FILENAMES` constants
- **Why**: Centralizes path management; prevents typos

**Avoid hardcoding weeks or seasons:**
- ❌ Don't use `week = 14` in code
- ✅ Use `config.py` to calculate current week from `WEEK_ONE_START_DATE` (Tuesday-to-Tuesday windows)
- **Why**: Prevents stale code as season progresses

**Avoid storing API keys in code:**
- ❌ `api_key = "abc123"` in any module
- ✅ Read from env via `config.py`: `config.the_odds_api_key`
- **Why**: Prevents credential leaks; enables different keys per environment

## External Docs & When To Read Them

**Onboarding:**
- `README.md` — Install, `.env` setup, quickstart commands

**Core usage:**
- `docs/usage.md` — Running the strategy simulator (use weekly for picks)
- `docs/win-analyzer.md` — Win probability analysis (use mid-week/live tracking)
- `docs/realtime.md` — Real-time polling mode via main CLI

**Data sources:**
- `docs/data-sources.md` — CBS/ESPN/Odds API details and failure modes
- **When**: Debugging API failures or adding new data sources

**Simulation internals:**
- `docs/monte-carlo.md` — Strategy definitions, tunables (`STRATEGY_MIX`, `N_SIMS`)
- **When**: Modifying strategy logic or tuning simulation parameters

**Output configuration:**
- `docs/publishers.md` — File/Gmail/Supabase publisher setup
- **When**: Configuring email delivery or database integration
- `docs/schemas.md` — Data formats (JSON, CSV, Supabase tables)
- **When**: Consuming output files programmatically

**Future features:**
- `docs/streaming-tasks.md` — Task list for `game_status` overlay implementation

## Potential Automation Opportunities

If you find yourself repeating multi-step CLI workflows, consider adding wrapper scripts:

**Examples:**
- Bulk historical backfill (loop through weeks 1-17)
- Scraper dry-run mode (test selectors without publishing)
- Non-interactive strategy run (picks via CLI args instead of prompts)

**Guideline**: Add a wrapper if a workflow requires >3 manual menu selections or complex flag combinations.

---

**Last Updated**: 2026-09-15
**For questions**: Check git history or ask the human (me).
