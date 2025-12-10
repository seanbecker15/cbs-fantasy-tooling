# CBS Fantasy Tooling - Copilot Instructions

## Repository Overview

**Purpose**: Python toolkit for CBS Sports fantasy football confidence pools. Scrapes standings, fetches ESPN game data and betting odds, runs Monte Carlo simulations for strategy optimization.

**Stack**: Python 3.9+, Selenium WebDriver, Pandas/NumPy, Matplotlib, InquirerPy CLI, Pydantic models, optional Supabase

**Size**: ~55 Python files, ~2000 LOC, no test suite currently

## Setup and Environment

### Initial Setup (Required Before Any Work)

1. **Create and activate virtual environment** (ALWAYS do this first):
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. **Install the package in editable mode** (required for CLI to work):
```bash
pip install -e .
pip install -r requirements.txt  # Required: pyproject.toml is incomplete
```
This takes ~60 seconds. **Important**: `requirements.txt` has additional dependencies (InquirerPy, supabase) not in `pyproject.toml`.

3. **Install development dependencies** (required for linting):
```bash
pip install pytest black ruff
```

4. **Create .env file** (required for most functionality):
Copy `.env.example` to `.env` and configure at minimum:
- `EMAIL` - CBS Sports login (required for scraping)
- `PASSWORD` - CBS Sports password (required for scraping)
- `THE_ODDS_API_KEY` - For strategy simulator (required for analysis)
- `ENABLED_PUBLISHERS` - Defaults to "file,gmail" (use "file" for local dev)
- `WEEK_ONE_START_DATE` - Used for week calculations (default: "2025-09-02")

**Note**: The code loads `.env` automatically via `python-dotenv`. Missing credentials will cause runtime errors when scraping or analyzing, but imports will work.

**Chrome/Selenium**: Chrome browser required; ChromeDriver auto-managed by Selenium 4.x

## Build, Test, and Validation

### Linting (ALWAYS run before committing)

```bash
black .                  # Auto-format (line-length=100)
ruff check --fix .       # Fix linting issues
```

**Expected**: Black may report many files to reformat (normal). Fix any issues in your modified files. No pre-commit hooks exist.

### Testing

**No test suite exists**. If adding tests: use `pytest`, write tests FIRST for critical logic (scoring, Monte Carlo, probabilities).

### Running the Application

```bash
python -m cbs_fantasy_tooling.main  # Interactive CLI with InquirerPy menus
```

**Note**: The `cbs-scrape` command defined in `pyproject.toml` is broken (tries to import non-existent `app`). Use `python -m` instead.

**Validation**: Run CLI after changes → test in "Once" mode → verify outputs in `./out/` (CSV/JSON files)

## Project Structure and Architecture

### High-Level Directory Layout

```
cbs-fantasy-tooling/
├── cbs_fantasy_tooling/          # Main package
│   ├── main.py                   # CLI entry point (InquirerPy menus)
│   ├── config.py                 # Config management (loads .env)
│   ├── ingest/                   # Data fetching
│   │   ├── cbs_sports/           # Selenium-based CBS scraping
│   │   ├── espn/                 # ESPN API for game outcomes
│   │   └── the_odds_api/         # TheOddsAPI for betting lines
│   ├── storage/                  # Data persistence
│   │   ├── game_results.py       # Game result storage logic
│   │   ├── pickem_results.py     # Pickem result storage logic
│   │   └── providers/            # Storage backends (file, database)
│   ├── publishers/               # Output distribution
│   │   ├── factory.py            # Publisher factory
│   │   ├── file.py               # File-based publisher (CSV/JSON)
│   │   ├── gmail.py              # Gmail email publisher
│   │   └── database.py           # Supabase database publisher
│   ├── analysis/                 # Core analysis logic
│   │   ├── monte_carlo.py        # Main orchestration for simulations
│   │   ├── competitor_intelligence.py  # Competitor analysis
│   │   ├── core/                 # Simulation engine
│   │   │   ├── config.py         # N_SIMS, STRATEGY_MIX tunables
│   │   │   ├── strategies.py     # Strategy implementations
│   │   │   └── simulator.py      # Monte Carlo simulation loop
│   │   ├── odds/                 # Odds processing
│   │   │   └── converter.py      # Moneyline to probability conversion
│   │   ├── user/                 # User pick analysis
│   │   ├── competitor/           # Competitor pattern detection
│   │   └── visualization/        # Chart generation
│   ├── models/                   # Pydantic data models
│   │   ├── game_result.py        # Game result model
│   │   └── pickem_result.py      # Pickem result model
│   └── utils/                    # Utility functions
│       └── date.py               # NFL week calculations
├── docs/                         # Documentation
│   ├── USAGE.md                  # Confidence pool simulator usage
│   ├── win-analyzer.md           # "Can I still win?" analysis
│   ├── realtime.md               # Real-time polling setup
│   ├── data-sources.md           # Data source details
│   ├── monte-carlo.md            # Simulation internals
│   ├── publishers.md             # Publisher configuration
│   └── schemas.md                # Data schemas
├── scripts/                      # Helper scripts
│   ├── schedule-task.sh          # macOS launchctl scheduling
│   └── unschedule-task.sh        # Remove scheduled task
├── out/                          # Output directory (gitignored)
├── .env                          # Environment config (gitignored)
├── .env.example                  # Example environment file
├── pyproject.toml                # Package configuration
├── requirements.txt              # Pinned dependencies
├── README.md                     # Quick start guide
└── CLAUDE.md                     # Agent constitution (for Claude, not Copilot)
```

### Key Patterns

- **Publishers**: Outputs via `ENABLED_PUBLISHERS` in `.env` (file/gmail/database)
- **Storage providers**: Use abstractions in `storage/providers/`, not direct file I/O
- **Config singleton**: Import `config` from `config.py`, don't reload `.env`
- **Pydantic models**: Structured validation in `models/`

## Common Workflows

**Development**: Edit → `black . && ruff check --fix .` → `python -m cbs_fantasy_tooling.main` test → verify `./out/` → commit

**Scraping changes**: Edit `ingest/cbs_sports/scrape.py` → test in "Once" mode first (CBS HTML changes frequently, selectors are brittle)

**Strategy changes**: Edit `analysis/core/strategies.py` or `config.py` → run Strategy Simulator via CLI → validate expected points

## Critical Constraints

**Never**:
- Commit secrets (`.env`, `credentials.json`, `token.*`)
- Hardcode weeks/seasons (use `config.py` with `WEEK_ONE_START_DATE`)
- Bypass storage providers (use `storage.providers/`)
- Skip de-vig odds (use `analysis/odds/converter.py`)
- Assume stable CBS HTML (test scrapers in "Once" mode)

**Known Issues**:
- Real-time mode stubbed (TODOs in `main.py` lines 102, 116)
- No CI/CD or pre-commit hooks
- Chrome required for scraping
- `cbs-scrape` command broken (use `python -m cbs_fantasy_tooling.main` instead)
- `pyproject.toml` dependencies incomplete (must also install `requirements.txt`)

## Key Files

**Config**: `pyproject.toml` (deps, tools), `.env.example` (secrets template), `config.py` (singleton)
**Entry**: `main.py` (CLI), `analysis/monte_carlo.py` (simulation orchestrator)
**Core**: `analysis/core/{strategies,simulator,config}.py`, `ingest/cbs_sports/scrape.py`
**Docs**: `README.md` (quick start), `docs/{USAGE,publishers,monte-carlo}.md`

## Trust These Instructions

Follow directly; only search if incomplete or errors occur. Common issues: forgot venv activation, missing `pip install -e .`, unconfigured `.env`.

## Quick Reference Card

```bash
# Setup (one-time)
python -m venv .venv && source .venv/bin/activate
pip install -e .
pip install -r requirements.txt  # Important: pyproject.toml is incomplete
pip install pytest black ruff
cp .env.example .env  # Then edit with your credentials

# Daily workflow
source .venv/bin/activate           # Start session
python -m cbs_fantasy_tooling.main  # Run interactive CLI
black . && ruff check .             # Lint before commit

# Verify outputs
ls -l out/                          # Check for expected CSVs/JSONs
```

**Most common mistakes**: 
- Forgetting venv activation (`source .venv/bin/activate`)
- Running `pip install -e .` without also installing `requirements.txt`
- Using `cbs-scrape` command (broken) instead of `python -m cbs_fantasy_tooling.main`
