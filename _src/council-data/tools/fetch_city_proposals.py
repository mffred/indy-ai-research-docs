"""Save the city's proposal database, one JSON file per year, to _src/council-data/city-proposals/.
This is the public feed behind indy.gov's "Council Proposal Search"; one request returns a whole year.
Run: python3 _src/council-data/tools/fetch_city_proposals.py [years...]   (default 2020-2026)"""
import os, sys, time, urllib.parse, urllib.request

WORKFLOW = "89e1109f-eb67-4e0c-9cb9-40a51bb85c9d"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "city-proposals")
years = [int(y) for y in sys.argv[1:]] or list(range(2020, 2027))
os.makedirs(OUT, exist_ok=True)
for y in years:
    q = urllib.parse.urlencode({"__workflow_id": WORKFLOW, "year": y, "proposal_number": "", "ordinance_number": "",
                                "proposal_type": "", "councillor": "", "committee": "", "initiator": "", "keywords": ""})
    with urllib.request.urlopen("https://www.indy.gov/api/v1/indy_find_proposals?" + q, timeout=90) as r:
        open(os.path.join(OUT, f"{y}.json"), "wb").write(r.read())
    print("saved", y)
    time.sleep(1)
