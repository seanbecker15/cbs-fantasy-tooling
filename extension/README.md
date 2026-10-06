# 3G's Pool Standings — Chrome extension

Scrapes one week of the pool's standings from CBS Pick'em and saves it in the
format the analysis pipeline reads. It runs inside your own signed-in Chrome,
so there is no login, no password stored anywhere, and nothing for CBS's
bot check to block.

No build step, no npm, no external code. The folder is the extension.

## Install (once, ~1 minute)

1. In Chrome, open **chrome://extensions**.
2. Turn on **Developer mode** (toggle, top right).
3. Click **Load unpacked** and choose this folder:
   `~/Code/cbs-fantasy-tooling/extension`
4. Click the puzzle-piece icon in the toolbar and **pin** "3G's Pool Standings".

That's it. Chrome keeps it installed; you don't need to repeat this.

## Use (every Tuesday)

1. Open the pool's **Standings → Weekly** page on picks.cbssports.com.
   (If you open the extension anywhere else, it offers to take you there.)
2. Click the extension icon. It shows the week the page is on and defaults to
   scraping the **last finished week** — usually what you want.
3. Click **Scrape week N**. It switches the page to that week, reads every
   player's row, and shows the standings with the two bonus winners.
4. Click **Save JSON**. The file lands in your Downloads folder as
   `week_N_pickem_results.json`.
5. In a terminal, email the league:

   ```
   cbs-publish
   ```

   That picks up the newest results file from Downloads, copies it into the
   season's data folder, and sends the weekly email. To publish a specific
   file instead: `cbs-publish ~/Downloads/week_4_pickem_results.json`.

Your own row is highlighted — set your name once in the popup and it's remembered.

## What it saves

Exactly what the Python scraper saves, so nothing downstream changes:

- `week_N_pickem_results.json` — every player's points, wins, losses, and
  all picks with confidence values, plus the most-points and most-wins winners.
- `week_N_pickem_results.csv` — the same table, one row per player.

## If something goes wrong

| What you see | What to do |
|---|---|
| "Not on the standings page" | Click **Open weekly standings**, or go there yourself. |
| "Week N isn't in the standings dropdown yet" | CBS hasn't published that week. Try the week before. |
| "Couldn't find the standings table" | You're on the Overall tab. Click **Weekly** on the page and try again. |
| Scrape returns 0 players | The page was mid-load. Wait a second and click again. |
| Row count looks wrong | Scroll the page's table once so it fully renders, then scrape again. |

Nothing here sends email or writes outside your Downloads folder; `cbs-publish`
does the publishing, and only after validating the file.

## Updating

Pull the repo. If `extension/` changed, open **chrome://extensions** and click
the **reload** icon on the extension's card.
