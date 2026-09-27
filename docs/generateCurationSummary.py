#!/usr/bin/env python3
"""Generate docs/Curation_Summary.html from the bba-curated/ Layer B verdicts.

Reads every bba-curated/<scenario>-graded.json plus theme-index.json, embeds
the data inline (file:// + GitHub Pages compatible), and renders a page in the
site's existing style (matches index.html / Scenario_Summary.html). Re-run
after re-curating to refresh:  python3 docs/generateCurationSummary.py
"""
import json, os, glob, collections, sys
from datetime import datetime, timezone

DOCS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DOCS)
sys.path.append(os.path.join(ROOT, "py"))
from curate import scenario_config  # noqa: E402

def collect():
    rows = []
    for f in sorted(glob.glob(os.path.join(ROOT, "bba-curated", "*-graded.json"))):
        scn = os.path.basename(f).replace("-graded.json", "")
        V = json.load(open(f))["verdicts"]
        kind, _, _ = scenario_config(scn)
        def tc(disc):
            c = collections.Counter(v[disc]["tier"] for v in V)
            return {t: c.get(t, 0) for t in ("textbook", "standard", "judgment", "reject")}
        rows.append({"scenario": scn, "kind": kind, "boards": len(V),
                     "bidding": tc("bidding"), "declarer": tc("declarer"), "defense": tc("defense")})
    themes = json.load(open(os.path.join(ROOT, "bba-curated", "theme-index.json")))
    theme_rows = [{"theme": th, "total": len(lst),
                   "textbook": sum(1 for x in lst if x["tier"] == "textbook")}
                  for th, lst in themes.items()]
    theme_rows.sort(key=lambda r: -r["total"])
    return {"scenarios": rows, "themes": theme_rows,
            "totals": {"scenarios": len(rows), "boards": sum(r["boards"] for r in rows),
                       "themes": len(theme_rows)}}

NAV = ('<p style="text-align:center;color:#666;margin-bottom:24px">Generated <span id="gen-time" data-utc="__GENERATED__"></span> &mdash; '
       '<a class="nav-btn" href="./">Dashboard</a> '
       '<a class="nav-btn" href="Scenario_Summary.html">Scenario Summary</a> '
       '<a class="nav-btn" href="Convention_Card_Summary.html">Convention Cards</a> '
       '<a class="nav-btn nav-btn-active" href="Curation_Summary.html">Curation</a></p>')

HTML = r'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PBS Curation Summary</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:13px;max-width:1100px;margin:40px auto;padding:20px;background:#f5f5f5;color:#333}
h1{color:#222;text-align:center;margin-bottom:6px;font-size:22px}
.subtitle{text-align:center;color:#666;margin-bottom:18px}
.nav-btn{display:inline-block;padding:6px 14px;background:#0077b6;color:#fff;border-radius:4px;text-decoration:none;font-size:12px;margin:0 4px}
.nav-btn:hover{background:#005f8a}
.nav-btn-active{background:#333;pointer-events:none}
.stats{display:grid;grid-template-columns:repeat(5,1fr);gap:15px;margin-bottom:26px}
.stat-box{background:#fff;border-radius:8px;padding:18px;text-align:center;box-shadow:0 2px 4px rgba(0,0,0,.08)}
.stat-value{font-size:24px;font-weight:bold;color:#0077b6}
.stat-label{color:#666;margin-top:5px;font-size:12px}
h3{color:#333;font-size:14px;margin:26px 0 10px}
.hint{font-weight:normal;color:#999;font-size:12px}
.legend{font-size:12px;color:#555;margin-bottom:10px}
.swatch{display:inline-block;width:11px;height:11px;border-radius:2px;margin:0 5px 0 14px;vertical-align:-1px}
.card{background:#fff;border-radius:8px;padding:18px;box-shadow:0 2px 4px rgba(0,0,0,.08)}
table{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;font-size:12.5px;box-shadow:0 2px 4px rgba(0,0,0,.08)}
th,td{padding:8px 10px;text-align:left;border-bottom:1px solid #eee}
th{background:#eef3f6;font-weight:600;cursor:pointer;user-select:none;white-space:nowrap}
th:hover{background:#e4ecf1}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.scn{font-weight:600}
.kind{display:inline-block;font-size:11px;padding:1px 7px;border-radius:10px;background:#eef2f7;color:#4a6275}
.kind.bidding{background:#eaf2ff;color:#2b5fa8}.kind.byforce{background:#eafaf0;color:#1f7a44}
.kind.soundness{background:#fff4e6;color:#9a6212}.kind.avoidance{background:#f5ecff;color:#6b3fa0}
.bar{display:flex;height:15px;border-radius:3px;overflow:hidden;min-width:120px;border:1px solid #00000010}
.tb{background:#2e7d4f}.st{background:#7cc59a}.ju{background:#f0c040}.rj{background:#e6e3dd}
.note{background:#fff;border-left:3px solid #f0c040;border-radius:6px;padding:12px 16px;margin-top:14px;font-size:12.5px;color:#54514b;box-shadow:0 2px 4px rgba(0,0,0,.08)}
</style></head><body>
<h1>PBS Curation Summary</h1>
<p class="subtitle">Teaching-value grades for every curated scenario &mdash; bidding, declarer, and defense</p>
__NAV__
<p style="text-align:center;color:#888;font-size:12px;margin:-8px 0 22px">Scope: the __SCOPE__ coaching scenarios curated for teaching (a subset of the full scenario library on the Scenario Summary page). Each board's full pool is graded; one row per scenario below.</p>
<div class="stats" id="stats"></div>
<h3>Bidding tiers by scenario <span class="hint">&mdash; click a header to sort</span></h3>
<div class="legend"><span class="swatch tb"></span>textbook<span class="swatch st"></span>standard<span class="swatch ju"></span>judgment<span class="swatch rj"></span>reject</div>
<table id="scnTable"><thead><tr>
<th data-k="scenario">Scenario</th><th data-k="kind">Kind</th><th class="num" data-k="boards">Boards</th>
<th>Bidding mix</th><th class="num" data-k="btb">Bid&nbsp;TB</th><th class="num" data-k="dtb">Decl&nbsp;TB</th><th class="num" data-k="ftb">Def&nbsp;TB</th>
</tr></thead><tbody></tbody></table>
<h3>Theme index <span class="hint">&mdash; cross-scenario play-lesson pools (textbook boards in dark green)</span></h3>
<div class="card"><canvas id="themeChart" height="190"></canvas></div>
<div class="note" id="note"></div>
<script>
const D=__DATA__;
const sum=o=>o.textbook+o.standard+o.judgment+o.reject;
const stats=[["Scenarios",D.totals.scenarios],["Boards graded",D.totals.boards.toLocaleString()],
["Play themes",D.totals.themes],["Textbook bids",D.scenarios.reduce((a,r)=>a+r.bidding.textbook,0)],
["Judgment bids",D.scenarios.reduce((a,r)=>a+r.bidding.judgment,0)]];
document.getElementById('stats').innerHTML=stats.map(s=>`<div class="stat-box"><div class="stat-value">${s[1]}</div><div class="stat-label">${s[0]}</div></div>`).join('');
let rows=D.scenarios.map(r=>({...r,btb:r.bidding.textbook,dtb:r.declarer.textbook,ftb:r.defense.textbook}));
let sk='btb',sd=-1;
const bar=o=>{const t=sum(o)||1,s=(c,n)=>n?`<span class="${c}" style="width:${100*n/t}%"></span>`:'';
return `<div class="bar" title="tb ${o.textbook} / st ${o.standard} / ju ${o.judgment} / rj ${o.reject}">${s('tb',o.textbook)}${s('st',o.standard)}${s('ju',o.judgment)}${s('rj',o.reject)}</div>`;};
function render(){rows.sort((a,b)=>{let x=a[sk],y=b[sk];return typeof x==='string'?sd*x.localeCompare(y):sd*(x-y);});
document.querySelector('#scnTable tbody').innerHTML=rows.map(r=>`<tr><td class="scn">${r.scenario}</td>
<td><span class="kind ${r.kind}">${r.kind}</span></td><td class="num">${r.boards}</td><td>${bar(r.bidding)}</td>
<td class="num">${r.btb}</td><td class="num">${r.dtb}</td><td class="num">${r.ftb}</td></tr>`).join('');}
document.querySelectorAll('#scnTable th[data-k]').forEach(th=>th.onclick=()=>{const k=th.dataset.k;
if(sk===k)sd*=-1;else{sk=k;sd=(k==='scenario'||k==='kind')?1:-1;}render();});
render();
const T=D.themes.filter(t=>t.total>=5);
new Chart(document.getElementById('themeChart'),{type:'bar',
data:{labels:T.map(t=>t.theme),datasets:[
{label:'textbook',data:T.map(t=>t.textbook),backgroundColor:'#2e7d4f',stack:'s'},
{label:'standard+',data:T.map(t=>t.total-t.textbook),backgroundColor:'#cfe8d8',stack:'s'}]},
options:{indexAxis:'y',plugins:{legend:{labels:{boxWidth:12}}},
scales:{x:{beginAtZero:true,ticks:{precision:0}},y:{ticks:{font:{size:11}}}},
responsive:true,maintainAspectRatio:false}});
const hu=(D.themes.find(t=>t.theme==='hold-up')||{}).textbook,cw=(D.themes.find(t=>t.theme==='count-winners')||{}).textbook;
const gt=document.getElementById('gen-time'),gd=new Date(gt.dataset.utc);
gt.textContent=gd.toLocaleDateString()+' '+gd.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',timeZoneName:'short'});
document.getElementById('note').innerHTML='<b>Reading the themes:</b> a play lesson pulls from any pool here regardless of which scenario generated the board &mdash; e.g. a hold-up lesson draws the <b>'+hu+'</b> textbook hold-up boards, a counting lesson the <b>'+cw+'</b> textbook count-winners boards. Defensive themes skew low on textbook because the current library is bidding- and declarer-heavy.';
</script></body></html>'''

if __name__ == "__main__":
    data = collect()
    # The dashboard job sets PBS_GENERATED_AT so every page it writes shows one time.
    generated = (os.environ.get("PBS_GENERATED_AT")
                 or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    out = (HTML.replace("__NAV__", NAV.replace("__GENERATED__", generated))
               .replace("__SCOPE__", str(data["totals"]["scenarios"]))
               .replace("__DATA__", json.dumps(data)))
    path = os.path.join(DOCS, "Curation_Summary.html")
    open(path, "w").write(out)
    print(f"wrote {path}  ({data['totals']['scenarios']} scenarios, "
          f"{data['totals']['boards']} boards, {data['totals']['themes']} themes)")
