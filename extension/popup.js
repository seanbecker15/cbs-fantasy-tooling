// Popup controller. All page work happens through chrome.scripting on the
// active tab; this file only orchestrates and renders.

const STANDINGS_RE = /^https:\/\/picks\.cbssports\.com\/football\/pickem\/pools\/([^/?#]+)/;
const $ = (id) => document.getElementById(id);
const views = ["offsite", "ready", "working", "results", "error"];

let tab = null;
let shownWeek = null;
let lastData = null;

function show(view) {
  for (const v of views) $(v).hidden = v !== view;
}
function status(text) { $("status").textContent = text; }
function nowLabel() { return new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }); }

// Python's datetime.now().isoformat(): local time, no offset.
function localIso() {
  const d = new Date();
  const p = (n, w = 2) => String(n).padStart(w, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}.${p(d.getMilliseconds(), 3)}000`;
}

// Same shape as cbs_fantasy_tooling.models.PickemResults.to_dict().
function buildExport(week, results) {
  const maxWins = Math.max(...results.map((r) => r.wins));
  const maxPts = Math.max(...results.map((r) => parseInt(r.points, 10) || 0));
  const winners = (f) => results.filter(f).map((r) => r.name).join(", ");
  return {
    timestamp: localIso(),
    week_number: week,
    max_wins: { max_wins: maxWins, players: winners((r) => r.wins === maxWins) },
    max_points: { max_points: maxPts, players: winners((r) => (parseInt(r.points, 10) || 0) === maxPts) },
    results,
  };
}
function buildCsv(results) {
  const lines = ["Name,Points,Wins,Losses"];
  for (const r of results) lines.push(`${r.name},${r.points},${r.wins},${r.losses}`);
  return lines.join("\n") + "\n";
}
function download(filename, mime, text) {
  const url = `data:${mime};charset=utf-8,` + encodeURIComponent(text);
  chrome.downloads.download({ url, filename, saveAs: false });
}

async function inject(func, args = []) {
  const [res] = await chrome.scripting.executeScript({ target: { tabId: tab.id }, func, args });
  return res.result;
}

function setTarget(n) {
  n = Math.max(1, Math.min(18, n));
  $("targetWeek").value = n;
  $("scrape").textContent = `Scrape week ${n}`;
  $("targetHint").textContent =
    shownWeek && n === shownWeek ? "The week the page is showing. Use − and + for another."
    : shownWeek && n > shownWeek ? "A later week than the page is showing; it may not be posted yet."
    : "";
}

function render(data, me) {
  const rows = [...data.results].sort((a, b) => (parseInt(b.points, 10) || 0) - (parseInt(a.points, 10) || 0));
  const exp = buildExport(data.week, data.results);
  $("bonusPoints").textContent = exp.max_points.max_points;
  $("bonusPointsWho").textContent = exp.max_points.players;
  $("bonusWins").textContent = exp.max_wins.max_wins;
  $("bonusWinsWho").textContent = exp.max_wins.players;
  const tbody = $("rows");
  tbody.textContent = "";
  rows.forEach((r, i) => {
    const tr = document.createElement("tr");
    if (me && r.name.trim().toLowerCase() === me.trim().toLowerCase()) tr.className = "me";
    const cells = [
      ["num", String(i + 1)], ["", r.name], ["num pts", r.points], ["num", `${r.wins}–${r.losses}`],
    ];
    for (const [cls, text] of cells) {
      const td = document.createElement("td");
      if (cls) td.className = cls;
      td.textContent = text;
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  });
  $("weekNum").textContent = data.week;
  $("weekSub").textContent = `Scraped ${data.results.length} players at ${nowLabel()}`;
  show("results");
  status(`Week ${data.week} · ${data.results.length} players`);
}

async function scrape() {
  const target = parseInt($("targetWeek").value, 10);
  const me = $("yourName").value;
  chrome.storage.sync.set({ yourName: me });
  show("working");
  $("workingText").textContent = shownWeek === target ? "Reading the standings…" : `Switching to week ${target}…`;
  status("");
  try {
    const data = await inject(runScrape, [target]);
    if (!data || !data.results || data.results.length === 0) throw new Error("empty");
    lastData = data;
    render(data, me);
  } catch (e) {
    const msg = String(e && e.message || e);
    $("errorText").textContent =
      msg.includes("week-not-listed") ? `Week ${target} isn't in the standings dropdown yet.`
      : msg.includes("table-missing") ? "Couldn't find the standings table. Open the Weekly tab on the standings page and try again."
      : msg.includes("empty") ? "The table loaded with no players. Give the page a second and try again."
      : "Something went wrong reading the page. Reload it and try again.";
    show("error");
  }
}

async function init() {
  [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const { yourName = "", poolUrl = "" } = await chrome.storage.sync.get(["yourName", "poolUrl"]);
  $("yourName").value = yourName;

  const m = STANDINGS_RE.exec(tab.url || "");
  if (!m) {
    $("weekSub").textContent = "Not on the standings page";
    $("offsiteHint").textContent = poolUrl ? "" : "Open your pool on picks.cbssports.com once and this will remember it.";
    $("openStandings").disabled = !poolUrl;
    $("openStandings").onclick = () => chrome.tabs.update(tab.id, { url: poolUrl });
    show("offsite");
    return;
  }
  const standingsUrl = `https://picks.cbssports.com/football/pickem/pools/${m[1]}/standings/weekly`;
  chrome.storage.sync.set({ poolUrl: standingsUrl });

  const page = await inject(readPage);
  if (!page.table) {
    $("weekSub").textContent = "This pool page has no standings table";
    $("offsiteHint").textContent = "";
    $("openStandings").onclick = () => chrome.tabs.update(tab.id, { url: standingsUrl });
    show("offsite");
    return;
  }
  if (page.pool) $("poolName").textContent = page.pool;
  shownWeek = page.shown;
  $("weekNum").textContent = shownWeek ?? "–";
  $("weekSub").textContent = "Showing on the page now";
  // Default to the week the page is on: the dropdown is already the user's choice.
  setTarget(shownWeek || 1);
  show("ready");
  status("Ready");
}

$("weekDown").onclick = () => setTarget(parseInt($("targetWeek").value, 10) - 1);
$("weekUp").onclick = () => setTarget(parseInt($("targetWeek").value, 10) + 1);
$("targetWeek").onchange = () => setTarget(parseInt($("targetWeek").value, 10) || 1);
$("scrape").onclick = scrape;
$("retry").onclick = () => show("ready");
$("again").onclick = () => show("ready");
$("saveJson").onclick = () => {
  const exp = buildExport(lastData.week, lastData.results);
  download(`week_${lastData.week}_pickem_results.json`, "application/json", JSON.stringify(exp, null, 2));
  status(`Saved week_${lastData.week}_pickem_results.json to Downloads`);
};
$("saveCsv").onclick = () => {
  download(`week_${lastData.week}_pickem_results.csv`, "text/csv", buildCsv(lastData.results));
  status(`Saved week_${lastData.week}_pickem_results.csv to Downloads`);
};

init();
