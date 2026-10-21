"""Builds data.json for the Beech Grove budget page from text extracted from the city's own PDFs.
Sources (all on the Clerk-Treasurer page, beechgrove.com/clerk-treasurers-office):
  form1.txt  = 2027 Budget Form 1 (line items; "Advertised"), pypdf text of Form1+(3).pdf
  form2.txt  = 2027 Budget Form 2 (non-property-tax revenue estimates), pypdf text of Form+2+Revenues.pdf
Run: python3 _src/beech-grove-data/make_data.py   (checks every fund total against the PDF's own totals)"""
import re, json, collections, pathlib
HERE = pathlib.Path(__file__).resolve().parent
t = (HERE / "form1.txt").read_text().replace("=====PAGE=====", "\n")
t = re.sub(r"Page \d+\s*\nGenerated:[^\n]*\n", "", t)
t = re.sub(r"Fund\s*\nDepartment\s*\nCategory\s*\nSub-Category.*?Adopted\n", "", t, flags=re.S)
FUNDS = {"0061": "Rainy Day", "0101": "General", "0256": "Public Safety Local Income Tax", "0283": "Lease Rental Payment", "0341": "Fire Pension", "0342": "Police Pension", "0706": "Local Road & Street", "0708": "Motor Vehicle Highway", "1151": "Continuing Education", "1310": "Park Nonreverting - Capital", "9507": "Home-Rule Fund #8", "9509": "Home-Rule Fund #10", "9510": "Home-Rule Fund #11", "9511": "Building & Construction Fees", "9512": "Motor Vehicle License Excise Surtax"}
DEPTS = {"0000": "No department", "0041": "Clerk-Treasurer", "0044": "Mayor", "0069": "City Council", "0077": "Board of Public Works & Safety", "0164": "City Hall", "0165": "Senior Center", "0167": "Community Center", "0248": "City Court", "0301": "Ambulance / EMS", "0362": "Fire Department", "0370": "Police Department", "0801": "Parks Department", "9600": "No department"}
CATS = ["Personal Services", "Supplies", "Other Services and Charges", "Capital Outlays", "Debt Service"]
norm = lambda s: re.sub(r"\s+", " ", s).strip()
pair = re.compile(r"\$([\d,]+)\s*\n\$([\d,]+)\s*\n")
pos, rows, totals = 0, [], {}
for m in pair.finditer(t):
    chunk, pos = t[pos:m.start()], m.end()
    adv = int(m.group(1).replace(",", ""))
    flat = norm(chunk)
    if "UNIT TOTAL" in flat[:20]: continue
    if flat.endswith("Total"):
        fm = re.findall(r"(\d{4})-[^$]*? Total$", flat)
        totals[re.findall(r"(\d{4})-", flat)[-1]] = adv; continue
    code = re.search(r"\b\d{9,10}\b", flat)
    cut = code.start() if code else len(flat)
    pre = flat[:cut]
    pre = re.sub(r"^.*?Total ", "", pre) if re.match(r"^[^0-9]*\d{4}-.*Total ", pre) else pre
    pre = pre[pre.find("0061-RAINY"):] if "0061-RAINY" in pre else pre
    fm = re.search(r"(?:^|\s)(\d{4})-", pre)
    if not fm:
        print("NOFUND", pre[:120]); continue
    fund = fm.group(1); pre = pre[fm.start():].strip()
    dm = re.search(r"(\d{4}) - ", pre.split(" ", 1)[1])
    dept = dm.group(1)
    cat = next((c for c in CATS if c in pre), None)
    sub = pre.split(cat, 1)[1].strip() if cat else ""
    rc = re.search(r"\b\d{9,10}\b", chunk)
    # Line-item text is hard-wrapped by the PDF: a line break with no trailing space splits a word, so rejoin it.
    item = re.sub(r"(?<=\S)\n", "", chunk[rc.end():]) if rc else ""
    item = norm(item)
    item = re.sub(r"^[\d.]*\.\d{3}\s*", "", item)
    if not item: item = re.sub(r"^[\d.]+ ", "", sub)
    rows.append(dict(f=fund, d=dept, c=cat, s=sub, i=item, a=adv))
# Some sub-category fields absorbed the line-item text when the PDF omitted the code; split them.
for r in rows:
    for key in ("Payments on Bonds and Other Debt Principal Lease Rental Payments", "Machinery, Equipment, and Vehicles", "Improvements Other Than Building", "Operating Supplies", "Professional Services", "Other Services and Charges", "Salaries and Wages", "Employee Benefits"):
        if r["s"].startswith(key) and r["s"] != key and not r["i"]:
            r["i"] = r["s"][len(key):].strip(); r["s"] = key
    if r["s"].startswith("Payments on Bonds"): r["s"], r["i"] = "Payments on Bonds and Other Debt", "Lease rental payments"
    r["s"] = r["s"].replace(" Motor Vehicle License Excise Surtax and Fund", "")
    if not r["i"]: r["i"] = r["s"]
    r["i"] = re.sub(r"^[\d.]+ ", "", r["i"]).replace("Improvements Other Than Building Improvements (wheel tax)", "Improvements (wheel tax)").strip() or r["s"]
SUBS = sorted({"Buildings", "Communication and Transportation", "Employee Benefits", "Improvements Other Than Building", "Infrastructure", "Insurance", "Machinery, Equipment, and Vehicles", "Office Supplies", "Operating Supplies", "Other Capital Outlays", "Other Personal Services", "Other Services and Charges", "Other Supplies", "Payments on Bonds and Other Debt", "Printing and Advertising", "Professional Services", "Rentals", "Repair and Maintenance Supplies", "Repairs and Maintenance", "Salaries and Wages", "Utility Services"}, key=len, reverse=True)
for r in rows:  # rows whose PDF line item had no code: the line-item text ended up inside the sub-category field
    sub = next((x for x in SUBS if r["s"].startswith(x)), r["s"])
    if sub != r["s"]:
        rest = re.sub(r"^[\d. ]+(?=[A-Z])", "", r["s"][len(sub):].strip())
        r["s"], r["i"] = sub, (rest or r["i"])
    r["i"] = re.sub(r"(?<=[A-Z]) (?=[A-Z]{1,3}\b)(?!AND|THE)", " ", r["i"])
FIX = {"Improvements Other Than Building Motor Vehicle License Excise Surtax and Fund": "Improvements other than buildings (wheel tax)", "PARKS NONREVERTI NG CAPITAL": "Parks nonreverting capital", "PERMIT - BUILDING COMMISSION ER": "PERMIT - BUILDING COMMISSIONER", "PST/ AMBULANCE CONTRACTUAL PRINCIPAL 2022, 2023, 2": "PST / AMBULANCE CONTRACTUAL PRINCIPAL (2022, 2023, 2...)"}  # the PDF itself cuts this label short
for r in rows: r["i"] = FIX.get(r["i"], r["i"])
by = collections.Counter()
for r in rows: by[r["f"]] += r["a"]
bad = {f: (by[f], totals.get(f)) for f in FUNDS if by[f] != totals.get(f)}
assert not bad, bad
# Form 2
t2 = (HERE / "form2.txt").read_text().replace("=====PAGE=====", "\n")
t2 = re.sub(r"Page \d+\s*\nGenerated:[^\n]*\n", "", t2)
rev, fund = [], None
for blk in re.split(r"\n(?=\d{4}-)", t2):
    fm = re.match(r"(\d{4})-", blk)
    if not fm: continue
    f = fm.group(1)
    for mm in re.finditer(r"\n(R\d{3})\n(.*?)\n\$([\d,]+)\n\$([\d,]+)", blk, re.S):
        rev.append(dict(f=f, code=mm.group(1), n=norm(mm.group(2)), h2=int(mm.group(3).replace(",", "")), y=int(mm.group(4).replace(",", ""))))
out = dict(funds=FUNDS, depts=DEPTS, items=rows, revenue=rev, fundTotals={f: by[f] for f in FUNDS})
(HERE / "data.json").write_text(json.dumps(out, separators=(",", ":")))
print(len(rows), "line items; total", sum(by.values()), "| revenue rows", len(rev), "sum 2027", sum(r["y"] for r in rev))
