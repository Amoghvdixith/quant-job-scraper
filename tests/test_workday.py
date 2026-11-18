import pytest
import requests

from jobscraper.sources import careers


class _Resp:
    def __init__(self, status, payload=None, headers=None):
        self.status_code = status
        self._payload = payload or {"jobPostings": []}
        self.headers = headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Client Error: Too Many Requests")


class _Session:
    def __init__(self, statuses, payload=None):
        self.statuses = list(statuses)
        self.payload = payload
        self.calls = 0
        self.bodies = []

    def post(self, api, json=None, timeout=None):
        self.calls += 1
        self.bodies.append(json)
        return _Resp(self.statuses.pop(0), self.payload)


class _Clock:
    def __init__(self):
        self.now = 1000.0
        self.slept = []

    def __call__(self):
        return self.now

    def sleep(self, t):
        self.slept.append(t)
        self.now += t


@pytest.fixture(autouse=True)
def _fresh():
    careers._workday_blocked.clear()
    careers._workday_last[0] = -1e9
    yield
    careers._workday_blocked.clear()
    careers._workday_last[0] = -1e9


def test_one_request_per_site_for_the_newest_postings():
    payload = {"jobPostings": [{"title": "Risk Analyst", "externalPath": "/job/London/Risk_R1",
                                "postedOn": "Posted Today", "locationsText": "London"}]}
    s = _Session([200], payload)
    site = {"id": "barclays.wd3/External", "institution": "Barclays", "platform": "workday"}
    jobs = careers._workday(s, site, {"max_age_days": 7})
    assert s.calls == 1
    assert s.bodies[0]["searchText"] == "" and s.bodies[0]["limit"] == careers.WORKDAY_LIMIT
    assert [j.title for j in jobs] == ["Risk Analyst"]


def test_workday_requests_are_kept_apart():
    clock = _Clock()
    for _ in range(3):
        careers._workday_post(_Session([200]), "https://a.wd1.myworkdayjobs.com/wday/cxs/a/b/jobs", {},
                              sleep=clock.sleep, clock=clock)
    # the first goes at once, each later one waits out the gap
    assert clock.slept == [careers.WORKDAY_GAP, careers.WORKDAY_GAP]


def test_a_429_is_waited_out_once():
    clock = _Clock()
    s = _Session([429, 200])
    r = careers._workday_post(s, "https://x.wd3.myworkdayjobs.com/wday/cxs/x/y/jobs", {},
                              sleep=clock.sleep, clock=clock)
    assert r.status_code == 200 and s.calls == 2
    assert careers.WORKDAY_429_WAIT in clock.slept
    assert not careers._workday_blocked.is_set()


def test_a_blocked_run_fails_the_other_workday_sites_fast():
    clock = _Clock()
    s = _Session([429] * careers.WORKDAY_429_TRIES)
    with pytest.raises(requests.HTTPError):
        careers._workday_post(s, "https://a.wd1.myworkdayjobs.com/wday/cxs/a/b/jobs", {},
                              sleep=clock.sleep, clock=clock)
    assert careers._workday_blocked.is_set()
    waited = len(clock.slept)
    s2 = _Session([429])
    with pytest.raises(requests.HTTPError):
        careers._workday_post(s2, "https://b.wd1.myworkdayjobs.com/wday/cxs/b/c/jobs", {},
                              sleep=clock.sleep, clock=clock)
    assert s2.calls == 0 and len(clock.slept) == waited    # no request and no wait once Workday is blocking


def test_descriptions_are_skipped_once_workday_is_blocking():
    from jobscraper.models import Job
    careers._workday_blocked.set()
    job = Job(source="Careers sites", title="Risk Analyst", company="Barclays", location="London",
              url="https://barclays.wd3.myworkdayjobs.com/External/job/London/Risk_R1", posted=None)
    assert careers.fetch_description(job) == ""
