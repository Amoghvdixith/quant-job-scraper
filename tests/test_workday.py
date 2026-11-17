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
    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.calls = 0

    def post(self, api, json=None, timeout=None):
        self.calls += 1
        return _Resp(self.statuses.pop(0))


@pytest.fixture(autouse=True)
def _fresh():
    careers._workday_blocked.clear()
    yield
    careers._workday_blocked.clear()


def test_a_429_is_waited_out_and_retried():
    waits = []
    s = _Session([429, 429, 200])
    r = careers._workday_post(s, "https://x.wd3.myworkdayjobs.com/wday/cxs/x/y/jobs", {}, sleep=waits.append)
    assert r.status_code == 200 and s.calls == 3
    assert [w for w in waits if w >= 10] == [10, 20]       # backoff between tries
    assert not careers._workday_blocked.is_set()


def test_a_blocked_run_fails_the_other_workday_sites_fast():
    s = _Session([429] * careers.WORKDAY_429_TRIES)
    with pytest.raises(requests.HTTPError):
        careers._workday_post(s, "https://a.wd1.myworkdayjobs.com/wday/cxs/a/b/jobs", {}, sleep=lambda t: None)
    assert careers._workday_blocked.is_set()
    s2 = _Session([429])
    with pytest.raises(requests.HTTPError):
        careers._workday_post(s2, "https://b.wd1.myworkdayjobs.com/wday/cxs/b/c/jobs", {}, sleep=lambda t: None)
    assert s2.calls == 1                                    # no long wait once Workday is known to be blocking
