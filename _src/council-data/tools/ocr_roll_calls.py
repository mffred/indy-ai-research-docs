"""OCR each roll-call PDF page (scans are rotated sideways) into one plain-text file per meeting.
Run from anywhere: python3 _src/council-data/tools/ocr_roll_calls.py  (needs tesseract; reads pdf/roll-calls/, writes roll-calls/)."""
import glob, io, os, subprocess, sys, tempfile
from multiprocessing import Pool
import pypdf

def ocr_image(data, ext):
    with tempfile.TemporaryDirectory() as t:
        src = os.path.join(t, "p." + ext); open(src, "wb").write(data)
        png = os.path.join(t, "p.png")
        subprocess.run(["sips", "-s", "format", "png", src, "--out", png], capture_output=True)
        best = ""
        for rot in (270, 90, 0, 180):  # these scans are nearly always 270
            r = os.path.join(t, f"r{rot}.png")
            if rot: subprocess.run(["sips", "-r", str(rot), png, "--out", r], capture_output=True)
            else: r = png
            out = subprocess.run(["tesseract", r, "stdout", "--psm", "4"], capture_output=True, text=True).stdout
            if any(k in out for k in ("Council", "Proposal", "Yea", "Nay", "Excused")): return out
            if len(out) > len(best): best = out
        return best

def page_text(page):
    imgs = page.images
    if imgs:
        img = imgs[0]
        return ocr_image(img.data, img.name.rsplit(".", 1)[-1].lower())
    return page.extract_text() or ""

def do(path):
    date = os.path.basename(path)[:-4]
    out = f"roll-calls/{date}.txt"
    if os.path.exists(out): return date, "skip"
    r = pypdf.PdfReader(path)
    parts = [f"=== {date} roll call, page {i+1} of {len(r.pages)} ===\n" + page_text(p).strip() + "\n" for i, p in enumerate(r.pages)]
    open(out + ".tmp", "w").write("\n".join(parts)); os.rename(out + ".tmp", out)
    return date, len(r.pages)

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    with Pool(8) as pool:
        for date, n in pool.imap_unordered(do, sorted(glob.glob("pdf/roll-calls/*.pdf"))):
            print(date, n, flush=True)
    print("DONE")
