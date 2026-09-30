"""Parse council roll-call votes out of the plain-text minutes (and, for meetings whose minutes aren't
posted yet, the OCR'd roll-call sheets) into _src/council-data/votes.json.

Run: python3 _src/council-data/tools/parse_votes.py
Every vote keeps the meeting date, the PDF page it came from and the source document's URL, so any
row on the public page can be traced back to the official record.
"""
import glob, json, os, re, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = json.load(open(os.path.join(HERE, "sources.json")))["meetings"]

# Surnames as the records print them -> canonical key. Two Evanses served 2021-23 and two Browns from
# 2024, which the records tell apart with -E/-J and -A/-J (or A./J. Brown).
SURNAMES = ["Adamson", "Allen", "Annee", "Bain", "Barth", "Boots", "Brown-A", "Brown-J", "Brown", "Cahill",
            "Carlino", "Delaney", "Dilk", "Evans-E", "Evans-J", "Evans", "Gibson", "Graves", "Gray", "Hart",
            "Jackson", "Jones", "Larrison", "Lewis", "Mascari", "Masquelier", "McCormick", "Mowery", "Nielsen",
            "Oliver", "Osili", "Perkins", "Potts", "Ray", "Roberts", "Robinson", "Wells"]
LABELS = {"YEAS": "Yes", "YEA": "Yes", "NAYS": "No", "NAY": "No", "ABSENT": "Absent", "EXCUSED": "Absent",
          "NOT VOTING": "Not voting", "ABSTAIN": "Abstain", "ABSTAINED": "Abstain", "ABSTAINING": "Abstain"}


def spaced(word):
    """Regex for a word whose letters the PDF text may have split with stray spaces ('Ad amson')."""
    return r"\s?".join(re.escape(ch) for ch in word)


def name_pattern():
    alts = []
    for s in sorted(SURNAMES, key=len, reverse=True):
        if "-" in s:
            base, suf = s.split("-")
            alts.append((rf"(?:{spaced(base)}\s?-\s?{suf}\b|{suf}\.\s?{spaced(base)}\b)", s))
        else:
            alts.append((spaced(s) + r"\b", s))
    return alts


NAME_ALTS = [(re.compile(p), s) for p, s in name_pattern()]


def read_names(text):
    """Consume a comma/and-separated run of surnames from the start of text. Returns (names, chars used)."""
    names, pos = [], 0
    while True:
        m = re.match(r"\s*(?:,|\band\b)?\s*", text[pos:])
        start = pos + m.end()
        for rx, key in NAME_ALTS:
            mm = rx.match(text, start)
            if mm:
                names.append(key); pos = mm.end(); break
        else:
            return names, pos


def ocr_name(token):
    """Match one OCR'd word from a roll-call sheet to a surname, allowing small misreads ('Poits', 'Evans-&')."""
    import difflib
    t = token.strip(".,;:!|'")
    if t.endswith("-") and t[:-1] in SURNAMES: t = t[:-1]  # "Brown-" / "Jones-" with the suffix lost or a stray hyphen
    if t in SURNAMES: return t
    m = re.fullmatch(r"(Evans|Brown)-?(.)", t)
    if m:  # the suffix letter is the part OCR most often mangles
        suf = {"E": "E", "&": "E", "F": "E", "J": "J", "A": "A", "4": "A"}.get(m.group(2).upper())
        return f"{m.group(1)}-{suf}" if suf else None
    if len(t) < 3: return None
    close = difflib.get_close_matches(t, SURNAMES, n=1, cutoff=0.7)
    return close[0] if close else None


def load_minutes(date):
    """Minutes text for a meeting with whitespace collapsed and page breaks kept as ⟦pN⟧ markers."""
    raw = open(os.path.join(HERE, "minutes", f"{date}.txt")).read()
    raw = re.sub(r"^=== \S+ minutes, page (\d+) of \d+ ===$", r" ⟦p\1⟧ ", raw, flags=re.M)
    # running page headers: the meeting date or "Journal of the City-County Council", and a page number
    raw = re.sub(r"⟦p(\d+)⟧\s*\n(?:[A-Z][a-z]+ \d{1,2}, \d{4}|Journal of the City-County Council)\s*\n\s*\d+\s*\n", r"⟦p\1⟧ ", raw)
    return re.sub(r"\s+", " ", raw)


def page_at(text, pos):
    ps = re.findall(r"⟦p(\d+)⟧", text[:pos])
    return int(ps[-1]) if ps else 1


PROP_REF = re.compile(r"Proposal Nos?\.\s*((?:\d+\s*(?:-\s*\d+)?\s*(?:,|and|&)?\s*)+),\s*(20\d\d)", re.I)


def real(refs):
    """Drop misreads like "Proposal No. 2022" (a year caught as a number)."""
    return [(n, y) for n, y in refs if n < 1000]


def expand(nums, year):
    out = []
    for part in re.split(r",|\band\b|&", nums):
        part = re.sub(r"\s+", "", part)  # the PDF text splits some numbers: "28 8"
        if not part: continue
        if "-" in part:
            a, b = [int(x) for x in part.split("-")]
            if 0 <= b - a <= 60: out += [(n, int(year)) for n in range(a, b + 1)]
        else:
            out.append((int(part), int(year)))
    return out


def parse_minutes(date, titles, types, sponsors, rezonings):
    text = load_minutes(date)
    # Titles. The PDF text sometimes splits words ("Counci llor", "th e") and puts a space before
    # periods, so the fixed phrases are matched with S(), which allows a stray space between letters.
    def S(phrase): return r"\s*".join(re.escape(ch) if not ch.isspace() else r"\s+" for ch in phrase)
    NO = r"(?i:PROPOSAL)\s+NO\s?\.\s*(\d+)\s*,\s*(20\d\d)\s*\.?"
    COUNCILORS = r"(" + S("Counci") + r"l?\s*l?\s*" + S("or") + r"s?\s.{2,200}?)"
    def clean(x): return re.sub(r"⟦p\d+⟧\s*", "", x).strip()
    def add(m, title_group, sponsor_group=None):
        key = (int(m.group(1)), int(m.group(2)))
        t = clean(m.group(title_group))
        if len(t) > 8: titles.setdefault(key, t[0].upper() + t[1:])
        if sponsor_group: sponsors.setdefault(key, re.sub(r"^Counci\s?l?\s?l?\s?ors?\s*", "", clean(m.group(sponsor_group))))
    # 1. Introduction: 'PROPOSAL NO. 212, 2026. Introduced by Councilor Boots. The Clerk read the proposal entitled: "..."'
    for m in re.finditer(NO + r"\s*" + S("Introduced by") + r"\s+" + COUNCILORS + r"\s*\.\s*" + S("The Clerk read the proposal") + r"s?\s*" + S("entitled") + r"\s*:?\s*[\"“](.+?)[\"”]", text):
        add(m, 4, 3)
    # 2a. Committee report, keyed on its heading (the body sometimes names the wrong number:
    #     'PROPOSAL NO. 24, 2025. Councilor Robinson reported that ... heard Proposal No. 23, 2025 ...')
    for m in re.finditer(NO + r"\s*" + COUNCILORS.replace("{2,200}", "{2,60}") + r"\s+" + S("reported that") + r".{0,300}?" + S("The proposal") + r"\s*,?\s*" + S("sponsored by") + r"\s+" + COUNCILORS + r"\s*,\s+([a-z].{10,500}?)(?<!\s[A-Z])(?<!\sSt)(?<!\sNo)(?<!\sInc)(?<!\sDr)(?<!\sMr)(?<!\sMs)(?<!\sJr)(?<!\sSr)(?<!\sCo)\s*\.[\"\u201d']?\s", text):
        key = (int(m.group(1)), int(m.group(2)))
        t = clean(m.group(5))
        if len(t) > 8: titles.setdefault(key, t[0].upper() + t[1:])
        sponsors.setdefault(key, re.sub(r"^Counci\s?l?\s?l?\s?ors?\s*", "", clean(m.group(4))))
    # 2b. Committee report: '... heard Proposal No. 285, 2024 on August 22, 2024. The proposal, sponsored by Councilor Osili, appoints ...'
    # 3. Special resolution read at the meeting: 'PROPOSAL NO. 223, 2026. The proposal, sponsored by Councilor Evans, celebrates ...'
    for m in re.finditer(r"(?:" + NO + r"|Proposal No\.\s*(\d+)\s*,\s*(20\d\d)\s+on\s+[A-Z][^.]{3,80}?\d{4}\s*\.)\s*" + S("The proposal") + r"\s*,?\s*" + S("sponsored by") + r"\s+" + COUNCILORS + r"\s*,\s+([a-z].{10,500}?)(?<!\s[A-Z])(?<!\sSt)(?<!\sNo)(?<!\sInc)(?<!\sDr)(?<!\sMr)(?<!\sMs)(?<!\sJr)(?<!\sSr)(?<!\sCo)\s*\.[\"\u201d']?\s", text):
        g = (1, 2) if m.group(1) else (3, 4)
        key = (int(m.group(g[0])), int(m.group(g[1])))
        t = clean(m.group(6))
        if len(t) > 8: titles.setdefault(key, t[0].upper() + t[1:])
        sponsors.setdefault(key, re.sub(r"^Counci\s?l?\s?l?\s?ors?\s*", "", clean(m.group(5))))
    for m in re.finditer(r"REZONING\s+ORDINANCE\s+NO\s?\.\s*(\d+)\s*,\s*(20\d\d)\s*\.?\s*(?=\d{4}\s*-\s*[A-Z]{2,4}\s*-)(.+?)(?=\s*REZONING\s+ORDINANCE\s+NO|\s*⟦p|\s*PROPOSAL NO|\s*The (?:President|Council)|$)", text):
        rezonings.setdefault((int(m.group(1)), int(m.group(2))), m.group(3).strip()[:600])
    # 3b. 2026-style rezoning lists: '2026-ZON-006 701 Shelby Street (Approximate Address) Prop No. 224, 2026
    #     Center Township, Council District #18 R.O. No. 64, 2026 Patrick Burtch, by ... Rezoning of ...'
    for m in re.finditer(r"(\d{4}\s*-\s*[A-Z]{2,4}\s*-\s*\d{3}\b.{0,160}?)\s*Prop\.?\s*No\.\s*(\d+)\s*,\s*(20\d\d)\s+(.+?)(?=\s\d{4}\s*-\s*[A-Z]{2,4}\s*-\s*\d{3}\b|\s*⟦p|\s*(?:PROPOSAL|REZONING ORDINANCE) NO|$)", text):
        rest = re.sub(r"R\.\s?O\.\s*No\.\s*\d+\s*,\s*\d{4}\s*", "", clean(m.group(4)))
        titles.setdefault((int(m.group(2)), int(m.group(3))), "Rezoning: " + clean(m.group(1)) + " " + rest[:480])
    # 4. The adopted text: 'Proposal No. 16, 2026 was retitled ... and reads as follows: CITY-COUNTY FISCAL
    #    ORDINANCE NO. 16, 2026 A FISCAL ORDINANCE amending ...' (also used for resolutions read in full)
    for m in re.finditer(r"Proposal No\.\s*(\d+)\s*,\s*(20\d\d)[^⟦]{0,160}?" + S("reads as follows") + r"\s*:\s*CITY\s*-\s*COUNTY[A-Z ,.\d-]{0,80}?(\bAN?\s+(?:[A-Z]+\s+){1,3}(?:ORDINANCE|RESOLUTION)S?\b.{10,420}?)(?:\s*[.;:](?:\s|$)|\s+WHEREAS|\s+BE IT)", text):
        t = clean(m.group(3))
        t = re.sub(r"^(AN?\s+(?:[A-Z]+\s+){0,3}(?:ORDINANCE|RESOLUTION)S?)", lambda x: x.group(1).capitalize(), t)
        titles.setdefault((int(m.group(1)), int(m.group(2))), t)
    # 5. Fallback: '... Proposal No. 124, 2026, which approves ...'
    for m in re.finditer(r"Proposal No\.\s*(\d+)\s*,\s*(20\d\d)\s*,?\s*which\s+([a-z].{15,400}?)(?<!\s[A-Z])(?<!\sSt)(?<!\sNo)(?<!\sInc)(?<!\sDr)(?<!\sMr)(?<!\sMs)(?<!\sJr)(?<!\sSr)(?<!\sCo)\s*\.[\"\u201d']?\s", text):
        add(m, 3)
    for m in re.finditer(r"Proposal No\.\s*(\d+),\s*(20\d\d),?\s*(?:as amended,\s*)?was retitled\s+((?:[A-Z]+\s){1,4})NO\.", text):
        types.setdefault((int(m.group(1)), int(m.group(2))), m.group(3).strip().title())

    votes = []
    for m in re.finditer(r"(?:the following|by the following) roll call vote;?\s*viz:?", text, re.I):
        before = text[max(0, m.start() - 700):m.start()]
        sentence = re.split(r"(?<=[a-z0-9)])\.\s(?=[A-Z])", before)[-1]
        refs = real([r for mm in PROP_REF.finditer(sentence) for r in expand(mm.group(1), mm.group(2))])
        if not refs:  # a motion: tie it to the last proposal mentioned before it
            prev = list(PROP_REF.finditer(before))
            refs = real(expand(prev[-1].group(1), prev[-1].group(2)))[-1:] if prev else []
        low = sentence.lower()
        if "motion to amend" in low or "was amended" in low or "were amended" in low: action = "Amendment"
        elif "motion" in low or "debate was ended" in low or "question was divided" in low or "agenda was amended" in low: action = "Procedural motion"
        elif "elected" in low: action = "Election"
        elif "returned to committee" in low: action = "Return to committee"
        elif "stricken" in low: action = "Strike"
        else: action = "Final passage"
        if re.search(r"\b(failed|defeated|lost)\b", low): outcome = "Failed"
        elif re.search(r"\b(adopted|carried|amended|passed|returned|stricken|elected|ended|divided)\b", low): outcome = "Passed"
        else: outcome = "Unknown"

        pos, counts, cast = m.end(), {}, {}
        while True:
            g = re.match(r"\s*(?:⟦p\d+⟧\s*)?(\d+)\s?(YEAS?|NAYS?|ABSENT|EXCUSED|NOT VOTING|ABSTAIN(?:ED|ING)?)\s*:?", text[pos:])
            if not g: break
            label = LABELS[g.group(2)]
            counts[label] = counts.get(label, 0) + int(g.group(1))
            pos += g.end()
            names, used = read_names(text[pos:pos + 600])
            pos += used
            for n in names: cast[n] = label
        if not counts:
            continue
        mismatch = {k: (v, sum(1 for x in cast.values() if x == k)) for k, v in counts.items() if v != sum(1 for x in cast.values() if x == k)}
        votes.append({"date": date, "source": "minutes", "page": page_at(text, m.start()), "proposals": refs,
                      "action": action, "outcome": outcome, "counts": counts, "votes": cast,
                      "context": re.sub(r"⟦p\d+⟧\s*", "", sentence.strip())[-300:], "mismatch": mismatch or None})
    return votes


def complete_from_totals(cast, counts, members):
    """If exactly one serving member is missing and exactly one group is one short of its printed total,
    that member's vote is the missing one. Returns the names filled in this way."""
    if not members: return []
    missing = [m for m in members if m not in cast]
    short = [k for k, v in counts.items() if v - sum(1 for x in cast.values() if x == k) == 1]
    over = [k for k, v in counts.items() if v - sum(1 for x in cast.values() if x == k) < 0]
    if len(missing) == 1 and len(short) == 1 and not over:
        cast[missing[0]] = short[0]
        return missing
    return []


def sheet_action(act):
    low = act.lower()
    if low.startswith(("adopt", "deny")): return "Final passage"  # "Deny" is the final vote on a rezoning denial
    if "amend" in low: return "Amendment"
    if "postpone" in low or "table" in low: return "Postpone or table"
    if "withdraw" in low: return "Withdraw"
    if "cmte" in low or "committee" in low: return "Return to committee"
    return "Procedural motion"


def parse_roll_call_sheets(date, members=None):
    """OCR'd sheets: one vote per page. `members` is who served at that meeting (for completing a misread name)."""
    raw = open(os.path.join(HERE, "roll-calls", f"{date}.txt")).read()
    out = []
    for page_no, page in re.findall(r"^=== \S+ roll call, page (\d+) of \d+ ===\n(.*?)(?=^=== |\Z)", raw, flags=re.M | re.S):
        pm = re.search(r"Proposal:\s*PROP\s?-?\s?(\d\d)\s?-?\s+(\d+)|Proposal:\s*PROP(\d\d)-\s?(\d+)", page)
        if not pm: continue  # attendance and other non-proposal sheets
        year, no = 2000 + int(pm.group(1) or pm.group(3)), int(pm.group(2) or pm.group(4))
        om = re.search(r"Ordinance:\s*([A-Z]\.\s?[A-Z]\.)\s*(\d+)?", page)
        code = om.group(1).replace(" ", "") if om else None
        ord_no = int(om.group(2)) if om and om.group(2) and om.group(2) != "0" else None
        consent = "BY CONSENT" in page.upper() or "UNANIMOUS CONSENT" in page.upper()
        group = re.search(r"PART OF\s+GROUP RCS\s*#\s*(\d+)", page.upper().replace("\n", " "))
        act = (re.search(r"Action:\s*([^\n]+)", page) or [None, ""])[1].strip()
        res = re.search(r"\((PASSED|FAILED|ADOPTED|CARRIED|DEFEATED)\)", page)
        cast, counts, label = {}, {}, None
        for line in page.splitlines():
            h = re.match(r"\s*(Yea|Nay|Abstain|Not Voting|Excused)\s*-\s*(\d+)", line)
            if h:
                label = {"Yea": "Yes", "Nay": "No", "Abstain": "Abstain", "Not Voting": "Not voting", "Excused": "Absent"}[h.group(1)]
                counts[label] = counts.get(label, 0) + int(h.group(2)); continue
            if label:
                for tok in line.split():
                    n = ocr_name(tok)
                    if n: cast[n] = label
        action = sheet_action(act)
        outcome = "Failed" if res and res.group(1) in ("FAILED", "DEFEATED") else "Passed" if res else "Unknown"
        # The summary line is the authoritative total; group headings can repeat ("Excused - 1 ... Excused - 0")
        tl = re.search(r"Yea:\s*(\d+)\s+Nay:\s*(\d+)\s+Ab\w*:\s*(\d+)\s+Not Voting:\s*(\d+)\s+Excused:\s*(\d+)", page)
        if tl:
            counts = {k: int(x) for k, x in zip(["Yes", "No", "Abstain", "Not voting", "Absent"], tl.groups())}
        inferred = complete_from_totals(cast, counts, members)
        mismatch = {k: (v, sum(1 for x in cast.values() if x == k)) for k, v in counts.items() if v != sum(1 for x in cast.values() if x == k)}
        out.append({"date": date, "source": "roll-call sheet (OCR)", "inferred": inferred or None, "page": int(page_no), "proposals": [(no, year)],
                    "action": action, "outcome": outcome, "counts": counts, "votes": cast,
                    "context": f"Action: {act}", "code": code, "ordinanceNo": ord_no, "consent": consent,
                    "group": int(group.group(1)) if group else None, "mismatch": mismatch or None})
    return out


TYPE_CODES = {"R.O.": "Rezoning Ordinance", "G.O.": "General Ordinance", "F.O.": "Fiscal Ordinance",
              "S.O.": "Special Ordinance", "C.R.": "Council Resolution", "G.R.": "General Resolution",
              "S.R.": "Special Resolution"}


def members_by_meeting(minutes_votes):
    by, n = defaultdict(Counter), Counter()
    for v in minutes_votes:
        n[v["date"]] += 1
        for k in v["votes"]: by[v["date"]][k] += 1
    return {d: [k for k, c in by[d].items() if c >= 0.5 * n[d]] for d in by}


def main():
    titles, types, sponsors, rezonings = {}, {}, {}, {}
    minutes_votes = []
    for mt in SOURCES:
        if mt["minutes"]:
            minutes_votes += parse_minutes(mt["date"], titles, types, sponsors, rezonings)
    # Agendas fill in titles for proposals the posted minutes don't reach yet (their "DIGEST" line)
    for f in sorted(glob.glob(os.path.join(HERE, "agendas", "*.txt"))):
        t = re.sub(r"\s+", " ", re.sub(r"^=== .* ===$", " ", open(f).read(), flags=re.M))
        for m in re.finditer(r"PROPOSAL NO\.\s*(\d+),\s*(20\d\d)\s*\(([^)]+)\)\s*INTRODUCED:.{0,40}?BY:\s*(Councill?ors?\s*.+?)\s*REFERRED TO:.*?DIGEST:\s*(.+?)\s*(?=COMMITTEE ACTION:|PROPOSAL NOS?\.|\d+\s+[IVX]+\.\s|$)", t):
            key, digest = (int(m.group(1)), int(m.group(2))), m.group(5).strip()
            titles.setdefault(key, digest[0].upper() + digest[1:])
            types.setdefault(key, m.group(3).strip().title())
            sponsors.setdefault(key, re.sub(r"^Councill?ors?\s*", "", m.group(4)).strip())
        for m in re.finditer(r"PROPOSAL NOS\.\s*(\d+)\s*-\s*(\d+)\s*,\s*(20\d\d)\s*\(Rezoning Ordinances\).*?DIGEST:\s*(.+?)\s*(?=COMMITTEE ACTION:|PROPOSAL NOS?\.|\d+\s+[IVX]+\.\s|$)", t):
            for n in range(int(m.group(1)), int(m.group(2)) + 1):
                key = (n, int(m.group(3)))
                digest = re.sub(r"^rezoning ordinances", "Rezoning ordinance", m.group(4).rstrip(".")).replace("APPROVAL", "approval")
                titles.setdefault(key, digest + " (one of a batch; the address will be in the minutes once they're posted)")
                types.setdefault(key, "Rezoning Ordinance")
    members = members_by_meeting(minutes_votes)
    # Meetings with no minutes yet: who served comes from their own sheets (e.g. Masquelier from Sept 2026)
    sheet_votes = []
    for mt in SOURCES:
        if mt["rollCall"] and mt["rollCall"].get("url"):
            sheet_votes += parse_roll_call_sheets(mt["date"], members.get(mt["date"]))

    urls = {mt["date"]: {"minutes": (mt["minutes"] or {}).get("url"), "rollCall": (mt["rollCall"] or {}).get("url")} for mt in SOURCES}
    sheet_dates = {v["date"] for v in sheet_votes}
    by_key = defaultdict(list)  # (date, proposal) -> minutes votes that cover it
    for v in minutes_votes:
        for pr in v["proposals"]: by_key[(v["date"], pr)].append(v)

    records, agree, compared = [], 0, 0
    for v in sheet_votes:
        pr = v["proposals"][0]
        rec = dict(v, proposals=[pr], status="ok")
        matches = [m for m in by_key.get((v["date"], pr), []) if m["action"] == v["action"] or (m["action"] == "Final passage" and v["action"] == "Final passage")]
        if matches and not matches[-1]["mismatch"] and not v["mismatch"]:
            compared += 1
            if matches[-1]["votes"] == v["votes"]: agree += 1
            else: rec["status"] = "sources differ"
        if v["mismatch"]:
            if matches and not matches[-1]["mismatch"]:
                rec.update(votes=matches[-1]["votes"], counts=matches[-1]["counts"], source="minutes (sheet unreadable)", status="ok")
            else:
                rec["status"] = "needs review"
        records.append(rec)
    for v in minutes_votes:
        if v["date"] in sheet_dates: continue  # those meetings are covered per proposal by the sheets
        for pr in v["proposals"] or [None]:
            records.append(dict(v, proposals=[pr] if pr else [], status="needs review" if v["mismatch"] or not pr else "ok"))
    for r in records:
        # Some minutes keep listing Jackson after Allen took her seat (June 2024); the roll-call sheets for the
        # same period show Allen, so the minutes' name list was stale.
        if r["date"] >= "2024-06-03" and "Jackson" in r["votes"] and "Allen" not in r["votes"]:
            r["votes"] = {("Allen" if k == "Jackson" else k): x for k, x in r["votes"].items()}
            r["note"] = "Minutes list Jackson, who had left the Council; recorded as Allen, as on the roll-call sheets from this period."

    props = {}
    for r in records:
        r["urls"] = urls.get(r["date"])
        for no, yr in r["proposals"]:
            k = f"{no}-{yr}"
            pr = props.setdefault(k, {"no": no, "year": yr, "title": titles.get((no, yr)),
                                      "type": types.get((no, yr)), "sponsors": sponsors.get((no, yr))})
            if not pr["type"] and r.get("code") in TYPE_CODES: pr["type"] = TYPE_CODES[r["code"]]
            if r.get("code") == "R.O." and r.get("ordinanceNo"):
                desc = rezonings.get((r["ordinanceNo"], yr))
                if desc:
                    pr["rezoning"] = desc
                    if not pr["title"]: pr["title"] = "Rezoning: " + desc
        r["proposals"] = [f"{no}-{yr}" for no, yr in r["proposals"]]
    # City proposal database (indy.gov/workflow/city-county-council-proposals, saved per year by
    # tools/fetch_city_proposals.py): fills titles the records lack, adds committee/initiator/full-text
    # links, and gives an independent check of each final-passage tally ("Adopted 17-8").
    city = {}
    for f in glob.glob(os.path.join(HERE, "city-proposals", "*.json")):
        yr = int(os.path.basename(f)[:4])
        for c in json.load(open(f))["data"]:
            city[f"{c['proposal_number']}-{yr}"] = c
    tally_checked = tally_agree = 0
    for k, pr in props.items():
        c = city.get(k)
        if not c: continue
        digest = re.sub(r"\s*\.\.\.$", "", (c.get("digest") or "").strip())
        if not pr["title"] and digest:
            pr["title"] = digest[0].upper() + digest[1:] + ("..." if (c.get("digest") or "").rstrip().endswith("...") else "")
            pr["titleSource"] = "city proposal database (shortened summary)"
        if not pr["type"] and c.get("proposal_type"): pr["type"] = c["proposal_type"]
        if not pr["sponsors"] and c.get("sponsors"):
            pr["sponsors"] = ", ".join(re.sub(r"^Councill?or\s+", "", x.strip()) for x in c["sponsors"].splitlines() if x.strip())
        pr["committee"] = c.get("committee_name") or None
        pr["initiator"] = c.get("initiator") or None
        pr["introduced"] = c.get("introduced") or None
        doc = next((d for d in c.get("document_list") or [] if d.get("has_content")), None)
        pr["documentUrl"] = "https://www.indy.gov" + doc["content_link"] if doc else None
        pr["cityActions"] = [f"{a['action_date']}: {a['action_description'].strip()}" for a in c.get("action_list") or []]
    for r in records:
        if r["action"] != "Final passage" or len(r["proposals"]) != 1: continue
        c = city.get(r["proposals"][0])
        if not c: continue
        for a in c.get("action_list") or []:
            m = re.match(r"(?i)\s*(?:ad\w*ted|denial upheld|ratified),?\s*(\d+)\s*-\s*(\d+)", a["action_description"])
            if m and a["action_date"] == r["date"]:
                tally_checked += 1
                yes = sum(1 for x in r["votes"].values() if x == "Yes"); no = sum(1 for x in r["votes"].values() if x == "No")
                if (yes, no) == (int(m.group(1)), int(m.group(2))): tally_agree += 1
                else:
                    r["cityTally"] = f"{m.group(1)}-{m.group(2)}"
                    r["status"] = "needs review"
                    r["note"] = ((r.get("note") or "") + f" The city's proposal database records this as \"{a['action_description'].strip()}\", "
                                 f"which doesn't match the names on the record ({yes}-{no}), so the individual votes shown may be wrong.").strip()
    records.sort(key=lambda r: (r["date"], r["page"]))
    json.dump({"votes": records, "proposals": props, "crossCheck": {"compared": compared, "agree": agree},
               "tallyCheck": {"compared": tally_checked, "agree": tally_agree}},
              open(os.path.join(HERE, "votes.json"), "w"), indent=1)

    print(len(records), "votes;", len(props), "proposals;", sum(1 for p in props.values() if p["title"]), "with titles;",
          sum(1 for p in props.values() if p["type"]), "with a type")
    print("status:", dict(Counter(r["status"] for r in records)))
    print("sources:", dict(Counter(r["source"] for r in records)))
    print("actions:", dict(Counter(r["action"] for r in records)))
    print(f"cross-check: {agree} of {compared} votes identical in minutes and roll-call sheets")
    print(f"tally check vs city database: {tally_agree} of {tally_checked} final-passage yes-no counts match")


if __name__ == "__main__":
    main()
