"""Builds the static site from _src into the site root. Run: python3 _src/build.py"""
import pathlib, markdown, re, html, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "_src"
UPDATED = "September 28, 2026"
SITE = "https://indy-ai-research-docs.vercel.app"
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
    links = [("/", "All docs", "home"), ("/budget", "City budget", "budget"), ("/flock", "Flock timeline", "flock"), ("/flock-cancellations", "How cities dropped Flock", "cancel")]
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
