"""Download each proposal's document from the city's proposal database and save its plain text to
_src/council-data/proposals/<no>-<year>.txt. Most are scans, so pages without a text layer are OCR'd
(tesseract). Resumable: proposals that already have a text file are skipped.

Run: python3 _src/council-data/tools/fetch_proposal_texts.py   (after parse_votes.py, which lists the documents)
"""
import json, os, re, subprocess, sys, tempfile, time
from multiprocessing import Pool
import pypdf

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR, TXT_DIR = os.path.join(HERE, "pdf", "proposals"), os.path.join(HERE, "proposals")


def ocr(data, ext):
    with tempfile.TemporaryDirectory() as t:
        src = os.path.join(t, "p." + ext); open(src, "wb").write(data)
        png = os.path.join(t, "p.png")
        subprocess.run(["sips", "-s", "format", "png", src, "--out", png], capture_output=True)
        best = ""
        for rot in (0, 90, 270, 180):  # proposals are normally upright
            img = png
            if rot:
                img = os.path.join(t, f"r{rot}.png")
                subprocess.run(["sips", "-r", str(rot), png, "--out", img], capture_output=True)
            out = subprocess.run(["tesseract", img, "stdout"], capture_output=True, text=True).stdout
            words = sum(1 for w in out.split() if w.isalpha() and len(w) > 3)
            if words > 25: return out
            if len(out) > len(best): best = out
        return best


def page_text(page):
    t = page.extract_text() or ""
    if len(t.strip()) > 80: return t, False
    imgs = page.images
    if not imgs: return t, False
    img = max(imgs, key=lambda i: len(i.data))
    return ocr(img.data, img.name.rsplit(".", 1)[-1].lower()), True


def do(item):
    key, url = item
    out = os.path.join(TXT_DIR, f"{key}.txt")
    if os.path.exists(out): return key, "skip"
    pdf = os.path.join(PDF_DIR, f"{key}.pdf")
    if not os.path.exists(pdf) or os.path.getsize(pdf) < 100:
        for attempt in range(3):
            r = subprocess.run(["curl", "-sfL", "--max-time", "180", "-o", pdf, url])
            if r.returncode == 0: break
            time.sleep(3 * (attempt + 1))
    if open(pdf, "rb").read(2) == b"PK":  # a few "PDFs" in the city's database are really Word documents
        import html, zipfile
        xml = zipfile.ZipFile(pdf).read("word/document.xml").decode("utf8")
        paras = [html.unescape(re.sub(r"<[^>]+>", "", x)) for x in re.findall(r"<w:p[ >].*?</w:p>", xml, flags=re.S)]
        text = "\n".join(x for x in paras if x.strip())
        open(out, "w").write(f"=== {key} proposal document, page 1 of 1 (Word document) ===\n{text.strip()}\n")
        return key, "Word document"
    try:
        rd = pypdf.PdfReader(pdf)
    except Exception as e:
        return key, f"unreadable: {e}"
    parts, ocrd = [], 0
    for i, p in enumerate(rd.pages):
        t, was_ocr = page_text(p); ocrd += was_ocr
        parts.append(f"=== {key} proposal document, page {i + 1} of {len(rd.pages)}{' (OCR)' if was_ocr else ''} ===\n{t.strip()}\n")
    open(out + ".tmp", "w").write("\n".join(parts)); os.rename(out + ".tmp", out)
    return key, f"{len(rd.pages)} pages, {ocrd} OCR"


if __name__ == "__main__":
    os.makedirs(PDF_DIR, exist_ok=True); os.makedirs(TXT_DIR, exist_ok=True)
    props = json.load(open(os.path.join(HERE, "votes.json")))["proposals"]
    items = sorted((k, p["documentUrl"]) for k, p in props.items() if p.get("documentUrl"))
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    with Pool(workers) as pool:
        for n, (key, msg) in enumerate(pool.imap_unordered(do, items), 1):
            print(f"{n}/{len(items)} {key} {msg}", flush=True)
    print("DONE")
