# Win Scenario Analyzer

Analyzes which combinations of remaining game outcomes would result in you winning the week, and calculates your probability of winning (assuming all remaining games are 50/50 coin flips).

## Features

1. **Win Combination Finder**: Identifies which specific game outcomes must occur for you to win the week
2. **Win Probability Calculator**: Calculates simple probability assuming 50/50 game outcomes
3. **Detailed Scenario Analysis**: Shows sample winning combinations with required game results
4. **Meta-Analysis TL;DR**: Analyzes ALL winning scenarios to identify critical patterns and shared outcomes

## How It Works

### Algorithm

1. **Load Current State**:
   - Fetches your picks from Supabase `player_picks` table
   - Fetches all opponents' picks
   - Identifies which games are finished (`is_correct != null`) vs pending (`is_correct = null`)

2. **Calculate Current Points**:
   - Sums up points from correct picks that are already finished
   - Identifies pending picks that could still add points

3. **Generate All Scenarios**:
   - For N pending games, generates 2^N possible outcome combinations
   - For each scenario, calculates:
     - Your total points if those outcomes occur
     - Every opponent's total points if those outcomes occur

4. **Count Winning Scenarios**:
   - A scenario is "winning" if your total points > all opponents' total points
   - Ties count as losses (you must have strictly higher points)

5. **Calculate Probability**:
   - Probability = (# winning scenarios) / (# total scenarios)
   - Assumes each game is 50/50 (doesn't use odds/probabilities)

### Example Calculation

Suppose you have:
- 60 points from finished games
- 3 pending games worth: 10 pts, 8 pts, 6 pts

Total scenarios: 2^3 = 8

| Scenario | 10pt game | 8pt game | 6pt game | Your Total | Best Opponent |
|----------|-----------|----------|----------|------------|---------------|
| 1        | Win       | Win      | Win      | 84         | 80            | ✓ You win
| 2        | Win       | Win      | Lose     | 78         | 82            | ✗ Opponent wins
| 3        | Win       | Lose     | Win      | 76         | 82            | ✗ Opponent wins
| 4        | Win       | Lose     | Lose     | 70         | 82            | ✗ Opponent wins
| 5        | Lose      | Win      | Win      | 74         | 82            | ✗ Opponent wins
| 6        | Lose      | Win      | Lose     | 68         | 82            | ✗ Opponent wins
| 7        | Lose      | Lose     | Win      | 66         | 82            | ✗ Opponent wins
| 8        | Lose      | Lose     | Lose     | 60         | 82            | ✗ Opponent wins

Win Probability: 1/8 = 12.5%

## Output Format

### Remaining Games Display

Each pending game is shown in the format: `(Team1 vs. Team2 - PickedTeam) [confidence pts]`

**Format variations:**
- `(BAL vs. NYJ - BAL) [14 pts]` - You picked BAL with 14 confidence points
- `(KC vs. IND - IND) [3 pts]` - You picked IND with 3 confidence points
- `(SF vs. ARI - any)` - You didn't pick either team in this game (or game not in your pool)

This makes it easy to see:
- All remaining games at a glance
- Which teams you have picks on
- How many confidence points are at stake

### Winning Combination Categories

When viewing detailed scenarios (`--detailed` flag), each winning combination shows games in three categories:

**Must win:**
- Games where you **MUST win your pick** for this specific scenario to occur
- You get points from these picks

**Must lose:**
- Games where you **MUST lose your pick** for this specific scenario to occur
- You don't get points from these picks (but you still win overall)

**Any outcome:**
- Games where the **outcome doesn't affect this scenario**
- Either you didn't pick in these games, or they're between other players only

**Example interpretation:**
```
#3: You score 85 pts, opponents max 83 pts
  Must win:
    - (BAL vs. NYJ - BAL) [14 pts]
  Must lose:
    - (GB vs. MIN - GB) [7 pts]
    - (SF vs. CAR - SF) [11 pts]
  Any outcome:
    - (JAC vs. ARI - any)
```

This scenario means:
- You **must** win your BAL pick (14 pts) ✓ Get points
- You **must** lose GB (7 pts) and SF (11 pts) picks ✗ No points
- The JAC/ARI game doesn't matter (doesn't affect outcome)
- Final score: 85 pts total vs 83 pts (best opponent) = You win by 2!

## Usage

### Basic Usage

```bash
python app/win_scenario_analyzer.py --week 12 --player "Your Name"
```

Output:
```
============================================================
WIN SCENARIO ANALYSIS - Week 12
============================================================
Player: Your Name
Current Points: 68

Remaining Games (8):
  (BAL vs. NYJ - BAL) [14 pts]
  (DET vs. NYG - DET) [12 pts]
  (KC vs. IND - KC) [9 pts]
  (LAR vs. TB - LAR) [5 pts]
  (LV vs. CLE - LV) [6 pts]
  (NE vs. CIN - NE) [10 pts]
  (PHI vs. DAL - PHI) [4 pts]
  (SEA vs. TEN - SEA) [13 pts]

Total Possible Scenarios: 256
Winning Scenarios: 47

Win Probability (50/50): 18.36%
============================================================
```

### Detailed Analysis with TL;DR

Show sample winning combinations AND meta-analysis across all scenarios:

```bash
python app/win_scenario_analyzer.py --week 12 --player "Your Name" --detailed
```

Output:
```
============================================================
WIN SCENARIO ANALYSIS - Week 12
============================================================
Player: Your Name
Current Points: 68
Pending Games: 8
Pending Picks: 8

Total Possible Scenarios: 256
Winning Scenarios: 47

Win Probability (50/50): 18.36%
============================================================

SAMPLE WINNING COMBINATIONS:

#1: You score 98 pts, opponents max 96 pts
  Must win:
    - (BAL vs. NYJ - BAL) [14 pts]
    - (BUF vs. HOU - BUF) [8 pts]
    - (DET vs. NYG - DET) [12 pts]
    - (GB vs. MIN - GB) [7 pts]
    - (IND vs. KC - KC) [9 pts]
    - (NE vs. CIN - NE) [10 pts]
    - (SF vs. CAR - SF) [11 pts]
    - (SEA vs. TEN - SEA) [13 pts]

#2: You score 96 pts, opponents max 95 pts
  Must win:
    - (BAL vs. NYJ - BAL) [14 pts]
    - (BUF vs. HOU - BUF) [8 pts]
    - (DET vs. NYG - DET) [12 pts]
    - (IND vs. KC - KC) [9 pts]
    - (NE vs. CIN - NE) [10 pts]
    - (SF vs. CAR - SF) [11 pts]
    - (SEA vs. TEN - SEA) [13 pts]
  Must lose:
    - (GB vs. MIN - GB) [7 pts]

#3: You score 85 pts, opponents max 83 pts
  Must win:
    - (BAL vs. NYJ - BAL) [14 pts]
    - (DET vs. NYG - DET) [12 pts]
    - (SEA vs. TEN - SEA) [13 pts]
  Must lose:
    - (BUF vs. HOU - BUF) [8 pts]
    - (GB vs. MIN - GB) [7 pts]
    - (IND vs. KC - KC) [9 pts]
    - (NE vs. CIN - NE) [10 pts]
    - (SF vs. CAR - SF) [11 pts]
  Any outcome:
    - (JAC vs. ARI - any)
    - (PHI vs. DAL - any)

... (showing 20 of 47 winning combinations)
------------------------------------------------------------

============================================================
TL;DR - META-ANALYSIS ACROSS ALL WINNING SCENARIOS
============================================================

🎯 CRITICAL - Must ALWAYS win these:
   (BAL vs. NYJ - BAL) [14 pts] (100% of winning scenarios)
   (DET vs. NYG - DET) [12 pts] (100% of winning scenarios)
   (SEA vs. TEN - SEA) [13 pts] (100% of winning scenarios)

⭐ IMPORTANT - Should win these (75%+):
   (BUF vs. HOU - BUF) [8 pts] (87% need win)
   (IND vs. KC - KC) [9 pts] (79% need win)

🔀 VARIABLE - Mixed outcomes:
   (GB vs. MIN - GB) [7 pts]
      Win: 45% | Lose: 55%
   (NE vs. CIN - NE) [10 pts]
      Win: 62% | Lose: 38%
   (SF vs. CAR - SF) [11 pts]
      Win: 51% | Lose: 49%

💤 IRRELEVANT - Outcome doesn't matter:
   (JAC vs. ARI - any)
   (PHI vs. DAL - any)

============================================================
```

## Understanding the TL;DR Meta-Analysis

The TL;DR section analyzes **ALL winning scenarios** (not just the 20 samples) to identify patterns. This tells you which games are critical across all possible paths to victory.

### Category Definitions

**🎯 CRITICAL - Must ALWAYS win (100%)**
- These games appear in the "Must win" category in **every single winning scenario**
- If you lose ANY of these, you **cannot win the week** under any circumstances
- **Action**: These are your absolute must-wins. Watch them closely.

**⭐ IMPORTANT - Should win (75-99%)**
- These games must be won in **most** winning scenarios
- Losing these dramatically reduces your win probability
- **Action**: Treat these almost as critically as 100% games

**❌ CRITICAL - Must ALWAYS lose (100%)**
- These games appear in the "Must lose" category in **every single winning scenario**
- This seems counterintuitive, but it means winning these games **prevents you from winning the week**
- **Reason**: Usually means you're so far behind that getting these points pushes you over opponents who also have them, but doesn't give you enough to win
- **Action**: Accept that these picks are wrong. Focus on other games.

**⚠️ IMPORTANT - Should lose (75-99%)**
- Similar to "Must ALWAYS lose" but with slightly more flexibility
- Winning these hurts your chances in most scenarios
- **Action**: Don't count on points from these picks

**🔀 VARIABLE - Mixed outcomes (25-74%)**
- These games appear in both "Must win" and "Must lose" categories across different scenarios
- Your win path depends on **combinations** - winning some while losing others
- **Example**: "Win: 62% | Lose: 38%" means 62% of winning scenarios require you to win this game, 38% require you to lose it
- **Action**: These are pivot points. The actual outcome determines which path to victory remains open.

**💤 IRRELEVANT - Doesn't matter (100%)**
- The outcome of these games has **zero impact** on whether you win
- Usually games you didn't pick, or games where both outcomes lead to the same result
- **Action**: Ignore these completely. Focus energy elsewhere.

### Strategic Interpretation

**Example 1: Clear Path**
```
🎯 CRITICAL - Must ALWAYS win: 3 games
⭐ IMPORTANT - Should win: 2 games (87%, 79%)
💤 IRRELEVANT: 8 games
```
**Interpretation**: Clear and simple. Win your 5 key games and you're golden. The other 8 don't matter.

**Example 2: Uphill Battle**
```
❌ CRITICAL - Must ALWAYS lose: 5 games (worth 50 pts total)
🎯 CRITICAL - Must ALWAYS win: 2 games (worth 25 pts total)
```
**Interpretation**: You're likely behind. You need to lose 5 picks (sacrificing 50 points) and hope others do worse. Your only win paths involve scraping together points from 2 key games.

**Example 3: Complex Scenario**
```
🎯 CRITICAL - Must ALWAYS win: 1 game [14 pts]
🔀 VARIABLE - Mixed outcomes:
   Game A: Win 60% | Lose 40%
   Game B: Win 40% | Lose 60%
   Game C: Win 50% | Lose 50%
```
**Interpretation**: You must win your 14-pointer, but the path to victory branches based on Games A/B/C. Winning A opens certain paths, losing it opens others. This is a complex week where multiple combinations work.

### Using TL;DR for Live Game Tracking

As games finish, use the TL;DR to understand your situation:

1. **CRITICAL game finishes as a LOSS**: Your win probability drops to 0%. The week is over.
2. **CRITICAL game finishes as a WIN**: Remove it from the list. Recalculate if desired.
3. **VARIABLE game finishes**: Some winning paths close, others remain open. Your probability shifts.
4. **IRRELEVANT game finishes**: Your probability unchanged.

The TL;DR gives you the **strategic overview** while the detailed scenarios show **specific paths**.

## Strategic Pick Optimization

### The Optimization Mindset

This tool analyzes picks **after you've made them**, but the same framework can guide **pick selection** to maximize your winning scenarios.

### Key Insight: Maximize Scenario Count vs. Expected Value

Traditional strategy (like the simulator's Chalk-MaxPoints) maximizes **expected points**. But in head-to-head competition, you want to maximize **winning scenarios** - the number of outcome combinations where you beat everyone else.

**Trade-off Example:**
```
Strategy A (Chalk): 83.7 expected points, 47 winning scenarios (18%)
Strategy B (Differentiated): 81.2 expected points, 89 winning scenarios (35%)
```

Strategy B sacrifices 2.5 expected points but **doubles your win probability** because it creates more paths to victory by differentiating from competitors.

### Framework for Pick Optimization

#### 1. Model Your Competition

Before choosing picks, understand what your opponents will likely do:

**Scenario A: Everyone picks chalk**
- If 31 opponents all pick the same teams, you need to **differentiate**
- Picking the same teams as everyone means you need to win ALL high-value games
- Picking different teams creates scenarios where you win even if favorites lose

**Scenario B: Mixed field**
- Some opponents pick chalk, others pick contrarian
- Your strategy depends on your position (ahead vs. behind)

**Scenario C: You know opponent picks**
- If you can see competitor picks before finalizing yours, optimal strategy changes
- You can surgically pick games that maximize winning scenarios against the known field

#### 2. Differentiation Strategies

**Conservative Differentiation (Middle-to-Top Pack)**
- Pick the same **teams** as the field (Ravens, Lions, etc.)
- Differentiate on **confidence allocation** (Random-MidShuffle)
- **Effect**: Creates winning scenarios where you win the same games but allocate points differently
- **Win scenarios**: Moderate increase (20-40% more scenarios)

**Moderate Differentiation (Middle of Pack)**
- Flip 2-3 coin-flip games (50-55% favorites) to underdogs
- Keep high-probability favorites (80%+ games) the same
- **Effect**: Opens entirely new scenario branches
- **Win scenarios**: Significant increase (50-100% more scenarios)

**Aggressive Differentiation (Far Behind)**
- Pick multiple underdogs in medium-confidence games
- Accept lower expected value for higher variance
- **Effect**: Most scenarios lose, but creates rare scenarios where you win big
- **Win scenarios**: Count may decrease, but upside scenarios increase

#### 3. Practical Optimization Process

**Step 1: Get the baseline (Chalk)**
```bash
# Simulate everyone picking chalk
python simulator/main.py --week 12
# Note the picks: Ravens, Seahawks, Lions, etc.
```

**Step 2: Test alternative strategies**

Test different pick sets to see which maximizes winning scenarios:

```bash
# Test Strategy A: Pure Chalk
python app/win_scenario_analyzer.py --week 12 --player "You" --detailed
# Note: X winning scenarios

# Test Strategy B: Chalk with confidence shuffle
# (Manually adjust picks in database or via custom input)
# Note: Y winning scenarios

# Test Strategy C: Flip 2 coin-flip games
# Note: Z winning scenarios
```

**Step 3: Choose strategy with most winning scenarios**

If Z > Y > X, pick Strategy C even if expected value is lower.

#### 4. Advanced: Scenario Dependency Analysis

The most powerful insight is understanding **which games create branching scenarios**:

**Example Analysis:**
```
Game A (Ravens 88%): Everyone has Ravens high
Game B (49ers 74%): Everyone has 49ers medium-high
Game C (Bears 56%): Mixed - 50% pick Bears, 50% pick Steelers
```

**Strategic implication:**
- Games A & B: Little differentiation value (everyone picks the same)
- Game C: **High differentiation value** - picking the opposite of half the field creates unique winning scenarios

**Optimal pick**:
- A: Ravens (same as field - must win to stay competitive)
- B: 49ers (same as field - must win to stay competitive)
- C: Steelers (opposite of ~50% of field - creates differentiation)

This creates scenarios where:
- If Steelers win: You beat the 50% who picked Bears
- If Ravens + 49ers win and others' picks fail: You beat everyone

### Example: Field-Aware Pick Selection

**Scenario: You're 3rd place, 15 points behind leader**

**Leader's likely picks (Chalk):**
- Ravens (14), Seahawks (13), Lions (12), 49ers (11), Rams (10)

**Your optimization goal:**
- Maximize scenarios where you beat the leader

**Bad strategy (copy the leader):**
- Pick same teams, same confidence
- **Result**: 0 winning scenarios (you're 15 points behind, need them to lose picks)

**Good strategy (strategic differentiation):**
- Keep the 80%+ favorites (Ravens, Seahawks, Lions) - can't afford to lose if they win
- Flip 2-3 medium-confidence games (49ers, Rams, Packers)
- **Result**: Creates scenarios where leader loses 11+10+9=30 points, you gain 30 points = swing of 60

**Win scenario calculation:**
```
If leader picks: 49ers (11), Rams (10), Packers (9)
If you pick: Panthers (11), Bucs (10), Vikings (9)

Scenarios where you win:
- Leader's 3 picks all lose = lose 30 pts
- Your 3 picks all win = gain 30 pts
- Net swing: 60 points (closes your 15-point gap)
```

### When to Optimize for Scenarios vs. Expected Value

**Optimize for Expected Value (use simulator's chalk):**
- You're leading by 10+ points
- Early in the season (weeks 1-6)
- You want to minimize variance

**Optimize for Winning Scenarios (use differentiation):**
- You're behind by 5+ points
- Late in the season (weeks 12-18) - need to catch up
- You want to maximize variance and create unique win paths
- You know your competitors' picks

### Building a Pick Optimizer Tool

The current tool analyzes **after picks are made**. To optimize **before picking**, you'd need:

1. **Input**: Expected competitor picks (or assume all chalk)
2. **Process**: Test different pick combinations for you
3. **Output**: Strategy that maximizes winning scenarios

**Would you like me to build a pick optimizer that:**
- Loads competitor picks from Supabase (or assumes chalk)
- Tests different pick strategies for you
- Shows which strategy maximizes winning scenarios?

This would be a new tool: `app/pick_optimizer.py` that finds the optimal picks given the field composition.

### Use USER_NAME from .env

If `USER_NAME` is set in your `.env` file, you can omit the `--player` flag:

```bash
# .env file contains: USER_NAME=Sean Smith
python app/win_scenario_analyzer.py --week 12
```

### Different Season

```bash
python app/win_scenario_analyzer.py --week 12 --player "Your Name" --season 2024
```

## Requirements

### Environment Variables

Required in `.env`:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-or-service-key
USER_NAME=Your Name  # Optional, can use --player flag instead
```

### Data Requirements

The tool requires data to be populated in Supabase:

1. **player_picks table**: Must have picks for the specified week
2. **is_correct field**: Must be updated as games finish (null = pending, true = won, false = lost)

The `app/main.py` scraper and `app/game_status_fetcher.py` handle populating this data.

## Interpretation

### Win Probability

The probability shown assumes **all remaining games are 50/50 coin flips**. This is a simplification:

- **Actual probabilities vary**: A 90% favorite is not a coin flip
- **Useful for quick assessment**: Gives you a rough idea of your chances
- **For precise probabilities**: Use the confidence pool simulator with real odds

### Strategic Insights

**High Probability (>70%)**:
- You're in great shape
- Most scenarios result in you winning
- Consider playing safe with remaining picks

**Medium Probability (30-70%)**:
- Outcome is uncertain
- A few key games will determine the winner
- Review which specific games you need to win

**Low Probability (<30%)**:
- You need several upsets to win
- Review the detailed combinations to see what needs to happen
- Consider whether you want to take risks in future weeks

### When Probability Changes

Your win probability changes when:
- A pending game finishes (reduces # of scenarios)
- Your pick wins (increases points, may increase winning scenarios)
- Your pick loses (decreases potential points, may decrease winning scenarios)

## Example Scenarios

### Scenario 1: Crushing It
```
Current Points: 85
Pending Games: 3
Pending Picks: 3 (worth 5, 3, 1 points)

Total Scenarios: 8
Winning Scenarios: 7
Win Probability: 87.5%
```
**Interpretation**: You only lose if you go 0-3 on remaining picks. Very strong position.

### Scenario 2: Tight Race
```
Current Points: 72
Pending Games: 6
Pending Picks: 6 (worth 14, 12, 10, 6, 4, 2 points)

Total Scenarios: 64
Winning Scenarios: 31
Win Probability: 48.44%
```
**Interpretation**: Essentially a coin flip. High-value picks matter most.

### Scenario 3: Need Miracles
```
Current Points: 60
Pending Games: 5
Pending Picks: 5 (worth 8, 6, 4, 3, 1 points)

Total Scenarios: 32
Winning Scenarios: 3
Win Probability: 9.38%
```
**Interpretation**: You need to win almost all remaining games AND opponents need to lose theirs.

## Limitations

1. **50/50 Assumption**: Doesn't account for actual game probabilities (favorites vs underdogs)
2. **No Bonus Modeling**: Doesn't model weekly bonuses (Most Wins, Most Points) if your league uses them
3. **Ties**: Treats ties as losses (you must strictly win to count as a winning scenario)
4. **Large Scenarios**: With 14+ pending games, 2^14 = 16,384+ scenarios (may be slow)

## Advanced Usage

### Programmatic Usage

You can import and use the analyzer in Python scripts:

```python
from win_scenario_analyzer import WinScenarioAnalyzer

analyzer = WinScenarioAnalyzer(
    supabase_url="https://your-project.supabase.co",
    supabase_key="your-key",
    season=2025
)

result = analyzer.analyze_win_scenarios(
    week=12,
    target_player="Your Name",
    detailed=True
)

print(f"Win probability: {result['win_percentage']}")
print(f"Winning scenarios: {result['winning_scenarios']} / {result['total_scenarios']}")
```

### Integration with Scraper

The scraper (`app/main.py`) automatically updates `is_correct` in the database as games finish, so you can run the win analyzer at any point during the week to see your live win probability.

## Troubleshooting

### "Player not found in week data"
- Check that the player name matches exactly (case-sensitive)
- Verify that data exists in Supabase for that week
- Run the scraper to populate the week's data first

### "No pending games"
- All games are finished for the week
- The tool will show if you won or lost

### Probability seems wrong
- Remember: assumes 50/50 for all games
- For more accurate probabilities, use the simulator with real odds
- Check that `is_correct` is being updated properly in the database
