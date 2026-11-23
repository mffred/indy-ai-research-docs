"""Builds the data for /turnout: every Marion County precinct in six elections, grouped by City-County Council district.

Run: python3 _src/turnout-data/build_city.py   (needs openpyxl; downloads into _src/turnout-data/raw/, which is git-ignored)
Writes _src/turnout-data/city/data.json (district outlines, every precinct's numbers) and
_src/turnout-data/city/d/<n>.json (one per district: precinct shapes and major roads). build.py copies them to /turnout/.
See README.md in this folder for sources and checks.
"""
import csv, json, math, os, re, sys, time, urllib.parse, urllib.request
import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
RAW, OUT = os.path.join(HERE, "raw"), os.path.join(HERE, "city")
GIS = "https://gis.indy.gov/server/rest/services/OpenData"
PORTAL = "https://gis.indy.gov/portal/sharing/rest/content/items/{}/data"
FILES = {  # election -> (download URL, local name). Open data items are listed at data.indy.gov ("Election Results").
    "2023P": (PORTAL.format("9e45d50035e049c191600449ca46d707"), "2023P.xlsx"),
    "2023G": (PORTAL.format("b18b251e16c34d98a41148c3bdf4e1a7"), "2023G.xlsx"),
    "2024P": (PORTAL.format("1fca8989f1fa4acdba2ce7fb34a5e479"), "2024P.xlsx"),
    "2024G": (PORTAL.format("c869c853affe4f0c9ab0b580865bec80"), "2024G.xlsx"),
    "2026P": (PORTAL.format("51db465946dd477183f0181a2c4f4d8f"), "2026P.csv"),
    # Not yet on the open data portal; this is the Election Board's certified file (run 11/23/2026) from indy.gov/workflow/election-results
    "2026G": ("https://isaapi.indy.gov/ElectionNightReportingAPI/Document/DownloadC", "2026G.xlsx"),
}
PCT = re.compile(r"^[A-Z]{2}\d{3}$")
TWP = {"CN": "Center", "DE": "Decatur", "FR": "Franklin", "LA": "Lawrence", "PE": "Perry", "PK": "Pike", "WR": "Warren", "WS": "Washington", "WY": "Wayne"}


def get(url, path=None, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (indy-ai-research-docs data build)"})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            if path:
                open(path, "wb").write(data)
            return data
        except Exception as e:
            if i == tries - 1: raise
            time.sleep(3 * (i + 1))


def num(x):
    if x is None or x == "": return 0
    if isinstance(x, (int, float)): return int(round(x))
    s = str(x).replace(",", "").strip()
    if s.startswith("="): raise ValueError("formula without a cached value: " + s)
    return int(float(s)) if s else 0


def sheet_rows(wb, name):
    """{precinct: [cells...]} for one results sheet (header row first). Values, not formulas."""
    ws = wb[name]
    rows = list(ws.iter_rows(values_only=True))
    head = [str(h or "").strip() for h in rows[0]]
    out = {}
    for r in rows[1:]:
        p = str(r[0] or "").strip()
        if PCT.match(p): out[p] = r
    return head, out


def cand_cols(head, *needles):
    """Index of the column whose header contains every needle (case-insensitive)."""
    for i, h in enumerate(head):
        if all(n.lower() in h.lower() for n in needles): return i
    raise KeyError(f"no column with {needles} in {head}")


# ---------------------------------------------------------------- results
def load_results():
    os.makedirs(RAW, exist_ok=True)
    for k, (url, name) in FILES.items():
        p = os.path.join(RAW, name)
        if not os.path.exists(p):
            print("downloading", k); get(url, p)
    E = {}

    # 2023 primary: one row per precinct/office/candidate, with the precinct's ballots and registration on every row.
    wb = openpyxl.load_workbook(os.path.join(RAW, "2023P.xlsx"), read_only=True, data_only=True)
    e = {}
    for r in list(wb.worksheets[0].iter_rows(values_only=True))[1:]:
        p = str(r[0] or "").strip()
        if not PCT.match(p): continue
        x = e.setdefault(p, {"reg": num(r[6]), "bal": num(r[5]), "d": 0, "r": 0})
        if str(r[1]).strip().upper() == "MAYOR OF INDIANAPOLIS":
            party = str(r[2]).upper()
            if party.startswith("DEM"): x["d"] += num(r[4])
            elif party.startswith("REP"): x["r"] += num(r[4])
    E["2023P"] = e

    # 2023 general: Turnout sheet, mayor sheet, and one sheet per council district (which also gives each precinct's district)
    wb = openpyxl.load_workbook(os.path.join(RAW, "2023G.xlsx"), read_only=True, data_only=True)
    _, t = sheet_rows(wb, "Turnout")
    mh, m = sheet_rows(wb, "City of Indianapolis Mayor")
    di, dr = cand_cols(mh, "hogsett"), cand_cols(mh, "shreve")
    E["2023G"] = {p: {"reg": num(r[1]), "bal": num(r[2]), "d": num(m[p][di]), "r": num(m[p][dr])} for p, r in t.items()}
    p2d, council = {}, {}
    for n in range(1, 26):
        h, rows = sheet_rows(wb, f"City-County Council D{n}")
        cands = [(i, h[i]) for i in range(3, len(h)) if h[i] and h[i] != "None"]
        council[n] = [{"name": c, "votes": sum(num(r[i]) for r in rows.values())} for i, c in cands]
        for p in rows:
            if p in p2d: raise SystemExit(f"{p} is in two council districts")
            p2d[p] = n
    # Cities and towns inside Marion County that held their own 2023 races: a precinct with votes in that race is in (or partly in) it.
    cities = {}
    for city, sheet in [("Beech Grove", "City of Beach Grove Mayor"), ("Lawrence", "City of Lawrence Mayor"), ("Southport", "City of Southport Mayor"), ("Speedway", "Town of Speedway Clerk-Treas")]:
        h, rows = sheet_rows(wb, sheet)
        for p, r in rows.items():
            if sum(num(v) for v in r[3:] if v not in (None, "None")) > 0: cities[p] = city

    # 2024 primary: Turnout sheet has Democratic and Republican ballots separately
    wb = openpyxl.load_workbook(os.path.join(RAW, "2024P.xlsx"), read_only=True, data_only=True)
    h, t = sheet_rows(wb, "Turnout")
    ci, cr = cand_cols(h, "ballots", "democratic"), cand_cols(h, "ballots", "republican")
    E["2024P"] = {p: {"reg": num(r[1]), "bal": num(r[ci]) + num(r[cr]), "d": num(r[ci]), "r": num(r[cr])} for p, r in t.items()}

    # 2024 general: Turnout + President
    wb = openpyxl.load_workbook(os.path.join(RAW, "2024G.xlsx"), read_only=True, data_only=True)
    _, t = sheet_rows(wb, "Turnout")
    ph, pr = sheet_rows(wb, "President of the United States")
    di, ri = cand_cols(ph, "harris"), cand_cols(ph, "trump")
    E["2024G"] = {p: {"reg": num(r[1]), "bal": num(r[2]), "d": num(pr[p][di]), "r": num(pr[p][ri]),
                      "o": sum(num(v) for i, v in enumerate(pr[p][3:], 3) if i not in (di, ri) and v not in (None, "None"))} for p, r in t.items()}

    # 2026 primary: candidate votes only (no registration or ballots in the file). Both prosecutor nominees were unopposed.
    e = {}
    for r in csv.DictReader(open(os.path.join(RAW, "2026P.csv"), encoding="utf-8-sig")):
        p = r["PRECINCT"].strip()
        x = e.setdefault(p, {"d": 0, "r": 0})
        if r["OFFICE"].startswith("Prosecuting Attorney of Marion County"):
            if r["CANDIDATE"].strip().upper() == "RYAN MEARS": x["d"] += num(r["TOTAL"])
            elif r["CANDIDATE"].strip().upper() == "PHILIP FOUST": x["r"] += num(r["TOTAL"])
            else: raise SystemExit("unexpected prosecutor candidate " + r["CANDIDATE"])
    E["2026P"] = e

    # 2026 general: Turnout + Secretary of State
    wb = openpyxl.load_workbook(os.path.join(RAW, "2026G.xlsx"), read_only=True, data_only=True)
    _, t = sheet_rows(wb, "Turnout")
    sh, s = sheet_rows(wb, "Secretary of State")
    di, ri = cand_cols(sh, "bayh"), cand_cols(sh, "engling")
    E["2026G"] = {p: {"reg": num(r[1]), "bal": num(r[2]), "d": num(s[p][di]) if p in s else 0, "r": num(s[p][ri]) if p in s else 0,
                      "o": sum(num(v) for i, v in enumerate(s[p][3:], 3) if i not in (di, ri) and v not in (None, "None")) if p in s else 0} for p, r in t.items()}
    return E, p2d, council, cities


# ---------------------------------------------------------------- shapes
def rnd(c, k=5): return [round(c[0], k), round(c[1], k)]


def simplify(ring, tol):
    """Douglas-Peucker on one ring (lon/lat degrees)."""
    if len(ring) < 5: return ring
    def dp(pts):
        a, b = pts[0], pts[-1]; dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy) or 1e-12
        imax, dmax = 0, -1
        for i in range(1, len(pts) - 1):
            d = abs(dy * pts[i][0] - dx * pts[i][1] + b[0] * a[1] - b[1] * a[0]) / L
            if d > dmax: imax, dmax = i, d
        if dmax <= tol: return [a, b]
        return dp(pts[:imax + 1])[:-1] + dp(pts[imax:])
    if ring[0] == ring[-1]:  # closed ring: split at the point farthest from the start, simplify each half
        far = max(range(len(ring)), key=lambda i: math.hypot(ring[i][0] - ring[0][0], ring[i][1] - ring[0][1]))
        out = dp(ring[:far + 1])[:-1] + dp(ring[far:])
    else:
        out = dp(ring)
    return out if len(out) >= 4 else ring


def arcgis_polys(layer, where, fields, tol):
    q = urllib.parse.urlencode({"where": where, "outFields": fields, "outSR": 4326, "f": "json", "returnGeometry": "true"})
    d = json.loads(get(f"{GIS}/{layer}/query?{q}"))
    out = []
    for f in d["features"]:
        rings = [[rnd(c) for c in simplify(r, tol)] for r in f["geometry"]["rings"]]
        out.append((f["attributes"], rings))
    return out


def ring_area(r): return sum(r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1] for i in range(len(r) - 1)) / 2


def to_polys(rings):
    """Esri rings (outer clockwise, holes counter-clockwise) -> list of polygons [outer, *holes]."""
    polys = []
    for r in rings:
        if ring_area(r) < 0 or not polys: polys.append([r])  # clockwise in lon/lat = negative area = outer
        else: polys[-1].append(r)
    return polys


def roads_in(bbox):
    """Major roads (freeway to primary collector) crossing a bbox, merged by street name."""
    cls = {"FREEWAY": 0, "EXPRESSWAY": 0, "PRIMARY ARTERIAL": 1, "SECONDARY ARTERIAL": 2, "PRIMARY COLLECTOR": 3}
    where = "TFARE IN ('" + "','".join(cls) + "')"
    geo = ",".join(str(round(v, 5)) for v in bbox)
    feats, off = [], 0
    while True:
        q = urllib.parse.urlencode({"where": where, "geometry": geo, "geometryType": "esriGeometryEnvelope", "inSR": 4326, "spatialRel": "esriSpatialRelIntersects",
                                    "outFields": "FULL_STNAME,TFARE", "outSR": 4326, "f": "json", "resultOffset": off, "resultRecordCount": 2000})
        d = json.loads(get(f"{GIS}/OpenData_Transportation/MapServer/13/query?{q}"))
        feats += d.get("features", [])
        if not d.get("exceededTransferLimit"): break
        off += 2000
    by = {}
    for f in feats:
        n = (f["attributes"]["FULL_STNAME"] or "").strip()
        if not n or "RAMP" in n: continue
        c = cls[f["attributes"]["TFARE"]]
        e = by.setdefault(n, {"n": nice_street(n), "c": c, "l": []})
        e["c"] = min(e["c"], c)
        for path in f["geometry"]["paths"]:
            e["l"].append([rnd(p) for p in simplify(path, 0.00004)])
    return list(by.values())


def nice_street(n):
    words = []
    for w in n.split():
        m = re.match(r"^0*(\d+)(ST|ND|RD|TH)$", w)
        if m: words.append(m.group(1) + m.group(2).lower())
        elif re.match(r"^(I|US|SR)-?\d+$", w) or w in ("I", "US", "SR"): words.append(w)
        elif w == "MC": words.append("Mc")
        else: words.append(w.capitalize())
    return re.sub(r"\bMc ([A-Z])", lambda m: "Mc" + m.group(1), " ".join(words))


def bbox(polys, pad=0.004):
    xs = [c[0] for p in polys for r in p for c in r]; ys = [c[1] for p in polys for r in p for c in r]
    return [min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad]


# ---------------------------------------------------------------- build
def main():
    E, p2d, council, cities = load_results()
    members = {m["district"]: m["name"] for m in json.load(open(os.path.join(HERE, "..", "council-data", "members.json")))["members"] if m.get("district")}
    prec = arcgis_polys("OpenData_Political/MapServer/2", "1=1", "PRECINCT", 0.00003)
    dist = arcgis_polys("OpenData_Political/MapServer/1", "1=1", "COUNCIL", 0.0004)
    ids = {a["PRECINCT"] for a, _ in prec}

    # ---- checks: every source covers the same precincts, and every precinct has a district
    problems = []
    for k, e in E.items():
        extra, missing = set(e) - ids, ids - set(e)
        if extra: problems.append(f"{k}: precincts not on the map: {sorted(extra)}")
        if missing: print(f"note: {k} has no row for {sorted(missing)} (left blank)")
    if ids - set(p2d): problems.append(f"precincts without a council district: {sorted(ids - set(p2d))}")
    if problems: raise SystemExit("\n".join(problems))

    ELECTIONS = [
        {"k": "2023P", "t": "May 2023 primary", "short": "2023 primary", "turnout": True, "race": "Indianapolis mayor primary", "dl": "Democratic mayor primary votes", "rl": "Republican mayor primary votes", "primary": True},
        {"k": "2023G", "t": "November 2023 general", "short": "2023 general", "turnout": True, "race": "Indianapolis mayor", "dl": "Joe Hogsett (D)", "rl": "Jefferson Shreve (R)"},
        {"k": "2024P", "t": "May 2024 primary", "short": "2024 primary", "turnout": True, "race": "Party ballots", "dl": "Democratic ballots", "rl": "Republican ballots", "primary": True},
        {"k": "2024G", "t": "November 2024 general", "short": "2024 general", "turnout": True, "race": "President", "dl": "Kamala Harris (D)", "rl": "Donald Trump (R)", "ol": "Others"},
        {"k": "2026P", "t": "May 2026 primary", "short": "2026 primary", "turnout": False, "race": "Prosecutor primary (both unopposed)", "dl": "Ryan Mears (D) votes", "rl": "Philip Foust (R) votes", "primary": True},
        {"k": "2026G", "t": "November 2026 general", "short": "2026 general", "turnout": True, "race": "Secretary of State", "dl": "Beau Bayh (D)", "rl": "Max Engling (R)", "ol": "Others (incl. Greg Ballard, Lincoln)"},
    ]
    KEYS = ["reg", "bal", "d", "r", "o"]
    # Precinct rows: [district, township, city, then per election [reg, bal, d, r, o] (null where the source has no figure)]
    P = {}
    for p in sorted(ids):
        row = {"d": p2d[p], "t": TWP[p[:2]], "c": cities.get(p)}
        for el in ELECTIONS:
            x = E[el["k"]].get(p)
            row[el["k"]] = [x.get(k) if x else None for k in KEYS] if x else None
        P[p] = row

    def total(sel, k):
        out = [0] * 5
        for p in sel:
            v = P[p][k]
            if v: out = [a + (b or 0) for a, b in zip(out, v)]
        return out

    county = {el["k"]: total(ids, el["k"]) for el in ELECTIONS}
    print("county totals:", {k: v[:2] for k, v in county.items()})

    os.makedirs(os.path.join(OUT, "d"), exist_ok=True)
    districts = []
    for a, rings in sorted(dist, key=lambda x: int(x[0]["COUNCIL"])):
        n = int(a["COUNCIL"])
        mine = [p for p in ids if p2d[p] == n]
        polys = to_polys(rings)
        districts.append({"n": n, "member": members.get(n), "polys": polys, "precincts": len(mine),
                          "tot": {el["k"]: total(mine, el["k"]) for el in ELECTIONS}, "race2023": council[n],
                          "twps": sorted({TWP[p[:2]] for p in mine}), "cities": sorted({cities[p] for p in mine if p in cities})})
        shapes = [{"id": pa["PRECINCT"], "polys": to_polys(pr)} for pa, pr in prec if pa["PRECINCT"] in mine]
        bb = bbox(polys)
        detail = {"n": n, "precincts": shapes, "roads": roads_in(bb)}
        json.dump(detail, open(os.path.join(OUT, "d", f"{n}.json"), "w"), separators=(",", ":"))
        print(f"district {n}: {len(mine)} precincts, {len(detail['roads'])} roads, {os.path.getsize(os.path.join(OUT, 'd', f'{n}.json')) // 1024} KB")

    # Freeways across the whole county, for orientation on the citywide map
    allpolys = [p for x in districts for p in x["polys"]]
    freeways = [r for r in roads_in(bbox(allpolys, 0.01)) if r["c"] == 0]
    for r in freeways: r["l"] = [[rnd(c, 4) for c in simplify(l, 0.0003)] for l in r["l"]]
    data = {"built": time.strftime("%Y-%m-%d"), "elections": ELECTIONS, "keys": KEYS, "county": county, "districts": districts, "precincts": P, "freeways": freeways}
    json.dump(data, open(os.path.join(OUT, "data.json"), "w"), separators=(",", ":"))
    print("data.json", os.path.getsize(os.path.join(OUT, "data.json")) // 1024, "KB")


if __name__ == "__main__":
    main()
