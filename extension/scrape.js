// Runs INSIDE the CBS standings page via chrome.scripting.executeScript.
// It must be self-contained: executeScript serialises the function, so no
// references to anything outside it. Logic mirrors
// cbs_fantasy_tooling/ingest/cbs_sports/scrape.py exactly, and a test pins
// the two SVG path constants to the Python ones.

async function runScrape(targetWeek) {
  const ICON_CHECK = "M12 22c5.5 0 10-4.5 10-10S17.5 2 12 2 2 6.5 2 12s4.5 10 10 10zm-1-5.2c-.4 0-.8-.2-1.1-.6l-2.2-2.6c-.2-.3-.3-.5-.3-.8 0-.6.5-1.1 1.1-1.1.3 0 .6.1.9.4l1.6 2 3.7-5.8c.3-.4.6-.6.9-.6.6 0 1.1.4 1.1 1 0 .2-.1.5-.3.7L12 16.2c-.3.3-.6.6-1 .6z";
  const ICON_X = "M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm4.3 14.3c-.4.4-1 .4-1.4 0L12 13.4l-2.9 2.9c-.4.4-1 .4-1.4 0-.4-.4-.4-1 0-1.4l2.9-2.9-2.9-2.9c-.4-.4-.4-1 0-1.4.4-.4 1-.4 1.4 0l2.9 2.9 2.9-2.9c.4-.4 1-.4 1.4 0 .4.4.4 1 0 1.4L13.4 12l2.9 2.9c.4.4.4 1 0 1.4z";
  const TABLE = 'table[aria-label="Weekly Standings"]';
  const COMBO = 'div[role="combobox"].MuiSelect-select';
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));

  const comboText = () => {
    const c = document.querySelector(COMBO);
    return c ? c.innerText.trim() : "";
  };
  const rowCount = () => document.querySelectorAll(TABLE + " tbody tr").length;

  async function selectWeek(n) {
    const want = "Week " + n;
    if (comboText() === want) return;
    const combo = document.querySelector(COMBO);
    if (!combo) throw new Error("week-selector-missing");
    // MUI's Select opens on mousedown, not click.
    combo.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    let option = null;
    for (let i = 0; i < 20 && !option; i++) {
      await wait(150);
      option = [...document.querySelectorAll('li[role="option"]')].find(
        (li) => li.innerText.trim() === want
      );
    }
    if (!option) {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
      throw new Error("week-not-listed:" + n);
    }
    option.click();
    for (let i = 0; i < 40 && comboText() !== want; i++) await wait(250);
    if (comboText() !== want) throw new Error("week-did-not-change:" + n);
  }

  // Wait for the table body to render and settle (same row count on two polls).
  // Needed even when no week switch happens: on a fresh page load the table
  // skeleton exists before any rows do.
  async function settle() {
    let prev = -1;
    for (let i = 0; i < 40; i++) {
      const n = rowCount();
      if (n > 0 && n === prev) return;
      prev = n;
      await wait(300);
    }
  }

  function scrapeTable() {
    const table = document.querySelector(TABLE);
    if (!table) throw new Error("table-missing");
    const results = [];
    for (const tr of table.querySelectorAll("tbody tr")) {
      const cells = [...tr.querySelectorAll("td")];
      if (cells.length < 3) continue;
      const nameSpans = cells[0].querySelectorAll("span");
      if (nameSpans.length < 2) continue;
      const name = nameSpans[1].innerText.trim();
      const points = cells[1].innerText.trim();
      let wins = 0;
      let losses = 0;
      const picks = [];
      for (const cell of cells.slice(3)) {
        const path = cell.querySelector("path");
        const d = path ? path.getAttribute("d") : null;
        if (d === ICON_CHECK) wins += 1;
        else if (d === ICON_X) losses += 1;
        const spans = cell.querySelectorAll("span");
        if (spans.length === 2) {
          const parts = (spans[0].innerText.trim() + " " + spans[1].innerText.trim()).split(" ");
          if (parts.length === 2) picks.push({ team: parts[0], points: parts[1].replace(/[()]/g, "") });
        }
      }
      results.push({ name, points, wins, losses, picks });
    }
    return results;
  }

  const shownBefore = parseInt((comboText().match(/\d+/) || [])[0], 10);
  if (targetWeek) await selectWeek(targetWeek);
  await settle();
  const results = scrapeTable();
  const week = parseInt((comboText().match(/\d+/) || [])[0], 10);
  return { week, shownBefore, results, url: location.href };
}

// Probe: what week is the page showing, is the table there, and has that
// week been scored? On Tuesday the page opens on the in-progress week with
// everyone at 0, which is not the week anyone wants to save.
async function readPage() {
  const TABLE = 'table[aria-label="Weekly Standings"]';
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const c = document.querySelector('div[role="combobox"].MuiSelect-select');
  const shown = c ? parseInt((c.innerText.match(/\d+/) || [])[0], 10) : null;
  const table = !!document.querySelector(TABLE);
  const pool = (document.querySelector("h1, h2") || {}).innerText || "";
  let rows = [];
  if (table) {
    let prev = -1;
    for (let i = 0; i < 40; i++) {
      rows = [...document.querySelectorAll(TABLE + " tbody tr")];
      if (rows.length > 0 && rows.length === prev) break;
      prev = rows.length;
      await wait(300);
    }
  }
  const hasResults = rows.some((tr) => {
    const cells = tr.querySelectorAll("td");
    return cells.length > 1 && (parseInt(cells[1].innerText.trim(), 10) || 0) > 0;
  });
  return { shown, table, hasResults, rows: rows.length, pool: pool.trim(), url: location.href };
}
