"""Builds history.json (2020-2027 history for the Beech Grove budget page).

Inputs, all from the city's public budget archive (the Dropbox folder linked from beechgrove.com/clerk-treasurers-office):
  Form 4 (appropriation ordinance, fund totals): 2020, 2021, 2025 are text PDFs; 2022, 2023, 2024, 2026 are scans, OCR'd with
    tesseract (sources/form4-*-ocr.txt). Where OCR dropped a figure, the figure is filled from the other arithmetic: the
    ordinance's own total minus the legible funds (checked below).
  Fiscal Plan, Sept 9 2024 draft (sources/fiscal-plan-2024-parsed.json): General Fund departments and revenue, 2021-2025.
  2026 department budgets: the Oct 6 2025 Council packet's budget summary table.
  2027: data.json (Form 1 advertised, make_data.py).
Run: python3 _src/beech-grove-data/make_history.py"""
import json, pathlib
HERE = pathlib.Path(__file__).resolve().parent
YEARS = [2020, 2021, 2022, 2023, 2024, 2025, 2026, 2027]
# Fund appropriations by year (Form 4 adopted; 2027 = advertised Form 1). Key: fund code, value per year 2020..2027
F = {
 "0101": [9421970, 10197020, 10562807, 11065879, 11559554, 12070917, 12413939, 12671403],   # General
 "0256": [1944229, 1993200, 2128161, 2146158, 2332500, 2646124, 2728691, 2826891],        # Public Safety local income tax (home-rule fund 9500 before 2025)
 "debt": [229913, 236051, 236498, 121380, 0, 0, 0, 0],                                    # Debt service (0180)
 "0283": [0, 0, 0, 395000, 899500, 1073000, 1077000, 1077000],                            # Lease rental (police station 2022 lease, gun range 2023 lease)
 "0341": [382000, 389000, 0, 40000, 40000, 40000, 40000, 41200],                          # Fire pension
 "0342": [648000, 533000, 533000, 533000, 543000, 554000, 570620, 586755],                # Police pension
 "0706": [595000, 518500, 556000, 556000, 556000, 490000, 476585, 295000],                # Local road & street
 "0708": [1622870, 1316350, 1378713, 1418500, 1758500, 1714900, 1592345, 1403595],        # Motor vehicle highway
 "1151": [40000, 40000, 40000, 40000, 40000, 40000, 20000, 20000],                        # Continuing education (police)
 "1310": [50000, 25000, 10000, 10000, 10000, 10000, 10000, 10000],                        # Park nonreverting
 "9507": [0, 0, 260000, 287845, 389061, 408000, 495240, 500195],                          # Home-rule #8: school policing
 "opioid": [0, 0, 0, 0, 11900, 15926, 16404, 16600],                                      # Home-rule #10 + #11 (opioid settlement)
 "9511": [0, 0, 0, 0, 0, 0, 0, 19500],                                                    # Building & construction fees
 "9512": [0, 0, 0, 0, 0, 0, 0, 225000],                                                   # Wheel tax / surtax
}
FUND_NAMES = {"0101": "General", "0256": "Public Safety Local Income Tax", "debt": "Debt Service", "0283": "Lease Rental Payment", "0341": "Fire Pension", "0342": "Police Pension", "0706": "Local Road & Street", "0708": "Motor Vehicle Highway", "1151": "Police Continuing Education", "1310": "Park Nonreverting", "9507": "School Policing (Home-Rule #8)", "opioid": "Opioid Settlement (Home-Rule #10, #11)", "9511": "Building & Construction Fees", "9512": "Wheel Tax / Surtax"}
# Each year's total as printed on the ordinance (Form 4 civil funds + home-rule funds); 2027 = Form 1 total
PRINTED = [14933982, 15248121, 15705179, 16613762, 18140015, 19062867, 19440824, 19693139]
for i, y in enumerate(YEARS):
    s = sum(v[i] for v in F.values())
    assert s == PRINTED[i], (y, s, PRINTED[i])
# General Fund departments, original certified budget. 2021-2024: Fiscal Plan (sums to Form 4 General exactly);
# 2025-2026: Council packet 10/6/2025 summary table (2025 Senior Center per Form 4 total); 2027: Form 1 advertised.
fp = json.load(open(HERE / "sources" / "fiscal-plan-2024-parsed.json"))
fd = fp["General - Departments"]
DEPTS = [("0370", "Police Department", "CLEANME"), ("0362", "Fire Department (IFD contract)", ""), ("0301", "Ambulance / EMS", ""), ("0077", "Board of Public Works & Safety", ""), ("0164", "City Hall", ""), ("0801", "Parks Department", ""), ("0167", "Community Center", ""), ("0165", "Senior Center", ""), ("0248", "City Court", ""), ("0041", "Clerk-Treasurer", ""), ("0044", "Mayor", ""), ("0069", "City Council", ""), ("cable", "Cable / contractual", "")]
FPKEY = {"0370": "POLICE DEPARTMENT", "0362": "FIRE DEPARTMENT", "0301": "EMS", "0077": "BOARD OF PUBLIC WORKS", "0164": "CITY HALL", "0801": "PARKS & RECREATION", "0167": "COMMUNITY SERVICES", "0165": "SENIOR CITIZENS CENTER", "0248": "CITY COURT", "0041": "CLERK - TREASURER", "0044": "MAYOR", "0069": "CITY COUNCIL", "cable": "CABLE / MISCELLANEOUS"}
D25 = {"0041": 142585, "0044": 104271, "0069": 52425, "0077": 1728638, "0164": 348250, "0165": 188330, "0167": 339256, "0248": 174803, "0301": 1030363, "0362": 3547660, "0370": 4080245, "0801": 320091, "cable": 14000}
D26 = {"0041": 144649, "0044": 106494, "0069": 51074, "0077": 1780129, "0164": 355925, "0165": 176106, "0167": 310532, "0248": 182512, "0301": 1226314, "0362": 3654090, "0370": 4081468, "0801": 335646, "cable": 9000}
data = json.load(open(HERE / "data.json"))
D27 = {k: 0 for k in D25}
for r in data["items"]:
    if r["f"] == "0101":
        D27["cable" if r["d"] == "9600" else r["d"]] += r["a"]
dept = {}
for code, name, _ in DEPTS:
    s = fd[FPKEY[code]]
    cb = s["Total Original Certified Budget"][:4]          # 2021..2024
    ex = s["TOTAL EXPENDITURES"][:3]                         # 2021..2023 actual
    cats = {k: s[k][:5] for k in ("Personal Services", "Supplies", "Other Services and Charges", "Capital Outlay") if k in s}
    dept[code] = dict(name=name, budget=[None] + cb + [D25[code], D26[code], D27[code]], actual=[None] + ex + [None] * 4, cats=cats)
for i, y in enumerate(YEARS):
    if y >= 2021:
        s = sum(d["budget"][i] for d in dept.values())
        assert s == F["0101"][i], (y, s, F["0101"][i])
# Functions (2021-2027)
def col(code, i): return F[code][i]
FUNCS = [("ps", "Public safety", "Police, fire contract, EMS, the public safety income tax fund, pensions, police training and school policing"),
         ("st", "Streets & roads", "Motor Vehicle Highway, Local Road & Street, wheel tax"),
         ("pc", "Parks & community", "Parks, Senior Center, Community Center, park capital fund"),
         ("gg", "General government", "Mayor, Clerk-Treasurer, Council, City Court, City Hall, Board of Works (citywide insurance and benefits), permit fees"),
         ("db", "Debt, leases & other", "Debt service, the police station and gun range lease payments, opioid settlement funds")]
def fn(i):
    d = {k: dept[k]["budget"][i] for k in dept}
    return dict(
        ps=d["0370"] + d["0362"] + d["0301"] + col("0256", i) + col("0341", i) + col("0342", i) + col("1151", i) + col("9507", i),
        st=col("0706", i) + col("0708", i) + col("9512", i),
        pc=d["0801"] + d["0167"] + d["0165"] + col("1310", i),
        gg=d["0077"] + d["0164"] + d["0248"] + d["0041"] + d["0044"] + d["0069"] + d["cable"] + col("9511", i),
        db=col("debt", i) + col("0283", i) + col("opioid", i))
func = {y: fn(i) for i, y in enumerate(YEARS) if y >= 2021}
for i, y in enumerate(YEARS):
    if y >= 2021: assert sum(func[y].values()) == PRINTED[i], (y, sum(func[y].values()), PRINTED[i])
# General Fund revenue by source (Fiscal Plan: 2021-2023 actual, 2024-2025 budget)
g = fp["0101 General"]
GROUPS = {"pt": ["Property Tax and COIT Levy Replacement"],
          "it": ["County Option Income Tax (COIT)", "LIT Levy Freeze", "Supplemental LIT"],
          "ps": ["PS LOIT Police & Fire OT", "PS LOIT Police & Fire Personal Services", "PS LOIT EMS"],
          "ex": ["Financial Institution Tax", "Auto and Aircraft Excise Tax", "Commercial Vehicle Excise Tax (CVET)", "ABC Excise", "ABC Gallonage", "State Cigarette Tax - General Fund", "Riverboat", "Payment In Lieu Of Tax (PILOT)"],
          "fe": ["Emergency Service Fees", "Building Permits", "Other Licenses and Permits", "Other / Cable TV", "Park Receipts", "Variance Board", "City citations / court fees", "Police Reimbursement", "BG School"],
          "ot": ["Return on Investment (ROI)", "Miscellaneous Revenue", "Reimbursements", "Refunds", "Sale of Assets", "Transfer In", "St. Francis Greenway Trail", "Hornet / ELF"]}
used = {n for v in GROUPS.values() for n in v}
rev = {k: [sum(g[n][i] for n in v if n in g) for i in range(5)] for k, v in GROUPS.items()}
for i in range(5):
    assert abs(sum(rev[k][i] for k in rev) - g["TOTAL REVENUES"][i]) <= 5, (i, sum(rev[k][i] for k in rev), g["TOTAL REVENUES"][i])  # the plan's own lines are off by $2 in 2022
gen = dict(revenue=g["TOTAL REVENUES"][:5], spending=g["TOTAL EXPENDITURES"][:5], ending=g["ENDING FUND BALANCE"][:5], begin=g["BEGINNING FUND BALANCE"][:5])
# Funds outside the civil-city appropriation totals (Fiscal Plan)
outside = {}
for k, t in (("sewer", "0606 Utility"), ("storm", "0605 Storm Water"), ("tif", "9999 Tax Increment Financing (TIF)")):
    s = fp[t]
    outside[k] = dict(revenue=s["TOTAL REVENUES"][:5], spending=s["TOTAL EXPENDITURES"][:5], ending=s["ENDING FUND BALANCE"][:5])
out = dict(years=YEARS, funds=F, fundNames=FUND_NAMES, printed=PRINTED, dept=dept, funcs=[dict(k=k, n=n, d=d) for k, n, d in FUNCS], func=func, genRev=rev, gen=gen, outside=outside)
(HERE / "history.json").write_text(json.dumps(out, separators=(",", ":")))
print("ok", {y: round(sum(func[y].values()) / 1e6, 2) for y in func})
