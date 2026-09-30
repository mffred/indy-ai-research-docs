"""Builds the static site from _src into the site root. Run: python3 _src/build.py"""
import pathlib, markdown, re, html, urllib.parse, json, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "_src"
UPDATED = "September 28, 2026"
SITE = "https://airesearch.myfriendfred.org"
ISSUES = "https://github.com/mffred/indy-ai-research-docs/issues/new"

FONTS = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Young+Serif&family=Bitter:ital,wght@0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap">'

def head(title, desc):
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta name="robots" content="index, follow">
{FONTS}
<link rel="stylesheet" href="/assets/site.css">
'''

def bar(current):
    links = [("/", "All docs", "home"), ("/budget", "City budget", "budget"), ("/flock", "Flock timeline", "flock"), ("/flock-cancellations", "How cities dropped Flock", "cancel"), ("/council-votes", "Council votes", "votes")]
    cur = ' aria-current="page"'
    nav = "".join(f'<a href="{h}"{cur if k == current else ""}>{t}</a>' for h, t, k in links)
    return f'<header class="site-bar"><a class="brand" href="/">Indy AI Research Docs</a><nav aria-label="Site">{nav}</nav></header>'

def theme(page, container, title):
    """Load the Pinstripe theme last, and turn the page's main container into a titled window."""
    page = page.replace("</head>", '<link rel="stylesheet" href="/assets/pinstripe.css">\n<script src="/assets/corrections.js" defer></script>\n</head>', 1)
    return page.replace(container, f'{container} data-ps-title="{html.escape(title)}"', 1)

def correction_url(path):
    """GitHub issue form (.github/ISSUE_TEMPLATE/correction.yml) with the page pre-filled."""
    return ISSUES + "?" + urllib.parse.urlencode({"template": "correction.yml", "page": SITE + path})

def notice(path):
    # Document pages get a correction flag on every section (assets/corrections.js); the home page, an index, links the form directly.
    if path == "/":
        fix = f'Found an error? <a href="{html.escape(correction_url(path))}" target="_blank" rel="noopener">Send a correction</a> with a link to your source.'
    else:
        fix = "Found an error? Use the flag next to any section to send a correction with a link to your source."
    return f'''<aside class="ai-notice" role="note"><span class="tag">AI draft</span><div><b>Preliminary research, generated with AI.</b> This page was drafted with an AI assistant (Claude) from public records and news reports. It may contain mistakes or miss context. Check the linked sources before you rely on, share or cite anything. {fix} Last updated {UPDATED}.</div></aside>'''

FOOT = f'''<footer class="site-foot">Indy AI Research Docs is a work in progress. Figures come from the linked public documents; summaries and analysis were generated with AI and spot-checked, not independently verified. Nothing here is legal or financial advice. Last updated {UPDATED}.</footer>'''

# ---------- Flock page ----------
md = (SRC / "flock.md").read_text()
body = markdown.markdown(md, extensions=["tables", "fenced_code"])
body = re.sub(r"<table>", '<div class="tbl-wrap"><table>', body)
body = re.sub(r"</table>", "</table></div>", body)
body = re.sub(r'<a href="(https?://[^"]+)"', r'<a href="\1" target="_blank" rel="noopener"', body)
flock_css = '''<style>
.doc{max-width:980px;margin:0 auto;padding-top:28px}
.doc h1{font-size:clamp(32px,5.5vw,46px);line-height:1.05;margin-bottom:14px}
.doc h2{font-size:27px;margin:40px 0 10px}
.doc h3{font-size:19px;margin:26px 0 8px}
.doc p,.doc li{max-width:72ch}
.doc ul,.doc ol{padding-left:22px}
.tbl-wrap{overflow-x:auto;background:var(--surface);border:1px solid var(--line);border-radius:8px;margin:12px 0}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{text-align:left;vertical-align:top;padding:9px 12px;border-bottom:1px solid var(--grid)}
thead th{font-size:12.5px;color:var(--ink-2);font-weight:600;border-bottom:1px solid var(--axis)}
tbody tr:last-child td{border-bottom:0}
td:first-child{white-space:nowrap;font-variant-numeric:tabular-nums;font-weight:600}
pre{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:14px 16px;overflow-x:auto;font-size:13px;line-height:1.5;white-space:pre-wrap}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.copy{font:inherit;font-size:13px;margin:-4px 0 8px;padding:5px 12px;border-radius:6px;border:1px solid var(--line);background:var(--surface);color:var(--ink);cursor:pointer}
</style>'''
copy_js = '''<script>
document.querySelectorAll('.doc pre').forEach(function(pre){
  var b=document.createElement('button');b.type='button';b.className='copy';b.textContent='Copy this request';
  b.onclick=function(){var t=pre.innerText;var done=function(){b.textContent='Copied';setTimeout(function(){b.textContent='Copy this request'},1500)};
    if(navigator.clipboard){navigator.clipboard.writeText(t).then(done,function(){})}};
  pre.parentNode.insertBefore(b,pre);
});
</script>'''
flock = (head("Indianapolis Flock and License Plate Reader Timeline", "Dated record of IMPD's license plate reader contracts from 2021 to 2026, with sources, open questions and template public records requests.")
         + flock_css + "</head>\n<body>\n" + bar("flock") + notice("/flock") + '<main class="doc">' + body + "</main>" + FOOT + copy_js + "\n</body>\n</html>\n")
(ROOT / "flock" / "index.html").write_text(theme(flock, '<main class="doc"', "Flock Timeline"))

# ---------- Budget page ----------
b = (SRC / "budget.html").read_text()
title_m = re.search(r"<title>.*?</title>", b)
b = b.replace(title_m.group(0), "")
b = re.sub(r'<link rel="preconnect"[^>]*>\s*<link rel="stylesheet" href="https://fonts.googleapis.com[^>]*>', "", b, count=1)
b = b.replace("padding-inline:16px;padding-block:28px 56px", "padding-inline:16px;padding-block:0 56px")
b = b.replace('<div class="wrap">', bar("budget") + notice("/budget") + '<div class="wrap" style="padding-top:28px">', 1)
b = re.sub(r"(<script>)", FOOT + r"\n\1", b, count=1)
budget = (head("Indianapolis Budget Explorer", "Nine years of Indianapolis and Marion County spending and a clickable breakdown of all 35 departments in the 2027 proposed budget.")
          + b.split("<style>", 1)[0] + "<style>" + b.split("<style>", 1)[1].split("</style>", 1)[0] + "</style>\n</head>\n<body>\n"
          + b.split("</style>", 1)[1] + "\n</body>\n</html>\n")
(ROOT / "budget" / "index.html").write_text(theme(budget, '<div class="wrap"', "City Budget"))

# ---------- Flock cancellations page ----------
# Self-contained page with its own styles, script and footer. Served as-is apart from the
# shared site bar and notice, which replaces the page's own AI warning so it doesn't show two.
c = (SRC / "flock-cancellations.html").read_text()
c = c.replace("<style>", FONTS + '\n<link rel="stylesheet" href="/assets/site.css">\n<style>', 1)
c = c.replace("padding-block:28px 64px", "padding-block:0 64px", 1)
# Match the page's 1040px column.
c = c.replace("</style>\n</head>", '.site-bar{max-width:1040px}\n.ai-notice{max-width:1040px}\n</style>\n</head>', 1)
c = re.sub(r'\s*<div class="ai-warn" role="note">.*?</div>', "", c, count=1)
c = c.replace('<div class="wrap">', bar("cancel") + notice("/flock-cancellations") + '\n<div class="wrap" style="padding-top:28px">', 1)
(ROOT / "flock-cancellations").mkdir(exist_ok=True)
(ROOT / "flock-cancellations" / "index.html").write_text(theme(c, '<div class="wrap"', "How Cities Dropped Flock"))

# ---------- Council votes page ----------
# Data: _src/council-data/votes.json (from tools/parse_votes.py), compacted into council-votes/data.json,
# which the page's script loads. One string per vote holds every member's vote (Y/N/A/V/S, "." = not
# serving), in members.json order.
CD = SRC / "council-data"
sys.path.insert(0, str(CD))
from topics import topics_for, NAMES as TOPIC_NAMES
cv = json.loads((CD / "votes.json").read_text())
members = json.loads((CD / "members.json").read_text())["members"]
key_idx = {k: i for i, m in enumerate(members) for k in m["keys"]}
CODE = {"Yes": "Y", "No": "N", "Absent": "A", "Not voting": "V", "Abstain": "S"}
ACTIONS = ["Final passage", "Amendment", "Procedural motion", "Postpone or table", "Return to committee", "Withdraw", "Election", "Strike"]
SRC_IDX = {"minutes": 0, "roll-call sheet (OCR)": 1, "minutes (sheet unreadable)": 2}
rows, used = [], set()
for v in cv["votes"]:
    if not v["proposals"]: continue  # e.g. electing a Council president: no proposal to file it under
    codes = ["."] * len(members)
    for k, how in v["votes"].items():
        if k in key_idx: codes[key_idx[k]] = CODE[how]
    flags = (1 if v.get("consent") else 0) | (2 if v.get("group") else 0) | (4 if v["status"] == "needs review" else 0) | (8 if v["status"] == "sources differ" else 0)
    if v.get("cityTally"):  # the record's names contradict the city's official count: don't show them as fact
        codes = ["?" if c != "." else "." for c in codes]
    rows.append([v["date"], v["proposals"][0], ACTIONS.index(v["action"]), {"Passed": "P", "Failed": "F"}.get(v["outcome"], "U"),
                 "".join(codes), flags, SRC_IDX[v["source"]], v["page"], v.get("note"), v.get("cityTally")])
    used.add(v["proposals"][0])
props = {}
for k in used:
    pr = cv["proposals"][k]
    title = re.sub(r"\s+", " ", pr["title"] or "")[:420]
    if title.count('"') % 2: title += '"'  # a description cut at 'Day."' loses its closing quote
    props[k] = [title, pr["type"], [TOPIC_NAMES.index(t) for t in topics_for(k, pr["title"], pr["type"])], pr["sponsors"],
                pr.get("committee"), pr.get("initiator"), pr.get("documentUrl"), 1 if pr.get("titleSource") else 0,
                1 if (CD / "proposals" / f"{k}.txt").exists() else 0]
meetings = {m["date"]: {"m": (m["minutes"] or {}).get("url"), "r": (m["rollCall"] or {}).get("url")}
            for m in json.loads((CD / "sources.json").read_text())["meetings"]}
(ROOT / "council-votes").mkdir(exist_ok=True)
# Each proposal's full text (_src/council-data/proposals/, from tools/fetch_proposal_texts.py) is published as
# its own file so the page loads it only when someone opens it.
TEXT_DIR = ROOT / "council-votes" / "text"
TEXT_DIR.mkdir(exist_ok=True)
for k in used:
    f = CD / "proposals" / f"{k}.txt"
    if f.exists():
        t = re.sub(r"^=== \S+ proposal document, page (\d+) of (\d+)( \([^)]*\))? ===$", r"[Page \1 of \2]", f.read_text(), flags=re.M)
        # rejoin lines the scan wrapped mid-sentence; short lines (headings, table rows) stay as they are
        t = re.sub(r"(?m)^(.{55,}[^.:;\n])\n(?=[a-z(\"“$\d])", r"\1 ", t)
        (TEXT_DIR / f"{k}.txt").write_text(re.sub(r"\n{3,}", "\n\n", t).strip() + "\n")
(ROOT / "council-votes" / "data.json").write_text(json.dumps(
    {"members": [{k: m[k] for k in ("name", "district", "former", "note") if k in m} for m in members],
     "topics": TOPIC_NAMES, "props": props, "meetings": meetings, "votes": rows}, separators=(",", ":")))
# Full-text search index: word -> proposals whose full text contains it. Common words and bare numbers are
# left out and a plural "s" is dropped (the page's script normalizes search words the same way). Postings are
# delta-encoded in base 36 to keep the file small; the page loads it only when someone searches.
STOP = set("the and for that with this from which such shall have been are was were will its their his her they them than then there these those upon into any all not but may other each said per also under same hereby being".split())
def norm_word(w):
    w = w.strip("'-")
    return w[:-1] if len(w) > 4 and w.endswith("s") and not w.endswith("ss") else w
def b36(n):
    d = "0123456789abcdefghijklmnopqrstuvwxyz"; out = ""
    while True:
        n, r = divmod(n, 36); out = d[r] + out
        if not n: return out
keys = sorted(k for k in used if (CD / "proposals" / f"{k}.txt").exists())
index = {}
for i, k in enumerate(keys):
    words = {norm_word(w) for w in re.findall(r"[a-z][a-z'-]{2,}", (CD / "proposals" / f"{k}.txt").read_text().lower())}
    for w in words:
        if len(w) >= 3 and w not in STOP: index.setdefault(w, []).append(i)
enc = {w: ",".join(b36(x - (ids[j - 1] if j else 0)) for j, x in enumerate(ids)) for w, ids in index.items()}
(ROOT / "council-votes" / "search-index.json").write_text(json.dumps({"keys": keys, "w": enc}, separators=(",", ":")))

cc, tc = cv["crossCheck"], cv["tallyCheck"]
vp = (SRC / "council-votes.html").read_text()
vp = vp.replace("{{CROSSCHECK}}", f"where both the minutes and a readable roll-call sheet cover the same vote, they list every councilor's vote identically {cc['agree']:,} times out of {cc['compared']:,} ({round(100 * cc['agree'] / cc['compared'])}%). Most differences are the minutes still listing a councilor who had left, or naming someone \"not voting\" whom the sheet shows abstaining. Where they differ, this page follows the sheet, which the voting system prints.")
vp = vp.replace("{{TALLYCHECK}}", f"the city's own proposal database records the final yes-no count for most proposals. It matches the count on this page for {tc['agree']:,} of {tc['compared']:,} final votes ({round(100 * tc['agree'] / tc['compared'])}%). The {tc['compared'] - tc['agree']} that don't match are marked \"Needs review\", with the city's figure shown.")
vp = vp.replace("{{STATS}}", f"In all: {len(rows):,} recorded votes on {len(props):,} proposals across {len({r[0] for r in rows})} meetings, {sum(1 for r in rows if r[5] & 3):,} of them routine group votes. {sum(1 for r in rows if r[5] & 4)} are marked as needing review.")
votes_page = (head("How Your Councilor Voted", "Search every recorded Indianapolis City-County Council roll-call vote since 2021 by councilor, topic and year, with a link to the official record for each vote.")
              + "</head>\n<body>\n" + bar("votes") + notice("/council-votes") + vp + FOOT + "\n</body>\n</html>\n")
(ROOT / "council-votes" / "index.html").write_text(theme(votes_page, '<main class="cv"', "Council Votes"))

# ---------- Home ----------
home_css = '''<style>
.home{max-width:980px;margin:0 auto;padding-top:36px;display:flex;flex-direction:column;gap:36px}
.home h1{font-size:clamp(38px,7vw,60px);line-height:1}
.lede{font-size:17px;color:var(--ink-2);max-width:64ch;margin:14px 0 0}
.docs{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}
.card{display:flex;flex-direction:column;gap:10px;background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:20px;text-decoration:none;color:var(--ink)}
.card:hover{border-color:var(--accent)}
.card h2{font-size:24px;line-height:1.15}
.card p{margin:0;color:var(--ink-2);font-size:14.5px}
.meta{display:flex;flex-wrap:wrap;gap:8px;font-size:12px}
.pill{border:1px solid var(--warn-line);color:var(--warn-ink);background:var(--warn-bg);border-radius:999px;padding:2px 9px;font-weight:600}
.pill.q{border-color:var(--line);color:var(--ink-2);background:transparent;font-weight:500}
.card .go{margin-top:auto;color:var(--accent);font-weight:600;font-size:14px}
.how{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:20px}
.how h3{font-size:18px;margin-bottom:4px}
.how p{margin:0;font-size:14px;color:var(--ink-2)}
.eyebrow{font-size:12px;font-weight:600;letter-spacing:.09em;text-transform:uppercase;color:var(--muted)}
</style>'''
home_body = f'''<main class="home">
  <section>
    <div class="eyebrow">Indianapolis and Marion County · Work in progress</div>
    <h1>Indy AI Research Docs</h1>
    <p class="lede">Preliminary research on how local government spends money and makes decisions, pulled from the city's own budget books, board packets and news coverage. Built with AI to get public information into a form people can actually read. Treat everything here as a first draft.</p>
  </section>
  <section class="docs" aria-label="Documents">
    <a class="card" href="/budget">
      <div class="meta"><span class="pill">AI draft</span><span class="pill q">Updated {UPDATED}</span></div>
      <h2>Indianapolis Budget Explorer</h2>
      <p>Nine years of city-county spending, revenue by source, and a clickable breakdown of all 35 departments in the $1.898B 2027 proposed budget: where each one's money comes from and what it pays for.</p>
      <span class="go">Open the explorer →</span>
    </a>
    <a class="card" href="/flock">
      <div class="meta"><span class="pill">AI draft</span><span class="pill q">Updated {UPDATED}</span></div>
      <h2>Flock and License Plate Reader Timeline</h2>
      <p>Every IMPD license plate reader approval in the public record since 2021, the money involved, the open questions, and template public records requests anyone can send.</p>
      <span class="go">Read the timeline →</span>
    </a>
    <a class="card" href="/flock-cancellations">
      <div class="meta"><span class="pill">AI draft</span><span class="pill q">Updated {UPDATED}</span></div>
      <h2>How Cities Dropped Flock</h2>
      <p>Campaigns that ended Flock contracts, how they won, and what they didn't win.</p>
      <span class="go">See the campaigns →</span>
    </a>
    <a class="card" href="/council-votes">
      <div class="meta"><span class="pill">AI draft</span><span class="pill q">Updated {UPDATED}</span></div>
      <h2>How Your Councilor Voted</h2>
      <p>Every recorded City-County Council roll-call vote since 2021, searchable by councilor, topic and year, from infrastructure funding to TIFs and rezoning, each linked to the official record.</p>
      <span class="go">Look up a councilor →</span>
    </a>
  </section>
  <section>
    <h2 style="font-size:26px;margin-bottom:14px">How these are made</h2>
    <div class="how">
      <div><h3>Public sources only</h3><p>Budget books, board meeting packets, city web pages and published news. Every page links to what it used.</p></div>
      <div><h3>Drafted with AI</h3><p>An AI assistant (Claude) pulled the numbers from source PDFs, wrote the summaries and built the pages. Totals were cross-checked against the documents' own summary tables.</p></div>
      <div><h3>Not verified line by line</h3><p>Descriptions and interpretations can be wrong. Where something is uncertain, the page says so. Check the source before citing anything.</p></div>
    </div>
  </section>
</main>'''
home = (head("Indy AI Research Docs", "Preliminary, AI-assisted research on Indianapolis and Marion County government: budget breakdowns, surveillance contracts and public records.")
        + home_css + "</head>\n<body>\n" + bar("home") + notice("/") + home_body + FOOT + "\n</body>\n</html>\n")
(ROOT / "index.html").write_text(theme(home, '<main class="home"', "Indy AI Research Docs"))
print("built", [p.relative_to(ROOT).as_posix() for p in ROOT.rglob("index.html")])
