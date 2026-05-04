#!/usr/bin/env python3
"""
actualitzar_lligues.py
Genera lligues_europees.html amb les classificacions actuals
de les 7 principals lligues europees via API football-data.org.

Layout:
- Pestanya Resum (bandera UE) amb classificació pivotada per posició × lliga.
- Pestanya per cada lliga amb estadístiques completes (PJ, G, E, P, GF, GC, DG, Pts).
- Detecció automàtica de campió (per `season.winner` o per comprovació matemàtica)
  amb badge, banner i icona de copa.

Ús: python3 actualitzar_lligues.py
Requereix: pip install requests
API key gratuïta: https://www.football-data.org/client/register
"""

import json
import os
import time
from datetime import datetime

import requests

API_KEY = os.getenv("FOOTBALL_API_KEY", "")
BASE_URL = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": API_KEY}

LLIGUES = [
    {"id": "PD",  "name": "La Liga",        "country": "Espanya",       "cc": "es",     "cl": 4, "el": 1, "cf": 1, "rel": 3},
    {"id": "PL",  "name": "Premier League", "country": "Anglaterra",    "cc": "gb-eng", "cl": 4, "el": 1, "cf": 1, "rel": 3},
    {"id": "BL1", "name": "Bundesliga",     "country": "Alemanya",      "cc": "de",     "cl": 4, "el": 1, "cf": 1, "rel": 3},
    {"id": "SA",  "name": "Serie A",        "country": "Itàlia",        "cc": "it",     "cl": 4, "el": 1, "cf": 1, "rel": 3},
    {"id": "FL1", "name": "Ligue 1",        "country": "França",        "cc": "fr",     "cl": 3, "el": 1, "cf": 1, "rel": 2},
    {"id": "PPL", "name": "Primeira Liga",  "country": "Portugal",      "cc": "pt",     "cl": 3, "el": 1, "cf": 1, "rel": 3},
    {"id": "DED", "name": "Eredivisie",     "country": "Països Baixos", "cc": "nl",     "cl": 1, "el": 1, "cf": 2, "rel": 2},
]

OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lligues_europees.html")

# Format dates in Catalan
MESOS_CA = ["gener", "febrer", "març", "abril", "maig", "juny",
            "juliol", "agost", "setembre", "octubre", "novembre", "desembre"]


def fetch_standings(code):
    url = f"{BASE_URL}/competitions/{code}/standings"
    r = requests.get(url, headers=HEADERS, timeout=15)
    if r.status_code == 429:
        print(f"  ⚠️  Rate limit per {code}")
        return None
    if r.status_code != 200:
        print(f"  ⚠️  Error {r.status_code} per {code}")
        return None
    payload = r.json()
    table = []
    for s in payload.get("standings", []):
        if s.get("type") == "TOTAL":
            table = s.get("table", [])
            break
    return {"season": payload.get("season", {}), "table": table}


def detect_champion(table, season):
    """Returns (name, info_dict) if champion is decided, else (None, None).

    Info dict may contain keys: name, date.
    Champion is detected from API season.winner if present; otherwise via
    mathematical certainty (leader pts > 2nd pts + 3 * 2nd remaining matches).
    """
    winner = season.get("winner")
    if isinstance(winner, dict) and winner.get("name"):
        return display_name(winner)
    if len(table) < 2:
        return None
    leader = table[0]
    second = table[1]
    leader_pts = leader.get("points", 0)
    second_pts = second.get("points", 0)
    total_clubs = len(table)
    total_matchdays = (total_clubs - 1) * 2
    second_played = second.get("playedGames", 0)
    second_remaining = max(0, total_matchdays - second_played)
    if leader_pts > second_pts + 3 * second_remaining:
        return display_name(leader.get("team", {}))
    return None


def display_name(team):
    """Prefer API shortName (e.g. 'Barça') over the long name ('FC Barcelona')."""
    return team.get("shortName") or team.get("name") or ""


def build_data():
    leagues_out = []
    data_out = {}
    for lg in LLIGUES:
        print(f"  Obtenint {lg['name']}...")
        result = fetch_standings(lg["id"])
        lg_out = {k: lg[k] for k in ("id", "name", "country", "cc", "cl", "el", "cf", "rel")}
        if not result or not result["table"]:
            leagues_out.append(lg_out)
            data_out[lg["id"]] = {"standings": []}
            time.sleep(6)
            continue
        champion = detect_champion(result["table"], result["season"])
        if champion:
            lg_out["champion"] = {"name": champion}
        leagues_out.append(lg_out)
        standings = []
        for row in result["table"]:
            team = row.get("team", {})
            standings.append({
                "pos": row.get("position"),
                "name": display_name(team),
                "logo": team.get("crest"),
                "gp": row.get("playedGames"),
                "w": row.get("won"),
                "d": row.get("draw"),
                "l": row.get("lost"),
                "gf": row.get("goalsFor"),
                "ga": row.get("goalsAgainst"),
                "gd": row.get("goalDifference"),
                "pts": row.get("points"),
            })
        data_out[lg["id"]] = {"standings": standings}
        time.sleep(6)
    return leagues_out, data_out


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ca">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>⚽ Lligues Europees 2025/26</title>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⚽</text></svg>">
  <style>
    :root{
      --bg:#0d1117; --bg2:#161b22; --bg3:#1c2128; --border:#30363d;
      --text:#e6edf3; --muted:#8b949e;
      --cl:#1a6fc4; --el:#f97316; --conf:#a855f7; --rel:#ef4444;
      --green:#2ea043; --blue:#58a6ff; --gold:#ffd700;
    }
    *,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
    body{background:var(--bg);color:var(--text);
         font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;min-height:100vh}
    header{background:var(--bg2);border-bottom:1px solid var(--border);
           padding:12px 18px;display:flex;align-items:center;gap:8px;
           position:sticky;top:0;z-index:200}
    header h1{font-size:1.05rem;font-weight:700;color:var(--blue)}
    .meta{margin-left:auto;font-size:.72rem;color:var(--muted)}
    .tabs-wrap{background:var(--bg2);border-bottom:1px solid var(--border);
               overflow-x:auto;scrollbar-width:none;position:sticky;top:46px;z-index:150}
    .tabs-wrap::-webkit-scrollbar{display:none}
    .tabs{display:flex;padding:0 10px}
    .tab{display:flex;align-items:center;gap:7px;padding:9px 13px;background:none;
         border:none;color:var(--muted);font-size:.81rem;font-weight:500;cursor:pointer;
         border-bottom:2px solid transparent;white-space:nowrap;transition:color .2s,border-color .2s;
         font-family:inherit}
    .tab:hover{color:var(--text)}
    .tab.active{color:var(--text);border-bottom-color:var(--green)}
    .tab-sum{border-right:1px solid var(--border);padding-right:16px;margin-right:6px}
    .hero-flag{height:44px;width:auto;border-radius:4px;
               box-shadow:0 2px 8px rgba(0,0,0,.5);flex-shrink:0}
    .page{display:none;padding:16px;max-width:980px;margin:0 auto}
    .page.active{display:block}
    #pg-sum{max-width:none}
    .hero{display:flex;align-items:center;gap:14px;margin-bottom:16px}
    .hero h2{font-size:1.3rem;font-weight:700}
    .hero small{font-size:.79rem;color:var(--muted);display:block;margin-top:2px}
    .hero-badge{margin-left:auto;font-size:.72rem;font-weight:700;
                padding:6px 12px;border-radius:20px;background:#b8860b33;
                color:var(--gold);border:1px solid #b8860b66;letter-spacing:.5px;
                white-space:nowrap}
    .card{background:var(--bg3);border:1px solid var(--border);
          border-radius:10px;overflow:hidden;margin-bottom:14px}
    .card-title{padding:8px 13px;background:var(--bg2);border-bottom:1px solid var(--border);
                font-size:.69rem;font-weight:700;color:var(--muted);
                text-transform:uppercase;letter-spacing:1px}
    .champ-banner{padding:10px 13px;text-align:center;font-size:.85rem;color:var(--gold);
                  background:linear-gradient(90deg,#b8860b22,#ffd70022,#b8860b22);
                  border-bottom:1px solid #ffd70033;letter-spacing:.5px;font-weight:600}
    .legend{display:flex;flex-wrap:wrap;gap:10px;padding:7px 13px;
            border-bottom:1px solid var(--border)}
    .li{display:flex;align-items:center;gap:5px;font-size:.68rem;color:var(--muted)}
    .ld{width:8px;height:8px;border-radius:50%}
    .tbl{width:100%;border-collapse:collapse;font-size:.8rem}
    .tbl thead tr{background:rgba(255,255,255,.02)}
    .tbl th{padding:6px 7px;font-size:.65rem;font-weight:700;color:var(--muted);
            text-transform:uppercase;letter-spacing:.4px;text-align:center}
    .tbl th.L,.tbl td.L{text-align:left}
    .tbl td{padding:7px;text-align:center;border-bottom:1px solid rgba(255,255,255,.04)}
    .tbl tr:last-child td{border-bottom:none}
    .tbl tbody tr:hover td{background:rgba(255,255,255,.03)}
    .pc{display:flex;align-items:center;gap:3px;justify-content:center}
    .pb{width:3px;height:14px;border-radius:2px;flex-shrink:0}
    .pn{font-weight:700;font-size:.75rem;min-width:13px}
    .tc{display:flex;align-items:center;gap:6px}
    .tl{width:20px;height:20px;object-fit:contain;flex-shrink:0;border-radius:50%;
        background:#222;display:inline-flex;align-items:center;justify-content:center;
        font-size:11px;font-weight:700;color:#888}
    .tn{font-weight:500;white-space:nowrap}
    .pts{font-weight:700;color:var(--blue)}
    .gdp{color:#3fb950}.gdn{color:var(--rel)}
    .tbl tr.champ .tn{color:var(--gold)}
    .tbl tr.champ td.pts{color:var(--gold)}
    .trophy{margin-left:5px}
    .sum-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch}
    .sum-tbl{border-collapse:collapse;font-size:.79rem;width:100%}
    .sum-tbl thead tr{background:var(--bg2)}
    .sum-tbl th{padding:7px 5px;font-size:.65rem;font-weight:700;
                color:var(--muted);text-transform:uppercase;text-align:center;
                border-bottom:2px solid var(--border)}
    .sum-tbl th.lgh{background:var(--bg2);border-left:2px solid var(--border);
                    border-right:2px solid var(--border);font-size:.72rem;
                    color:var(--text);padding:7px 10px;white-space:nowrap;
                    cursor:pointer;transition:color .15s}
    .sum-tbl th.lgh:hover{color:var(--blue)}
    .sum-tbl th.lgh img{vertical-align:middle;margin-right:4px}
    .sum-tbl td{padding:4px 5px;text-align:center;
                border-bottom:1px solid rgba(255,255,255,.04)}
    .sum-tbl tr:last-child td{border-bottom:none}
    .sum-tbl tbody tr:hover td{background:rgba(255,255,255,.03)}
    .sum-tbl td.lgsep{border-left:2px solid var(--border)}
    .sum-tbl td.lgend{border-right:2px solid var(--border)}
    .s-pos{font-weight:700;font-size:.77rem;color:var(--muted);
           min-width:24px;background:rgba(255,255,255,.02)}
    .s-logo{width:26px;padding:3px 2px}
    .s-name{text-align:left!important;white-space:nowrap;font-weight:500;
            padding-left:2px;max-width:140px;overflow:hidden;text-overflow:ellipsis}
    .s-pts{font-weight:700;color:var(--blue);min-width:26px}
    .s-empty{color:var(--muted);font-size:.72rem}
    .s-bar{display:inline-block;width:3px;height:13px;border-radius:2px;
           vertical-align:middle;margin-right:3px}
    .s-tbl tr.s-champ-row .s-name,
    .s-tbl tr.s-champ-row .s-pts{color:var(--gold)}
    .empty{padding:18px;text-align:center;color:var(--muted);font-size:.79rem}
    @media(max-width:600px){.page{padding:8px}.tabs-wrap{top:44px}}
  </style>
</head>
<body>
<header>
  <span style="font-size:1.35rem">⚽</span>
  <h1>Lligues Europees 2025/26</h1>
  <span class="meta" id="metaDate"></span>
</header>
<div class="tabs-wrap"><div class="tabs" id="tabs"></div></div>
<div id="pages"></div>

<script>
const UPDATED_AT = __UPDATED_AT__;
const LEAGUES    = __LEAGUES__;
const DATA       = __DATA__;

const CDN = 'https://flagcdn.com';

document.getElementById('metaDate').textContent = 'Actualitzat: ' + UPDATED_AT;

function flagImg(cc, h){
  return `<img src="${CDN}/w40/${cc}.png" alt="${cc}" style="height:${h||14}px;width:auto;border-radius:2px;vertical-align:middle">`;
}
function logoImg(name, size, url){
  const initial = (name || '?').charAt(0).toUpperCase();
  if (url) return `<img src="${url}" alt="${name}" width="${size}" height="${size}" class="tl" loading="lazy" onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'tl',style:'width:${size}px;height:${size}px;font-size:${Math.round(size*0.55)}px',textContent:'${initial}'}))">`;
  return `<span class="tl" style="width:${size}px;height:${size}px;font-size:${Math.round(size*0.55)}px">${initial}</span>`;
}
function posBar(pos, total, lg){
  if (pos <= lg.cl) return 'var(--cl)';
  if (pos <= lg.cl + lg.el) return 'var(--el)';
  if (pos <= lg.cl + lg.el + lg.cf) return 'var(--conf)';
  if (total && pos > total - lg.rel) return 'var(--rel)';
  return 'transparent';
}
function isChampion(lg, name){
  return !!(lg.champion && lg.champion.name === name);
}
function fmt(v){
  return (v === null || v === undefined) ? '<span style="color:var(--muted)">—</span>' : v;
}
function fmtGD(gd){
  if (gd === null || gd === undefined) return '<span style="color:var(--muted)">—</span>';
  if (gd > 0) return `<span class="gdp">+${gd}</span>`;
  if (gd < 0) return `<span class="gdn">${gd}</span>`;
  return '0';
}

function renderStandings(rows, lg){
  if (!rows.length) return '<div class="empty">Sense dades de classificació</div>';
  const total = rows.length;
  const trs = rows.map(r => {
    const bar = posBar(r.pos, total, lg);
    const champ = isChampion(lg, r.name);
    const trophy = champ ? ' <span class="trophy">🏆</span>' : '';
    return `<tr class="${champ ? 'champ' : ''}">
      <td><div class="pc"><div class="pb" style="background:${bar}"></div><span class="pn">${r.pos}</span></div></td>
      <td class="L"><div class="tc">${logoImg(r.name, 20, r.logo)}<span class="tn">${r.name}${trophy}</span></div></td>
      <td>${fmt(r.gp)}</td><td>${fmt(r.w)}</td><td>${fmt(r.d)}</td><td>${fmt(r.l)}</td>
      <td>${fmt(r.gf)}</td><td>${fmt(r.ga)}</td><td>${fmtGD(r.gd)}</td>
      <td class="pts">${fmt(r.pts)}</td>
    </tr>`;
  }).join('');
  const legendItems = [];
  if (lg.cl)  legendItems.push(`<div class="li"><div class="ld" style="background:var(--cl)"></div>Champions League</div>`);
  if (lg.el)  legendItems.push(`<div class="li"><div class="ld" style="background:var(--el)"></div>Europa League</div>`);
  if (lg.cf)  legendItems.push(`<div class="li"><div class="ld" style="background:var(--conf)"></div>Conference</div>`);
  if (lg.rel) legendItems.push(`<div class="li"><div class="ld" style="background:var(--rel)"></div>Descens</div>`);
  return `<div class="legend">${legendItems.join('')}</div>
    <table class="tbl"><thead><tr>
      <th>#</th><th class="L">Club</th>
      <th>PJ</th><th>G</th><th>E</th><th>P</th>
      <th>GF</th><th>GC</th><th>DG</th><th>Pts</th>
    </tr></thead><tbody>${trs}</tbody></table>`;
}

function goToLeague(i){
  document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  const btn = document.querySelector(`.tab[data-i="${i}"]`);
  if (btn) { btn.classList.add('active'); btn.scrollIntoView({inline:'nearest', block:'nearest'}); }
  const pg = document.getElementById(`pg${i}`);
  if (pg) pg.classList.add('active');
  window.scrollTo(0, 0);
}

function renderSummary(){
  const MAX = 20;
  let hdr = `<th class="s-pos">#</th>`;
  LEAGUES.forEach((lg, i) => {
    hdr += `<th colspan="3" class="lgh" onclick="goToLeague(${i})">${flagImg(lg.cc, 13)} ${lg.name}</th>`;
  });
  let body = '';
  for (let i = 1; i <= MAX; i++) {
    let row = `<tr>`;
    row += `<td class="s-pos">${i}</td>`;
    LEAGUES.forEach((lg, li) => {
      const rows = DATA[lg.id]?.standings || [];
      const team = rows.find(t => t.pos === i);
      const isLast = li === LEAGUES.length - 1;
      if (team) {
        const bar = posBar(i, rows.length, lg);
        const champ = isChampion(lg, team.name);
        const champCls = champ ? ' s-champ' : '';
        const trophy = champ ? ' 🏆' : '';
        row += `<td class="s-logo lgsep">${logoImg(team.name, 18, team.logo)}</td>
                <td class="s-name${champCls}"><span class="s-bar" style="background:${bar}"></span>${team.name}${trophy}</td>
                <td class="s-pts${isLast?' lgend':''}${champCls}">${team.pts ?? '–'}</td>`;
      } else {
        row += `<td class="s-logo lgsep s-empty">–</td>
                <td class="s-name s-empty">–</td>
                <td class="s-pts${isLast?' lgend':''} s-empty">–</td>`;
      }
    });
    row += '</tr>';
    body += row;
  }
  return `<div class="sum-wrap"><table class="sum-tbl s-tbl">
    <thead><tr>${hdr}</tr></thead>
    <tbody>${body}</tbody>
  </table></div>`;
}

function build(){
  const tabsEl  = document.getElementById('tabs');
  const pagesEl = document.getElementById('pages');

  const sumBtn = document.createElement('button');
  sumBtn.className = 'tab tab-sum active';
  sumBtn.innerHTML = `${flagImg('eu', 14)} Resum`;
  sumBtn.dataset.i = 'sum';
  tabsEl.appendChild(sumBtn);

  const sumPg = document.createElement('div');
  sumPg.className = 'page active';
  sumPg.id = 'pg-sum';
  sumPg.innerHTML = `
    <div class="hero">
      <img src="${CDN}/w80/eu.png" alt="EU" class="hero-flag">
      <div><h2>Resum Europeu</h2><small>Les 7 primeres divisions · 2025/26</small></div>
    </div>
    <div class="card">
      <div class="card-title">📊 Classificació per posició</div>
      ${renderSummary()}
    </div>`;
  pagesEl.appendChild(sumPg);

  LEAGUES.forEach((lg, i) => {
    const btn = document.createElement('button');
    btn.className = 'tab';
    btn.innerHTML = `${flagImg(lg.cc, 14)} ${lg.name}`;
    btn.dataset.i = i;
    tabsEl.appendChild(btn);

    const d  = DATA[lg.id] || {};
    const pg = document.createElement('div');
    pg.className = 'page';
    pg.id = `pg${i}`;
    const champBadge  = lg.champion ? `<div class="hero-badge">✓ CAMPIÓ</div>` : '';
    const champBanner = lg.champion
      ? `<div class="champ-banner">🏆 ${lg.champion.name} — Campió${lg.champion.date ? ' el ' + lg.champion.date : ''}</div>`
      : '';
    pg.innerHTML = `
      <div class="hero">
        <img src="${CDN}/w80/${lg.cc}.png" alt="${lg.country}" class="hero-flag">
        <div><h2>${lg.name}</h2><small>${lg.country} · 2025/26</small></div>
        ${champBadge}
      </div>
      <div class="card">
        <div class="card-title">📊 Classificació</div>
        ${champBanner}
        ${renderStandings(d.standings || [], lg)}
      </div>`;
    pagesEl.appendChild(pg);
  });

  tabsEl.addEventListener('click', e => {
    const btn = e.target.closest('.tab');
    if (!btn) return;
    const id = btn.dataset.i;
    tabsEl.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(id === 'sum' ? 'pg-sum' : `pg${id}`).classList.add('active');
    window.scrollTo(0, 0);
  });
}

build();
</script>
</body>
</html>
"""


def main():
    if not API_KEY:
        print("⚠️  Cal definir FOOTBALL_API_KEY.")
        print("   Obté una clau gratuïta a https://www.football-data.org/client/register")
        return

    print(f"Actualitzant lligues — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    leagues, data = build_data()
    updated_at = datetime.now().strftime("%d/%m/%Y %H:%M")

    html = (HTML_TEMPLATE
            .replace("__UPDATED_AT__", json.dumps(updated_at, ensure_ascii=False))
            .replace("__LEAGUES__", json.dumps(leagues, ensure_ascii=False))
            .replace("__DATA__", json.dumps(data, ensure_ascii=False)))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ Fitxer generat: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
