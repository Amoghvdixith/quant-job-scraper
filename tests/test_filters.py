from datetime import date, timedelta
from pathlib import Path

import yaml
from openpyxl import load_workbook

from jobscraper import filters
from jobscraper.excel import write_workbook
from jobscraper.mailer import build_email
from jobscraper.models import Job
from jobscraper.sources import efinancialcareers, linkedin

ROOT = Path(__file__).resolve().parent.parent
ROLES = yaml.safe_load((ROOT / "roles.yaml").read_text())["roles"]
CFG = yaml.safe_load((ROOT / "config.yaml").read_text())
matcher = filters.RoleMatcher(ROLES)


def role_of(title):
    m = matcher.match(title)
    return m[0]["id"] if m else None


def test_role_matching():
    assert role_of("Graduate Market Risk Analyst") == "T1-1"
    assert role_of("Market Risk Analyst - Rates") == "T1-1"
    assert role_of("Quantitative Analyst, Graduate") == "T2-1"
    assert role_of("Quant Risk Analyst") in {"T2-3", "T2-1"}
    assert role_of("Model Validation Associate") == "T1-6"
    assert role_of("Graduate Product Controller") == "T1-10"
    assert role_of("P&L Analyst") == "T1-12"
    assert role_of("Operational Risk Analyst") == "T2-13"  # broad "Risk Analyst" keyword
    assert role_of("Software Engineer") is None
    assert role_of("Marketing Analyst") is None


def test_seniority():
    words = CFG["senior_title_words"]
    assert filters.is_senior("Senior Market Risk Analyst", words)
    assert filters.is_senior("Sr. Quant Analyst", words)
    assert filters.is_senior("VP, Model Validation", words)
    assert not filters.is_senior("Graduate Market Risk Analyst", words)
    assert not filters.is_senior("Leadership Programme Analyst", words)


def test_location_exclusions():
    ex = CFG["excluded_locations"]
    assert filters.is_excluded_location("Bengaluru, Karnataka, India", ex)
    assert filters.is_excluded_location("Dubai, United Arab Emirates", ex)
    assert filters.is_excluded_location("Abu Dhabi, UAE", ex)
    assert not filters.is_excluded_location("London, England, United Kingdom", ex)
    assert not filters.is_excluded_location("Indianapolis, IN", ex)
    assert not filters.is_excluded_location("Remote", ex)
    assert filters.is_excluded_location("Riyadh, Saudi Arabia", ex)
    assert filters.is_excluded_location("Doha, Qatar", ex)
    assert filters.is_excluded_location("Tel Aviv-Yafo, Israel", ex)
    assert filters.is_excluded_location("Amman, Jordan", ex)
    assert not filters.is_excluded_location("Lebanon, PA", ex)
    assert not filters.is_excluded_location("Jordan, MN", ex)


def test_years_required():
    assert filters.years_required("You have 5+ years of experience in risk") == 5
    assert filters.years_required("1-2 years relevant experience") == 1
    assert filters.years_required("graduates welcome") is None


def test_sponsorship():
    assert filters.sponsorship("Visa sponsorship is available for this role.")[0] == "Yes"
    assert filters.sponsorship("We are able to sponsor Skilled Worker visas.")[0] == "Yes"
    assert filters.sponsorship("Unfortunately we are unable to offer visa sponsorship.")[0] == "No"
    assert filters.sponsorship("We do not sponsor.")[0] == "No"
    assert filters.sponsorship("You must have the right to work in the UK.")[0] == "No"
    assert filters.sponsorship("Sponsorship is not available.")[0] == "No"
    assert filters.sponsorship("Great team, hybrid working.")[0] == "Not stated"


LINKEDIN_HTML = """
<li><div class="base-card base-search-card job-search-card" data-entity-urn="urn:li:jobPosting:4012345678">
<a class="base-card__full-link" href="https://uk.linkedin.com/jobs/view/graduate-market-risk-analyst-at-barclays-4012345678?refId=x"></a>
<h3 class="base-search-card__title"> Graduate Market Risk Analyst </h3>
<h4 class="base-search-card__subtitle"><a>Barclays</a></h4>
<span class="job-search-card__location">London, England, United Kingdom</span>
<time class="job-search-card__listdate" datetime="2026-10-27">1 day ago</time>
</div></li>"""


def test_linkedin_card_parsing():
    from bs4 import BeautifulSoup
    card = BeautifulSoup(LINKEDIN_HTML, "html.parser").select("div.base-search-card, div.job-search-card")
    assert len(card) == 1
    job = linkedin._parse_card(card[0], "Market Risk Analyst")
    assert job.title == "Graduate Market Risk Analyst"
    assert job.company == "Barclays"
    assert job.url == "https://www.linkedin.com/jobs/view/4012345678"
    assert job.posted == date(2026, 10, 27)


def test_linkedin_keywords():
    assert linkedin.build_keywords(["A B", "C"]) == '"A B" OR "C"'


def test_efc_parsing():
    data = {"data": [{"id": "24710250", "title": "Model Validation Analyst", "clientBrandName": "HSBC",
                      "jobLocation": {"displayName": "London, United Kingdom"},
                      "postedDate": "2026-10-26T09:00:00Z", "detailsPageUrl": "/jobs-UK-London-Model_Validation.id24710250",
                      "summary": "<p>We offer visa sponsorship</p>"}]}
    raws = efinancialcareers._find_job_dicts(data)
    job = efinancialcareers._to_job(raws[0], ROLES[5])
    assert job.company == "HSBC"
    assert job.location == "London, United Kingdom"
    assert job.posted == date(2026, 10, 26)
    assert job.url.startswith("https://www.efinancialcareers.com/jobs-UK")
    assert "visa sponsorship" in job.description


def test_excel_and_email(tmp_path):
    jobs = [Job("LinkedIn", "Market Risk Analyst", "Barclays", "London", "https://x/1",
                posted=date.today() - timedelta(days=1), role_title="Market Risk Analyst", tier=1,
                category="Market Risk", sponsorship="Yes", sources=["LinkedIn"])]
    stats = {"LinkedIn": {"found": 1, "errors": 0}}
    path = write_workbook(jobs, {jobs[0].key}, stats, tmp_path / "t.xlsx")
    ws = load_workbook(path)["Jobs"]
    assert ws["A2"].value == "NEW" and ws["E2"].value == "Market Risk Analyst"
    assert ws["Q2"].hyperlink.target == "https://x/1"
    msg = build_email(jobs, {jobs[0].key}, stats, path, "a@gmail.com", "b@gmail.com")
    assert msg["To"] == "b@gmail.com"
    assert "1 new" in msg["Subject"]


def test_target_firms():
    from jobscraper import institutions
    assert institutions.match("Barclays") == "Barclays"
    assert institutions.match("Goldman Sachs Asset Management") == "Goldman Sachs"
    assert institutions.match("Two Sigma Investments, LP") == "Two Sigma"
    assert institutions.match("Jane Street Capital") == "Jane Street"
    assert institutions.match("Acme Widgets Ltd") == ""


def test_rotation():
    from jobscraper.main import rotate
    items = list(range(10))
    seen = set()
    for slot in range(4):
        seen |= set(rotate(items, 3, slot))
    assert seen == set(items)
    assert rotate(items, 20, 5) == items


def test_one_word_keywords_need_the_phrase():
    assert role_of("Associate, Fundraise Management, Liquid Credit Strategies") is None
    assert role_of("Trading Systems Engineer - Global Options") is None
    assert role_of("Credit Analyst - Leveraged Finance") == "T1-15"
    assert role_of("Graduate Treasury Analyst") == "T2-9"


def test_rules_rechecked_on_saved_jobs():
    from jobscraper.main import rule_broken
    regs = fake_registers()
    ok = Job("LinkedIn", "Graduate Market Risk Analyst", "Barclays", "London, UK", "u",
             posted=date.today(), first_seen=date.today().isoformat())
    ok.employer_sponsor = regs.status(ok.company, ok.location)
    assert rule_broken(ok, CFG, matcher, regs) is None
    for change, reason in [
        (dict(title="Senior Market Risk Analyst"), "too senior"),
        (dict(title="Market Risk Analyst II"), "too senior"),
        (dict(location="Mumbai, India"), "excluded country"),
        (dict(years_required=5), "asks for 5+ years"),
        (dict(sponsorship="No"), "no sponsorship"),
        (dict(qualification="CFA"), "asks for a professional qualification"),
        (dict(experience="proven experience"), "asks for work experience"),
        (dict(years_required=1), "asks for 1+ years"),
        (dict(posted=date.today() - timedelta(days=9)), "older than the age limit"),
        (dict(title="Software Engineer"), "title doesn't match a target role"),
    ]:
        job = Job(**{**ok.__dict__, **change})
        assert rule_broken(job, CFG, matcher, regs) == reason, change


def test_recruiters_and_duplicates():
    assert filters.is_recruiter("Oxford Knight")
    assert not filters.is_recruiter("Goldman Sachs")
    a = Job("LinkedIn", "Market Risk Analyst", "JPMorgan Chase", "", "u")
    b = Job("Careers", "Market Risk Analyst", "JPMorganChase", "", "v")
    assert a.key == b.key


def fake_registers():
    from jobscraper.sponsor_registers import SponsorRegisters, clean
    regs = SponsorRegisters.__new__(SponsorRegisters)
    regs.lists = {"UK": {clean("Barclays Bank PLC")}, "US": {clean("JPMORGAN CHASE BANK, N.A."), clean("Goldman Sachs & Co. LLC")}, "NL": set()}
    regs.loaded = {"UK": True, "US": True, "NL": False}
    return regs


def test_sponsorship_filter():
    from jobscraper.main import sponsorship_rule
    regs = fake_registers()

    def check(company, location, sponsorship="Not stated", mode="posting_or_employer"):
        job = Job("LinkedIn", "Market Risk Analyst", company, location, "u", sponsorship=sponsorship)
        job.employer_sponsor = regs.status(company, location)
        return sponsorship_rule(job, mode, regs)

    assert check("Barclays", "London, England, United Kingdom") is None          # UK list, UK job
    assert check("JPMorganChase", "New York, NY") is None                        # US list, US job
    assert check("Goldman Sachs", "Jersey City, NJ") is None                     # "Goldman Sachs & Co. LLC"
    assert check("Barclays", "New York, NY") == "employer not on a sponsor list"  # on UK list only, US job
    assert check("Barclays", "Singapore") is None                                # no list for Singapore
    assert check("Tiny Fintech Ltd", "London, UK") == "employer not on a sponsor list"
    assert check("Tiny Fintech Ltd", "London, UK", sponsorship="Yes") is None     # posting offers it
    assert check("Barclays", "London, UK", mode="posting_only") == "posting doesn't offer sponsorship"
    assert check("Tiny Fintech Ltd", "London, UK", mode="lenient") is None


def test_apply_links(tmp_path):
    from jobscraper.main import needs_reread
    page = ('<code id="applyUrl" style="display: none"><!--"https://www.linkedin.com/jobs/view/externalApply/4012345678'
            '?url=https%3A%2F%2Fbarclays%2Ewd3%2Emyworkdayjobs%2Ecom%2FExternal%2Fjob%2F123%3Fsource%3DLinkedIn'
            '&amp;urlHash=abcd"--></code>')
    assert linkedin.external_apply_url(page) == "https://barclays.wd3.myworkdayjobs.com/External/job/123?source=LinkedIn"
    assert linkedin.external_apply_url("<p>Easy Apply</p>") == ""
    job = Job("LinkedIn", "Market Risk Analyst", "Barclays", "London", "https://www.linkedin.com/jobs/view/1",
              apply_url="https://barclays.example/apply", sources=["LinkedIn"])
    easy = Job("LinkedIn", "Quant Analyst", "Acme", "London", "https://www.linkedin.com/jobs/view/2", sources=["LinkedIn"])
    assert job.apply_on == "Employer website" and easy.apply_on == "LinkedIn"
    path = write_workbook([job, easy], set(), {}, tmp_path / "a.xlsx")
    ws = load_workbook(path)["Jobs"]
    assert ws["Q2"].hyperlink.target == "https://barclays.example/apply" and ws["Q2"].value == "https://barclays.example/apply"
    assert ws["Q3"].hyperlink.target == easy.url
    assert ws["S2"].hyperlink.target == job.url
    assert needs_reread({"url": "https://www.linkedin.com/jobs/view/1"})
    assert needs_reread({"url": "https://www.linkedin.com/jobs/view/1", "apply_url": ""})
    assert not needs_reread({"url": "https://www.linkedin.com/jobs/view/1", "apply_url": "", "easy_apply": True, "experience": "",
                             "qualification": "", "experience": ""})
    easy.easy_apply = True
    assert easy.apply_on == "LinkedIn Easy Apply"
    assert not needs_reread({"url": "https://boards.greenhouse.io/x/jobs/1", "qualification": "", "experience": ""})
    assert needs_reread({"url": "https://boards.greenhouse.io/x/jobs/1"})  # saved before the qualification check


def test_email_schedule():
    from datetime import datetime, timezone
    from jobscraper.schedule import MAX_WAIT_SECONDS, is_due, latest_start, next_start, wait_seconds
    utc = timezone.utc
    now = datetime(2026, 11, 5, 6, 10, tzinfo=utc)  # UK is on GMT
    assert latest_start(CFG, now) == datetime(2026, 11, 5, 5, 5, tzinfo=utc)
    assert next_start(CFG, now) == datetime(2026, 11, 5, 11, 5, tzinfo=utc)
    assert is_due(CFG, now, datetime(2026, 11, 5, 0, 1, tzinfo=utc))
    assert not is_due(CFG, now, datetime(2026, 11, 5, 5, 50, tzinfo=utc))
    assert next_start(CFG, datetime(2026, 11, 5, 12, 0, tzinfo=utc)) == datetime(2026, 11, 5, 17, 5, tzinfo=utc)
    assert next_start(CFG, datetime(2026, 11, 5, 18, 0, tzinfo=utc)) == datetime(2026, 11, 5, 23, 5, tzinfo=utc)
    summer = datetime(2026, 7, 1, 9, 0, tzinfo=utc)  # BST: 12:00 UK = 11:00 UTC
    assert next_start(CFG, summer) == datetime(2026, 7, 1, 10, 5, tzinfo=utc)
    assert wait_seconds(CFG, datetime(2026, 11, 5, 22, 0, tzinfo=utc)) == 3905
    # A gap longer than a GitHub job may run makes the timer wake early.
    long_gap = {**CFG, "email_times": ["00:00", "12:00"]}
    assert wait_seconds(long_gap, datetime(2026, 11, 5, 11, 55, tzinfo=utc)) == MAX_WAIT_SECONDS
    # A run woken early finds no email due, so it only restarts the timer.
    assert not is_due(long_gap, datetime(2026, 11, 5, 17, 25, tzinfo=utc), datetime(2026, 11, 5, 11, 50, tzinfo=utc))


def test_qualifications():
    q = filters.qualification_asked
    assert q("Candidates must hold the CFA or be a qualified accountant (ACA/ACCA).") == "CFA"
    assert q("CFA Level I candidates preferred.") == "CFA"
    assert q("Progress towards FRM is a plus.") == "FRM"
    assert q("You are a Chartered Accountant.") == "Chartered Accountant"
    assert q("Newly qualified CA or ACA with audit background") == "qualified CA"
    assert q("", "Part Qualified ACCA Accountant") == "ACCA"
    assert q("We will support you to study for the ACA qualification.") == ""
    assert q("Our graduate scheme offers a training contract and exam support towards ACCA.") == ""
    assert q("Based in San Francisco, CA. Hybrid working.") == ""
    assert q("Strong Python and SQL skills. Degree in maths.") == ""


def test_experience_and_remote(tmp_path):
    e = filters.experience_asked
    assert e("Proven experience in market risk management.")
    assert e("Previous experience in a similar role is essential.")
    assert e("Candidates should have some experience working in financial services.")
    assert not e("Relevant experience through internships or university projects is welcome.")
    assert not e("You will gain hands-on experience across trading desks.")
    assert not e("No prior experience required.")
    assert not e("We offer an inclusive candidate experience.")
    assert filters.is_remote("Remote, United Kingdom") and filters.is_remote("London", "Quant Analyst (Remote)")
    assert not filters.is_remote("London, England, United Kingdom")
    job = Job("LinkedIn", "Quant Analyst", "Acme", "Remote", "https://x/1", posted=date.today(), remote=True,
              sources=["LinkedIn"])
    other = Job("LinkedIn", "Risk Analyst", "Beta", "London", "https://x/2", posted=date.today(), sources=["LinkedIn"])
    path = write_workbook([job, other], {job.key}, {}, tmp_path / "r.xlsx")
    wb = load_workbook(path)
    assert wb["Remote Jobs"].max_row == 2 and wb["Jobs"]["I2"].value == "Remote"
    msg = build_email([job, other], {job.key}, {}, path, "a@x", "b@x")
    assert "1 remote jobs" in msg.get_body(("plain",)).get_content()


def test_graduate_schemes(tmp_path):
    assert matcher.match("Graduate Programme 2027 - Global Markets")[0]["id"] == "GS"
    assert matcher.match("Investment Banking Analyst Program")[0]["id"] == "GS"
    assert matcher.match("Graduate Scheme - HR") is None
    assert matcher.match("Graduate Scheme - HR", "HSBC")[0]["id"] == "GS"     # target firm
    assert matcher.match("Software Engineering Graduate Programme") is None
    assert matcher.match("Graduate Market Risk Analyst")[0]["id"] == "T1-1"
    job = Job("LinkedIn", "Graduate Programme - Markets", "Acme", "London", "https://x/1", posted=date.today(),
              role_id="GS", sources=["LinkedIn"])
    path = write_workbook([job], {job.key}, {}, tmp_path / "g.xlsx")
    assert load_workbook(path)["Graduate Schemes"].max_row == 2
    assert "1 graduate schemes" in build_email([job], {job.key}, {}, path, "a@x", "b@x").get_body(("plain",)).get_content()


def test_government_jobs():
    import xml.etree.ElementTree as ET
    from jobscraper.sources import government
    matcher = filters.RoleMatcher([])
    assert matcher.match("Finance Officer", government="NHS")[0]["id"] == "GOV"
    assert matcher.match("Assistant Economist", government="Civil Service")
    assert matcher.match("Staff Nurse", government="NHS") is None
    assert matcher.match("Finance Officer") is None  # only for government jobs
    assert filters.is_senior_government("Information Analyst (Band 7)")
    assert filters.is_senior_government("Policy Advisor - Grade 7")
    assert not filters.is_senior_government("Finance Assistant Band 4")
    assert filters.sponsorship("Applications from job seekers who require current Skilled worker "
                               "sponsorship to work in the UK are welcome and will be considered")[0] == "Yes"
    v = ET.fromstring("<vacancyDetails><reference>C1-26-1</reference><title>Finance Officer</title>"
                      "<employer>Oxford Health NHS Trust</employer><postDate>2026-11-04T10:08:37</postDate>"
                      "<locations><location>Oxford, OX4 4XN</location></locations></vacancyDetails>")
    job = government._nhs_job(v, "finance")
    assert job.government == "NHS" and job.location.endswith("United Kingdom")
    assert job.url == "https://www.jobs.nhs.uk/candidate/jobadvert/C1-26-1" == job.apply_link
