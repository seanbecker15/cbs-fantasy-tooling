# CBS Fantasy Tooling - Task List

## Game Status Population (Streaming Overlay Support)

The `game_status` table is currently defined but not populated. This needs to be implemented to enable streaming overlay features like "key games to watch" and game importance tracking.

---

## ⚠️ PREREQUISITE: Real-Time Game Data Integration

**Before implementing Tasks 1.1-1.3**, you need a reliable source of NFL game data.

### Why This Is Required First

The current scraper only extracts:
- Player names
- Total points (wins/losses calculated)
- Pick selections (team + confidence points)

**What's Missing**:
- ❌ Game matchups (which teams play each other)
- ❌ Home vs Away designation
- ❌ Game times/schedules
- ❌ Live scores
- ❌ Game completion status

**Impact**: Without this data, you cannot:
1. Create `game_status` records (don't know matchups)
2. Calculate viewer interest (need to know which picks are for the same game)
3. Calculate importance scores (need game groupings)
4. Determine pick correctness (need game outcomes)

### Recommended Solution: ESPN API Integration (Task 2.1)

**Move Task 2.1 to be done FIRST** before Phase 1.

The ESPN API provides:
```json
{
  "events": [
    {
      "name": "Kansas City Chiefs at Buffalo Bills",
      "date": "2025-01-26T23:30Z",
      "competitions": [{
        "competitors": [
          {"team": {"abbreviation": "KC"}, "homeAway": "away"},
          {"team": {"abbreviation": "BUF"}, "homeAway": "home"}
        ],
        "status": {"type": {"completed": true}}
      }]
    }
  ]
}
```

**Good News**: You already have `simulator/game_results_fetcher.py` that uses ESPN API!

### Alternative: Manual Mapping (Quick Start)

If you want to start testing before ESPN integration:

**Option**: Create a simple mapping file for current week
```python
# week_3_games.py
WEEK_3_GAMES_2025 = [
    {"home": "BUF", "away": "KC", "time": "2025-09-14T17:00:00Z"},
    {"home": "DET", "away": "CHI", "time": "2025-09-14T17:00:00Z"},
    # ... all 16 games
]
```

**Pros**: Can test algorithms immediately
**Cons**: Manual work each week, no live scores

### Recommended Implementation Order (REVISED)

**Step 0: Get Game Data** ⚡ (DO THIS FIRST)
- Adapt `simulator/game_results_fetcher.py` to fetch schedules
- Create `app/game_schedule_fetcher.py`
- Test with current week
- **Estimated effort**: 2-4 hours

**Then proceed with original plan**:
- Sprint 1: Basic game status (Tasks 1.1-1.3)
- Sprint 2: Live score updates (Tasks 2.2-2.3)
- Sprint 3: Production polish (Tasks 3.1-3.3)

---

### Phase 0: Database Setup

#### Task 0.1: Configure Supabase RLS Policies 🔒
**Priority**: Critical
**Effort**: Low
**Status**: Not Started

**Description**: Review and configure Row Level Security (RLS) policies for all tables before populating data.

**Current State**:
The SQL schema in `database.py` includes basic "allow all" policies:
```sql
CREATE POLICY "Enable read access for all users" ON player_results FOR SELECT USING (true);
CREATE POLICY "Enable insert for all users" ON player_results FOR INSERT WITH CHECK (true);
-- etc.
```

**Security Considerations**:

**Option A: Keep Permissive (Current)**
```sql
-- Allow all operations for anyone with the anon key
FOR SELECT USING (true)
FOR INSERT WITH CHECK (true)
FOR UPDATE USING (true)
FOR DELETE USING (true)
```

**Pros**: Simple, works immediately
**Cons**: Anyone with your anon key can read/write all data
**Use when**: Private project, anon key kept secret

**Option B: Read-Only Public, Write Restricted**
```sql
-- Public can read, only authenticated users can write
CREATE POLICY "Public read access" ON player_results FOR SELECT USING (true);
CREATE POLICY "Authenticated write" ON player_results FOR INSERT
  WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "Authenticated update" ON player_results FOR UPDATE
  USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated delete" ON player_results FOR DELETE
  USING (auth.role() = 'authenticated');
```

**Pros**: Safe for public streaming overlays
**Cons**: Requires authentication for scraper
**Use when**: Building public-facing overlay

**Option C: Service Role Only**
```sql
-- Only service role can write, public can read
CREATE POLICY "Public read" ON player_results FOR SELECT USING (true);
CREATE POLICY "Service role write" ON player_results FOR INSERT
  WITH CHECK (auth.role() = 'service_role');
```

**Pros**: Most secure for writes
**Cons**: Must use service role key in scraper (not anon key)
**Use when**: Production deployment

**Recommendation for Now**: Keep **Option A** (permissive) while testing, plan to upgrade to **Option B** or **Option C** before going live.

**Implementation Steps**:

1. **Review Current Policies**
   - Check Supabase dashboard → Authentication → Policies
   - Verify all three tables have policies

2. **Test with Anon Key**
   ```bash
   # In realtime_main.py, verify connection works
   python app/realtime_main.py
   # Should see "✓ Database connection successful"
   ```

3. **Add API Key Management to .env**
   ```bash
   # .env
   SUPABASE_URL=https://xxx.supabase.co
   SUPABASE_KEY=eyJ...  # anon key for now
   # SUPABASE_SERVICE_KEY=eyJ...  # for later if using Option C
   ```

4. **Document Your Choice**
   - Add comment to `.env` explaining which policy option you chose
   - Note any plans to change before production

**Testing**:
- Verify scraper can insert data
- Check overlay can read data
- Confirm unauthorized requests are blocked (if using restricted policies)

**Dependencies**: None (should be done first)

**Time Estimate**: 15-30 minutes

---

### Phase 1: Basic Game Status Population

#### Task 1.1: Infer Games from Player Picks ⏳
**Priority**: High
**Effort**: Medium
**Status**: Not Started

**Description**: When saving player picks, automatically create/update `game_status` records by inferring matchups from the picks data.

**Approach**:
- Parse all picks for a week to identify unique teams
- Match teams into games (requires mapping team → opponent)
- Create `game_status` records with basic info

**Challenges**:
- Need to determine home vs away team (may require external data source)
- No direct game time information from CBS scraper
- Team matchup pairing logic needed

**Implementation**:
```python
# In database.py save_results()
def _infer_games_from_picks(self, picks_data, week_number):
    """
    Infer game matchups from player picks.
    Returns list of game records.
    """
    # Group picks by team
    teams_picked = set()
    for pick in picks_data:
        teams_picked.add(pick['team'])

    # TODO: Map teams to their opponents for this week
    # TODO: Determine home/away
    # TODO: Get scheduled game times
```

**Dependencies**: None

**Testing**:
- Verify all games for a week are created
- Check no duplicate games
- Validate team pairings are correct

---

#### Task 1.2: Calculate Viewer Interest Score 📊
**Priority**: Medium
**Effort**: Medium
**Status**: Not Started

**Description**: Calculate `viewer_interest` based on pick variance - games with diverse opinions are more interesting.

**Problem**: Each game will have exactly 32 picks (one per player), so simple count is meaningless.

**Better Approach - Pick Variance/Controversy**:

Games are interesting when:
1. **Split decisions**: 50/50 split on who will win
2. **High confidence disagreement**: Some pick Team A with high confidence, others pick Team B with high confidence
3. **Contrarian high stakes**: One player goes against the field with high confidence

**Algorithm Options**:

**Option A: Confidence Standard Deviation**
```python
def _calculate_viewer_interest(self, game, all_picks):
    """
    Measure spread of confidence points on each side.
    High variance = interesting game
    """
    home_confidences = [p.conf for p in picks if p.team == game.home]
    away_confidences = [p.conf for p in picks if p.team == game.away]

    # Standard deviation of all confidence levels
    all_conf = home_confidences + away_confidences
    variance = np.std(all_conf)

    return int(variance * 100)  # Scale for display
```

**Option B: Split + Confidence Combo**
```python
def _calculate_viewer_interest(self, game, all_picks):
    """
    Combine pick split with average confidence
    """
    home_picks = [p for p in picks if p.team == game.home]
    away_picks = [p for p in picks if p.team == game.away]

    # How close is the split?
    split_ratio = min(len(home_picks), len(away_picks)) / 32

    # Average confidence on each side
    avg_home_conf = mean([p.conf for p in home_picks])
    avg_away_conf = mean([p.conf for p in away_picks])

    # Interest = split * total confidence
    interest = split_ratio * (avg_home_conf + avg_away_conf)

    return int(interest)
```

**Option C: Contrarian Impact Score**
```python
def _calculate_viewer_interest(self, game, all_picks):
    """
    Flag games where going against consensus could be high impact
    """
    home_picks = [p for p in picks if p.team == game.home]
    away_picks = [p for p in picks if p.team == game.away]

    # Identify consensus side (more picks)
    consensus_side = home_picks if len(home_picks) > len(away_picks) else away_picks
    contrarian_side = away_picks if len(home_picks) > len(away_picks) else home_picks

    # Max contrarian confidence
    max_contrarian_conf = max([p.conf for p in contrarian_side], default=0)

    # Interest = how much is at stake for contrarians
    interest = len(consensus_side) * max_contrarian_conf

    return interest
```

**Recommended: Hybrid Approach**
Combine all three factors:
```python
viewer_interest = (
    split_score * 0.4 +          # 40% weight on even split
    confidence_variance * 0.3 +   # 30% weight on diverse opinions
    contrarian_impact * 0.3       # 30% weight on high-stakes disagreement
)
```

**User-Specific Interest** (separate calculation):

The `viewer_interest` field stores **league-wide** controversy/variance. But for streaming overlays, you'll want **personalized** interest scores.

**Example Scenario**:
> If I choose the Bears for 16 points and everyone else chooses their opponent for 1 point, that game is EXTREMELY interesting to me (high stakes), but low variance for the league (consensus pick).

**Personalized Query** - "Sean's must-watch games":
```sql
SELECT
    g.home_team,
    g.away_team,
    sp.team as my_pick,
    sp.confidence_points as my_confidence,
    COUNT(CASE WHEN op.team != sp.team THEN 1 END) as opponents_against_me,
    AVG(CASE WHEN op.team != sp.team THEN op.confidence_points END) as avg_opponent_confidence,
    -- Personal interest = my stakes * opposition strength
    (sp.confidence_points * COUNT(CASE WHEN op.team != sp.team THEN 1 END)) as personal_interest
FROM game_status g
JOIN player_picks sp ON
    sp.season = g.season AND
    sp.week_number = g.week_number AND
    (sp.team = g.home_team OR sp.team = g.away_team)
    AND sp.player_name = 'Sean Becker'
JOIN player_picks op ON
    op.season = g.season AND
    op.week_number = g.week_number AND
    (op.team = g.home_team OR op.team = g.away_team)
    AND op.player_name != 'Sean Becker'
GROUP BY g.home_team, g.away_team, sp.team, sp.confidence_points
ORDER BY personal_interest DESC
LIMIT 3;
```

**Output Example**:
```
Game: CHI @ DET
My pick: CHI (16 pts)
Opponents against me: 31 (avg confidence: 1.2 pts)
Personal interest: 496  (16 × 31)
Reason: High stakes contrarian - if I'm right, massive gain!

Game: KC @ BUF
My pick: KC (12 pts)
Opponents against me: 15 (avg confidence: 8.5 pts)
Personal interest: 180  (12 × 15)
Reason: Competitive game with significant opposition

Game: LAR @ SF
My pick: LAR (3 pts)
Opponents against me: 8 (avg confidence: 4.2 pts)
Personal interest: 24   (3 × 8)
Reason: Low stakes for me
```

**Overlay Display**:
```
🔥 SEAN'S MUST-WATCH GAMES 🔥
1. CHI @ DET - You vs The Field (16 pts at risk!)
2. KC @ BUF - High Stakes Battleground
3. LAR @ SF - Mild Interest
```

**Implementation**:
This doesn't need to be in `game_status` table - can be calculated on-demand for overlay queries. The league-wide `viewer_interest` helps casual viewers find exciting games; personal interest helps each player track their critical games.

**Implementation Location**: `database.py` - new method called after picks are saved

**Dependencies**: Task 1.1

**Testing**:
- Verify high-variance games score higher
- Check 50/50 splits rank high
- Validate contrarian scenarios flagged correctly

---

#### Task 1.3: Calculate Importance Score 🎯
**Priority**: Medium
**Effort**: Medium
**Status**: Not Started

**Description**: Calculate `importance_score` based on potential point swing impact on league standings.

**Key Insight**: A game is important if the outcome could significantly change standings.

**Algorithm Options**:

**Option A: Simple Confidence Sum**
```python
def _calculate_importance_score(self, game, all_picks):
    """
    Sum all confidence points assigned to this game.
    """
    total_confidence = sum(p.confidence_points for p in all_picks if p.team in [game.home, game.away])
    return total_confidence
```
Pros: Simple, interpretable
Cons: Doesn't account for pick distribution

**Option B: Maximum Potential Swing**
```python
def _calculate_importance_score(self, game, all_picks):
    """
    Calculate max points that could change hands.
    """
    home_picks = [p for p in all_picks if p.team == game.home]
    away_picks = [p for p in all_picks if p.team == game.away]

    # If home wins: away pickers lose their confidence points
    if_home_wins_impact = sum(p.confidence_points for p in away_picks)

    # If away wins: home pickers lose their confidence points
    if_away_wins_impact = sum(p.confidence_points for p in home_picks)

    # Max potential swing
    return max(if_home_wins_impact, if_away_wins_impact)
```
Pros: Captures actual stakes
Cons: Doesn't weight by current standings

**Option C: Weighted by Standings Position (Recommended)**
```python
def _calculate_importance_score(self, game, all_picks, current_standings):
    """
    Weight picks by player's proximity to podium (top 3).
    Leaders' games matter more.
    """
    importance = 0

    for pick in [p for p in all_picks if p.team in [game.home, game.away]]:
        player_rank = current_standings[pick.player_name]['rank']

        # Weight: Leaders (1-3) = 3x, Top 10 = 2x, Others = 1x
        if player_rank <= 3:
            weight = 3.0
        elif player_rank <= 10:
            weight = 2.0
        else:
            weight = 1.0

        importance += pick.confidence_points * weight

    return int(importance)
```
Pros: Focuses on games affecting the race
Cons: Requires current standings, more complex

**Option D: Expected Variance in Final Standings**
```python
def _calculate_importance_score(self, game, all_picks, current_standings):
    """
    Model how many position changes could result from each outcome.
    """
    # Simulate both outcomes
    positions_if_home_wins = simulate_standings(all_picks, game, winner='home')
    positions_if_away_wins = simulate_standings(all_picks, game, winner='away')

    # Count position changes
    position_swaps = count_rank_changes(positions_if_home_wins, positions_if_away_wins)

    return position_swaps * 100  # Scale for display
```
Pros: Most accurate "importance"
Cons: Computationally expensive, requires simulation

**Recommended: Hybrid (B + C)**
Combine potential swing with standings weighting:
```python
importance = max_potential_swing * standings_weight_multiplier
```

**Example**:
- Game 1: Chiefs vs Bills
  - 20 players pick Chiefs (avg confidence: 10), 12 pick Bills (avg confidence: 5)
  - Potential swing if Bills win: 20 players × avg 10 points = 200
  - If top 3 players all picked Chiefs with high confidence: weight = 3x
  - Importance = 200 × 1.5 (weighted avg) = 300

- Game 2: Panthers vs Titans
  - Even 16-16 split, low confidence (avg: 3 each side)
  - Potential swing: 16 × 3 = 48
  - Mixed ranks: weight = 1.2x
  - Importance = 48 × 1.2 = 58

**Implementation Location**: `database.py` - new method called after picks are saved

**Dependencies**: Task 1.1, Task 1.2

**Testing**:
- Manually verify for a sample week
- Check games with leader picks score higher
- Validate even splits with high confidence rank appropriately
- Compare to intuitive "must-watch" list

---

### Phase 2: External Game Data Integration

#### Task 2.1: Integrate ESPN API for Game Schedules 📅
**Priority**: High
**Effort**: High
**Status**: Not Started

**Description**: Fetch NFL game schedules from ESPN API to populate game times and home/away designations.

**API Endpoint**:
```
http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?week={week}&seasontype=2&dates={year}
```

**Data Extracted**:
- Home team
- Away team
- Game time (timestamp)
- Game ID for later score updates

**Implementation**:
```python
# New file: app/game_data_fetcher.py
class ESPNGameDataFetcher:
    def fetch_week_schedule(self, week, season):
        """Fetch game schedule for a week"""

    def parse_game_data(self, response):
        """Parse ESPN API response into game_status records"""
```

**Integration Point**: Call from `realtime_main.py` before scraping player picks

**Dependencies**: None

**Testing**:
- Verify all 16 games appear for a regular week
- Check time zones are correct
- Validate team abbreviations match CBS format

**Related**: You already have `simulator/game_results_fetcher.py` that uses ESPN API - can reuse this pattern!

---

#### Task 2.2: Live Score Updates from ESPN 📡
**Priority**: Medium
**Effort**: High
**Status**: Not Started

**Description**: Periodically fetch live scores and update `game_status` table with current scores and completion status.

**Approach**:
- Reuse ESPN scoreboard API
- Poll every 1-2 minutes during game days
- Update `home_score`, `away_score`, `is_finished`

**Implementation**:
```python
# In game_data_fetcher.py
def fetch_live_scores(self, week, season):
    """Get current scores for all games in a week"""

def update_game_scores(self, db: SupabaseDatabase):
    """Update database with latest scores"""
```

**New Script**: `app/game_score_updater.py` (runs separately)

**Dependencies**: Task 2.1

**Testing**:
- Run during live games
- Verify scores update correctly
- Check is_finished flag set appropriately

---

#### Task 2.3: Mark Pick Correctness Automatically ✅❌
**Priority**: Medium
**Effort**: Medium
**Status**: Not Started

**Description**: Once games finish, automatically mark `player_picks.is_correct` based on game outcomes.

**Logic**:
```python
def mark_pick_correctness(self, week_number, season):
    """
    For each finished game:
    - Determine winner
    - Update all picks for that game
    - Set is_correct = true/false
    """
```

**SQL**:
```sql
-- Find winner of a game
SELECT CASE
    WHEN home_score > away_score THEN home_team
    WHEN away_score > home_score THEN away_team
END as winner
FROM game_status
WHERE is_finished = true;

-- Update picks
UPDATE player_picks
SET is_correct = (team = winner)
WHERE ...
```

**Dependencies**: Task 2.2

**Testing**:
- Run after games complete
- Verify correctness matches actual results
- Check ties handled properly

---

### Phase 3: Real-time Updates & Optimization

#### Task 3.1: Separate Game Score Updater Service 🔄
**Priority**: Low
**Effort**: Medium
**Status**: Not Started

**Description**: Create a separate long-running process to continuously update game scores.

**New File**: `app/game_score_service.py`

**Features**:
- Runs independently of main scraper
- Polls ESPN API every 1-2 minutes on game days
- Only active during NFL game times (Thu/Sun/Mon)
- Updates `game_status` and `player_picks.is_correct`

**Deployment**: Can run as separate systemd service or cron job

**Dependencies**: Task 2.1, Task 2.2, Task 2.3

---

#### Task 3.2: Optimize Importance Score Algorithm 🧮
**Priority**: Low
**Effort**: Medium
**Status**: Not Started

**Description**: Enhance importance score calculation with more sophisticated weighting.

**Improvements**:
1. **Leader Proximity Weight**: Picks from top 5 players count more
2. **Games Remaining Factor**: Later in week = higher importance
3. **Expected Swing**: Model point differential impact
4. **Tiebreaker Scenarios**: Flag games that affect tiebreakers

**Algorithm**:
```python
importance = sum(confidence_points * player_weight * time_weight)
where:
  player_weight = 1.5 if player in top 5 else 1.0
  time_weight = games_remaining / total_games
```

**Dependencies**: Task 1.3

---

#### Task 3.3: Add Opponent Team to Picks During Scraping 🔍
**Priority**: Low
**Effort**: Low
**Status**: Not Started

**Description**: Enhance scraper to capture opponent information if available in CBS UI.

**Current**: Scraper only gets team abbreviation
**Desired**: Also capture opponent team

**Investigation Needed**:
- Check if CBS UI shows opponent
- May require parsing game description text
- Alternative: Infer from schedule after Task 2.1

**Dependencies**: None (standalone improvement)

---

### Phase 4: Advanced Features

#### Task 4.1: Swing Game Predictor 🎲
**Priority**: Low
**Effort**: High
**Status**: Not Started

**Description**: Predict which games will have the biggest impact on final standings.

**Algorithm**:
- Model all possible game outcomes
- Calculate standing changes for each scenario
- Identify games with highest variance

**Use Case**: "If Chiefs win, Bob takes 1st. If they lose, Jason leads by 3."

---

#### Task 4.2: Historical Game Importance Analysis 📈
**Priority**: Low
**Effort**: Medium
**Status**: Not Started

**Description**: Analyze past weeks to validate importance score algorithm.

**Approach**:
- Compare predicted importance vs actual impact
- Tune algorithm weights
- Build "best games of the season" highlights

---

## Implementation Order

**⚠️ REVISED SEQUENCE** (Game data is prerequisite):

### Sprint 0: Game Data Foundation (2-4 hours) ⚡ **DO THIS FIRST**
1. **Task 0.1**: Configure Supabase RLS Policies
   - Review and update Row Level Security policies
   - Ensure policies match your security requirements
   - Test with anon key to verify access

2. **Task 2.1**: ESPN API for schedules and game data
   - Adapt existing `simulator/game_results_fetcher.py`
   - Create `app/game_schedule_fetcher.py`
   - Fetch week's game matchups, times, home/away
   - Populate initial `game_status` records

**Deliverable**: `game_status` table has all games for the week with matchup info

**Why First**: Without game data, you can't group picks by game or calculate any metrics.

---

### Sprint 1: Scoring Algorithms (1-2 days)
1. Task 1.2: Calculate viewer interest (pick variance)
2. Task 1.3: Calculate importance score (potential swing)

**Note**: Task 1.1 (Infer games from picks) is **REPLACED** by Task 2.1 above.

**Deliverable**: `game_status` table has `viewer_interest` and `importance_score` populated

---

### Sprint 2: Live Score Integration (2-3 days)
1. Task 2.2: Live score updates from ESPN
2. Task 2.3: Auto-mark pick correctness
3. Task 3.1: Separate score updater service

**Deliverable**: Real-time score tracking and automated pick validation

---

### Sprint 3: Production Polish (1-2 days)
1. Task 3.2: Optimize importance algorithm
2. Task 3.3: Add opponent data to picks (optional)
3. Testing and validation

**Deliverable**: Production-ready game tracking system

---

### Future Enhancements
- Task 4.1: Swing game predictor
- Task 4.2: Historical analysis

---

### Critical Path Summary

```
Step 0a: Configure RLS Policies (0.1) ← START HERE
   ↓
Step 0b: ESPN API Integration (2.1)
   ↓
Step 1: Scoring Algorithms (1.2, 1.3)
   ↓
Step 2: Live Scores (2.2, 2.3, 3.1)
   ↓
Step 3: Polish & Optimize
```

**Estimated Total Time**: 5-8 days spread over 2-3 weeks

**First Session Checklist**:
- [ ] Task 0.1: Review and set Supabase RLS policies (15-30 min)
- [ ] Task 2.1: Set up ESPN API integration (2-4 hours)
- [ ] Test: Verify game data populates correctly

---

## Dependencies & Prerequisites

**Required**:
- ESPN API access (public, no auth needed)
- Existing `game_results_fetcher.py` can be reference

**Optional**:
- The Odds API (for point spreads, over/under)
- NFL official data (for more detailed stats)

---

## Technical Notes

### ESPN API Response Format
```json
{
  "events": [
    {
      "id": "401671729",
      "name": "Kansas City Chiefs at Buffalo Bills",
      "date": "2025-01-26T23:30Z",
      "competitions": [{
        "competitors": [
          {
            "team": {"abbreviation": "KC"},
            "homeAway": "away",
            "score": "24"
          },
          {
            "team": {"abbreviation": "BUF"},
            "homeAway": "home",
            "score": "27"
          }
        ],
        "status": {
          "type": {
            "completed": true
          }
        }
      }]
    }
  ]
}
```

### Team Abbreviation Mapping
CBS and ESPN may use different abbreviations. Will need mapping:
```python
TEAM_ABBREVIATION_MAP = {
    "KC": "KC",   # Usually same
    "LAR": "LAR",
    # Handle edge cases
}
```

---

## Testing Strategy

1. **Unit Tests**: Test each calculation in isolation
2. **Integration Tests**: Test full pipeline with sample data
3. **Live Test**: Run during actual NFL games
4. **Validation**: Compare importance scores with manual review

---

## Success Metrics

- [ ] `game_status` table populated for current week within 1 minute of scraping
- [ ] `viewer_interest` accurately counts league participation
- [ ] `importance_score` correctly identifies "must-watch" games
- [ ] Live scores update within 2 minutes of actual change
- [ ] Pick correctness marked within 5 minutes of game completion
- [ ] Top 3 important games match manual analysis 80%+ of the time

---

## Questions for User

1. **ESPN API sufficient?** Or prefer different data source?
2. **Score update frequency?** Every 1-2 minutes during games okay?
3. **Importance algorithm preference?** Simple sum or weighted calculation?
4. **Auto-update picks?** Should `is_correct` update automatically or manually triggered?
5. **Streaming integration timeline?** When do you need overlay features?

---

*Last Updated: 2025-10-26*
*Status: Game status table defined but not populated - implementation needed*
