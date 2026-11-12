from datetime import date

import yaml
from openpyxl import load_workbook

from jobscraper.excel import write_workbook
from jobscraper.mailer import build_email
from jobscraper.models import Job
from jobscraper.sources import startups as st

TODAY = date(2026, 11, 12)
CFG = yaml.safe_load(open("config.yaml"))
LONG = " Lorem ipsum." * 30


def fit(title, desc=LONG):
    return st.graduate_fit(title, desc, 2)


def test_graduate_fit():
    assert fit("Graduate Quant Analyst")[0] == "Graduate / junior role"
    assert fit("Software Engineer, New Grad")[0] == "Graduate / junior role"
    assert fit("Junior Trader")[0] == "Graduate / junior role"
    assert fit("Software Engineer I")[0] == "Graduate / junior role"
    assert fit("Quant Researcher", "We welcome new grads with strong maths." + LONG)[0] == "Welcomes graduates"
    assert fit("Data Analyst", "0-2 years of experience with SQL." + LONG)[0] == "Welcomes graduates"
    assert fit("Risk Analyst")[0] == "No experience asked"
    assert fit("Risk Analyst", "short")[0].startswith("No experience asked (check")
    assert fit("Quant Researcher", "You have 5+ years of experience in systematic trading." + LONG) is None
    assert fit("Data Scientist", "Proven experience building credit models is required." + LONG) is None
    assert fit("Junior Quant", "3+ years of experience in Python." + LONG) is None


def test_role_area():
    areas, excl = CFG["startups"]["role_areas"], CFG["startups"]["exclude_title_words"]
    assert st.role_area("Quantitative Researcher", areas, excl) == "Quant & Research"
    assert st.role_area("Algorithmic Trader", areas, excl) == "Trading"
    assert st.role_area("Credit Risk Analyst", areas, excl) == "Risk"
    assert st.role_area("Software Engineer", areas, excl) == "Engineering"
    assert st.role_area("Sales Engineer", areas, excl) == ""
    assert st.role_area("Enterprise Account Executive", areas, excl) == ""
    assert st.role_area("Product Designer", areas, excl) == ""


def job(title, desc=LONG, loc="London, UK", posted=TODAY):
    return Job(source="x", title=title, company="x", location=loc, url=f"https://x/{title}", posted=posted,
               description=desc)


def test_collect_keeps_graduate_roles_only():
    listed = [
        {"name": "Wintermute", "focus": "Market making", "stage": "Private", "hq": "London",
         "board": {"platform": "lever", "id": "wintermute-trading"}},
        {"name": "Primer", "board": "none"},
    ]
    boards_read = []

    def fake_fetch(site):
        boards_read.append(site["id"])
        return [
            job("Graduate Algorithmic Trader"),
            job("Senior Quant Researcher"),
            job("Quant Researcher", "Minimum 4 years of experience in research." + LONG),
            job("Trading Intern"),
            job("Recruiter"),
            job("Junior Data Engineer", loc="Bengaluru, India"),
            job("Junior Risk Analyst", "We are unable to sponsor visas for this role." + LONG),
            job("Data Scientist", "Ideal for recent graduates in maths or physics." + LONG),
        ]

    stats, store = {}, {}
    opps = st.collect(CFG, stats, store, listed, today=TODAY, fetch=fake_fetch)
    assert boards_read == ["wintermute-trading"]  # Primer has board: none, so no lookup either
    assert [o.title for o in opps] == ["Graduate Algorithmic Trader", "Data Scientist"]
    assert opps[0].area == "Trading" and opps[0].company == "Wintermute" and opps[0].focus == "Market making"
    assert stats["dropped"] == {"too senior": 1, "asks for experience": 1, "internship": 1,
                                "not a quant, finance, data or engineering role": 1, "excluded country": 1,
                                "no sponsorship": 1}
    new = st.mark_first_seen(opps, store.setdefault("first_seen", {}), "2026-11-12T08:00:00")
    assert new == {o.key for o in opps}
    assert st.mark_first_seen(opps, store["first_seen"], "2026-11-13T08:00:00") == set()


def test_board_lookup_is_remembered(monkeypatch):
    calls = []

    def probe(s, name):
        calls.append(name)
        return {"platform": "ashby", "id": "kaiko"} if name == "Kaiko" else None

    import jobscraper.discover_careers as dc
    monkeypatch.setattr(dc, "probe_apis", probe)
    monkeypatch.setattr(st, "known_sites", lambda: {})
    store = {}
    listed = [{"name": "Kaiko"}, {"name": "Nowhere Ltd"}]
    st.collect(CFG, {}, store, listed, today=TODAY, fetch=lambda site: [])
    assert calls == ["Kaiko", "Nowhere Ltd"]
    assert store["boards"]["Kaiko"]["id"] == "kaiko"
    st.collect(CFG, {}, store, listed, today=TODAY, fetch=lambda site: [])
    assert calls == ["Kaiko", "Nowhere Ltd"]  # neither looked up again within the retry window


def test_failed_board_is_looked_up_again(monkeypatch):
    monkeypatch.setattr(st, "known_sites", lambda: {})
    store = {"boards": {"Kaiko": {"checked": "2026-11-01", "platform": "ashby", "id": "kaiko"}}}

    def broken(site):
        raise RuntimeError("404")

    stats = {}
    st.collect(CFG, stats, store, [{"name": "Kaiko"}], today=TODAY, fetch=broken)
    assert "Kaiko" not in store["boards"] and stats["errors"] == 1


def test_sheet_and_email(tmp_path):
    opp = st.Opportunity(title="Graduate Trader", company="Wintermute", location="London, UK",
                         url="https://jobs.lever.co/wintermute-trading/1", focus="Market making", area="Trading",
                         graduate_fit="Graduate / junior role", graduate_evidence="Graduate", posted=TODAY,
                         platform="Lever")
    path = write_workbook([], set(), {}, tmp_path / "x.xlsx", startups=[opp], new_startups={opp.key})
    ws = load_workbook(path)["Startups"]
    assert ws["A2"].value == "NEW" and ws["B2"].value == "Graduate Trader"
    assert ws.cell(row=2, column=18).hyperlink.target == opp.url
    msg = build_email([], set(), {}, path, "a@b.c", "a@b.c", startups=[opp], new_startups={opp.key})
    body = msg.get_body(("plain",)).get_content()
    assert "1 roles at quant and fintech startups" in body and "NEW Graduate Trader | Wintermute" in body
    assert "Startups" not in load_workbook(write_workbook([], set(), {}, tmp_path / "y.xlsx")).sheetnames


def test_not_found_forgotten_when_network_down(monkeypatch):
    import jobscraper.discover_careers as dc
    monkeypatch.setattr(dc, "probe_apis", lambda s, name: None)
    monkeypatch.setattr(st, "known_sites", lambda: {})

    def broken(site):
        raise RuntimeError("offline")

    store = {}
    listed = [{"name": "Ramp", "board": {"platform": "ashby", "id": "ramp"}}, {"name": "Hebbia"}]
    st.collect(CFG, {}, store, listed, today=TODAY, fetch=broken)
    assert "Hebbia" not in store["boards"]  # looked up again next run
