# Season Rollover Checklist

Everything that has to change when a new NFL season starts. Work through it in
order; each step says how to verify it.

## 1. Get the new pool slug

CBS creates a **new pool every season**, so last year's URL 404s or silently
shows the wrong pool.

1. Open your pool in a browser and copy the URL:
   `https://picks.cbssports.com/football/pickem/pools/<SLUG>/standings/weekly`
2. Put `<SLUG>` in `.env` as `CBS_POOL_SLUG`.

The slug is base32. To confirm you have the right pool:

```bash
python -c "import base64,sys; s=sys.argv[1].upper(); s+='='*(-len(s)%8); print(base64.b32decode(s))" <SLUG>
# -> b'Pool:16579757'
```

Verify:

```bash
python -c "from cbs_fantasy_tooling.ingest.cbs_sports.scrape import build_login_url; print(build_login_url())"
```

## 2. Update season config

In `.env`:

```bash
SEASON=2026
WEEK_ONE_START_DATE=2026-09-08   # the TUESDAY before Week 1's first game
```

`WEEK_ONE_START_DATE` anchors every week calculation. Weeks run Tuesday 05:00
UTC to the following Tuesday 04:59 UTC, so use the Tuesday *before* the first
game — not the game date itself.

Verify:

```bash
python -c "from cbs_fantasy_tooling.utils.date import get_current_week, get_last_completed_week; \
print('current', get_current_week(), 'last completed', get_last_completed_week())"
```

During Week 1 this should print `current 1`.

## 3. Roll the data directories

**Output filenames are not season-scoped** (`week_1_game_results.json` has no
year in it), so a new season's ingest will overwrite last season's files. Last
season's data is what the competitor model is built from, so it must be kept.

```bash
mkdir -p data/2026
```

In `.env`:

```bash
OUTPUT_DIR="data/2026"    # this season's writes
HISTORY_DIR="data/2025"   # completed seasons, used to model the field
```

`HISTORY_DIR` defaults to `OUTPUT_DIR` when unset. It is what
`get_actual_field_composition()` reads, so pointing it at a completed season is
what lets Week 1 simulations use a real field instead of a guess.

Verify:

```bash
python -c "from cbs_fantasy_tooling.analysis.core.config import get_field_composition; print(get_field_composition())"
```

You want to see "Using ACTUAL field composition", not "Using THEORETICAL".

## 4. Check league size

If players joined or left, set `LEAGUE_SIZE` in `.env`. The simulator warns and
adjusts if the historical field doesn't match, but the count should be right.

```bash
python -c "import json; print(len(json.load(open('data/2025/week_18_pickem_results.json'))['results']))"
```

## 5. Confirm history is complete

The field model scores every historical pick against game results. A missing
week of game results silently counts that week's picks as **losses** and skews
the model.

```bash
for w in $(seq 1 18); do [ -f "data/2025/week_${w}_game_results.json" ] || echo "missing week $w"; done
```

Backfill any gaps (note `season=` selects the historical season):

```bash
python -c "
import json
from cbs_fantasy_tooling.ingest.espn.api import ESPNGameOutcomeApi
from cbs_fantasy_tooling.models import GameResults
w = 18
g = ESPNGameOutcomeApi(season=2025).fetch_game_results(week=w)
json.dump(GameResults(season=2025, week=w, games=g, num_games=len(g)).to_dict(),
          open(f'data/2025/week_{w}_game_results.json','w'), indent=2)
print('wrote', len(g), 'games,', sum(1 for x in g if x.is_finished), 'finished')
"
```

Sanity check the win rate — it should land near 60%, not the low 50s:

```bash
python -c "from cbs_fantasy_tooling.analysis.core.config import get_field_composition; get_field_composition()"
```

## 6. Re-check publishers

```bash
python -c "from cbs_fantasy_tooling.publishers.factory import create_publishers; \
print([p.name for p in create_publishers()])"
```

- **Gmail**: the OAuth token refreshes itself, but the refresh token expires
  after long inactivity. If auth fails, delete `token.json` and re-run to
  redo the consent flow.
- **Supabase**: free projects are paused after inactivity and eventually
  deleted, so the host stops resolving. Either restore the project and update
  `SUPABASE_URL`/`SUPABASE_KEY`, or drop `database` from `ENABLED_PUBLISHERS`.

## 7. Smoke test before the first real run

```bash
task check   # format, lint, tests
```

Then a dry run of each source:

```bash
# ESPN - should print this season's Week 1 slate
python -c "from cbs_fantasy_tooling.ingest.espn.api import ESPNGameOutcomeApi; \
from cbs_fantasy_tooling.config import config; \
g=ESPNGameOutcomeApi(season=config.season).fetch_game_results(week=1); \
print(len(g),'games'); print(g[0].away_team,'@',g[0].home_team,g[0].game_time)"
```

For the CBS scrape, run the CLI in **Once** mode and inspect the output before
enabling real-time polling or publishing. It needs Chrome and an interactive
login, so it can't be verified headlessly.

## Known external quirks

| Source | Quirk |
|--------|-------|
| ESPN | 403s browser-like `User-Agent` strings. Do not set one. |
| ESPN | Ignores `year=`; the season is selected with `dates=`. A wrong param silently returns the *current* season. |
| CBS | Pool slug changes every season and is base32 with `=` padding; unpadded slugs 307-redirect to the padded form. |
| The Odds API | 500 requests/month on the free tier; each simulator run costs 1. |
