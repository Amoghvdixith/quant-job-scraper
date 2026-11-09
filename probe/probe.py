import logging, yaml, sys
sys.path.insert(0, ".")
logging.basicConfig(level=logging.INFO)
from jobscraper import filters, main
from jobscraper.sources import government
from jobscraper.sponsor_registers import SponsorRegisters
cfg = yaml.safe_load(open("config.yaml"))
roles = yaml.safe_load(open("roles.yaml"))["roles"] if isinstance(yaml.safe_load(open("roles.yaml")), dict) else yaml.safe_load(open("roles.yaml"))
st = {"errors": 0}
raw = []
for kw in cfg["government"]["nhs_keywords"]:
    got = government.nhs_search(kw, cfg, st); print("NHS", kw, len(got)); raw += got
for d in cfg["government"]["civil_service_departments"][:4]:
    got = government.civil_service_search(d, cfg, st); print("CS", d, len(got), [j.company for j in got][:5]); raw += got
m = filters.RoleMatcher(roles)
kept = main.apply_filters(raw, cfg, m)
print("raw", len(raw), "kept", len(kept), st)
jobs = list(kept.values())[:25]
main.enrich_all(jobs, 5)
reg = SponsorRegisters()
from collections import Counter
c = Counter()
for j in jobs:
    j.first_seen = "2026-11-09T00:00:00"
    j.employer_sponsor = reg.status(j.company, j.location)
    r = main.rule_broken(j, cfg, m, reg); c[r] += 1
    print(f"{r or 'KEEP'} | {j.title} | {j.company} | {j.posted} | len={len(j.description)} | spons={j.sponsorship} | emp={j.employer_sponsor} | exp={j.experience} | q={j.qualification}")
print(c)
