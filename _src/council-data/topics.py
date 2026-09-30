"""Topic tags for council proposals, assigned by keyword matching on the proposal's title and ordinance
type. Predictable and easy to audit rather than clever: a proposal can have several topics, and anything
that matches none is "Other". To fix a wrong tag, add the proposal to topic-overrides.json
({"123-2024": ["Housing & homelessness"]}) instead of loosening a pattern here.
"""
import json, os, re

TOPICS = [
    ("Rezoning & land use", r"\brezon|\bzoning\b|variance|land use|metropolitan development commission|\bplat\b|vacat(?:e|ion|ing)|annex"),
    ("TIF & economic development", r"tax increment|\bTIF\b|allocation area|economic development|abatement|economic revitalization|redevelopment|revitalization enhancement|tax credit|incentive|payment in lieu of taxes|\bPILOT\b"),
    ("Infrastructure & transportation", r"(?-i:\bstreets?\b|\broads?\b)|roadway|traffic|speed limit|stop sign|signal|crosswalk|parking|sidewalk|bridge|sewer|storm ?water|drainage|\btrails?\b|transit|indygo|bicycle|\bbike|public works|wheel tax|infrastructure|pavement|resurfac|pothole|intersection"),
    ("Budget & spending", r"appropriat|\bbudget\b|\btransfer\b|fiscal|\bbonds?\b|\bfunds?\b|expenditure|\blease\b"),
    ("Taxes & fees", r"tax rate|\blevy\b|income tax|property tax|\bfees?\b|excise|wheel tax|food and beverage|\btaxes\b|\btax\b(?! increment)"),
    ("Public safety & justice", r"police|\bIMPD\b|\bfire\b|firefight|\bIFD\b|sheriff|\bjail\b|criminal|court|prosecutor|public defender|\bcrime|violence|firearm|\bguns?\b|public safety|\b911\b|emergency|corrections|juvenile|detention"),
    ("Housing & homelessness", r"housing|tenant|landlord|rental|homeless|eviction|affordable|shelter|dwelling"),
    ("Parks & environment", r"\bparks?\b|\btrees?\b|climate|environment|sustainab|recycl|solar|greenway|conservation|pollution|energy"),
    ("Health & human services", r"health|hospital|opioid|mental|substance|human services|food|hunger|child care|senior"),
    ("Appointments", r"\bappoint|reappoint|\bconfirm"),
    ("Council & government operations", r"council (?:rules|meetings?|president|district boundaries)|rules of the council|ethics|\belection|salar|compensation|\bpay\b|pension|clerk|redistrict|\baudit|procurement|schedule of regular"),
    ("Recognitions & honors", r"recogni[sz]|\bhonou?r|celebrat|commend|in memory|the life|congratulat|proclaim|awareness|month\b|\bweek\b|\bday\b"),
]
COMPILED = [(name, re.compile(rx, re.I)) for name, rx in TOPICS]
NAMES = [name for name, _ in TOPICS] + ["Other"]

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    OVERRIDES = json.load(open(os.path.join(HERE, "topic-overrides.json")))
except FileNotFoundError:
    OVERRIDES = {}


def topics_for(key, title, ptype):
    if key in OVERRIDES: return OVERRIDES[key]
    text = title or ""
    found = []
    if ptype == "Rezoning Ordinance" or text.startswith("Rezoning:"):
        return ["Rezoning & land use"]  # addresses ("... Road") would otherwise trip other topics
    if ptype == "Fiscal Ordinance": found.append("Budget & spending")
    for name, rx in COMPILED:
        if name == "Recognitions & honors" and ptype not in ("Special Resolution", None): continue
        if rx.search(text) and name not in found: found.append(name)
    # appointments and honors are narrow; don't let incidental words add broad topics to them
    if "Appointments" in found: found = [t for t in found if t in ("Appointments", "Public safety & justice", "Health & human services", "Housing & homelessness", "Parks & environment", "TIF & economic development", "Infrastructure & transportation")]
    if "Recognitions & honors" in found: found = ["Recognitions & honors"]
    return found or ["Other"]
