from datetime import date, timedelta

from jobscraper.healer import REST_AFTER_FAILED_RUNS, TRIP_AFTER_FAILURES, Healer


def _healer(tmp_path, today=date(2026, 11, 13)):
    return Healer.load(tmp_path / "health.json", sleep=lambda s: None, today=today)


def test_retry_fixes_a_one_off_failure(tmp_path):
    h = _healer(tmp_path)
    calls = []

    def flaky(stat):
        calls.append(1)
        if len(calls) == 1:
            raise TimeoutError("read timed out")
        return ["job"]

    assert h.call("Indeed", "quant @ uk", flaky, {}) == ["job"]
    assert [e.kind for e in h.events] == ["fixed"]


def test_site_that_keeps_failing_is_skipped_for_the_rest_of_the_run(tmp_path):
    h = _healer(tmp_path)
    calls = []

    def broken(stat):
        calls.append(1)
        raise ConnectionError("reset")

    results = [h.call("LinkedIn", f"search {i}", broken, {}) for i in range(TRIP_AFTER_FAILURES + 3)]
    assert results[:TRIP_AFTER_FAILURES] == [None] * TRIP_AFTER_FAILURES
    assert results[TRIP_AFTER_FAILURES:] == [[]] * 3          # skipped, not counted as errors
    assert len(calls) == TRIP_AFTER_FAILURES * 2              # each failure was tried twice
    h.check_sources({})
    kinds = {(e.area, e.kind) for e in h.events}
    assert ("LinkedIn", "problem") in kinds and ("LinkedIn", "fixed") in kinds


def test_careers_site_rests_after_failing_several_runs_then_comes_back(tmp_path):
    def broken(stat):
        raise ValueError("layout changed")

    for _ in range(REST_AFTER_FAILED_RUNS):
        h = _healer(tmp_path)
        assert h.call_site("Acme Bank", broken, {}) is None
        h.save({}, {})
    h = _healer(tmp_path)
    assert h.site_resting("Acme Bank")
    assert h.call_site("Acme Bank", lambda st: ["never called"], {}) == []
    h.save({}, {})
    assert "Acme Bank" in (tmp_path / "HEALTH.md").read_text()

    later = _healer(tmp_path, today=date(2026, 11, 13) + timedelta(days=10))
    assert later.call_site("Acme Bank", lambda st: ["job"], {}) == ["job"]
    later.check_sources({})
    assert any("came back" in e.what for e in later.events)
    assert "Acme Bank" not in later.state["sites"]


def test_sudden_drop_is_flagged(tmp_path):
    h = _healer(tmp_path)
    for n in (5000, 4800, 5100):
        h.state["runs"].append({"utc": "2026-11-12T00:00:00", "sources": {"LinkedIn": {"found": n, "errors": 0}},
                                "events": []})
    h.check_sources({"LinkedIn": {"found": 12, "errors": 0}})
    assert [(e.area, e.kind) for e in h.events] == [("LinkedIn", "problem")]
    h2 = _healer(tmp_path)
    h2.state["runs"] = h.state["runs"]
    h2.check_sources({"LinkedIn": {"found": 4700, "errors": 0}})
    assert h2.events == []


def test_email_retries_then_gives_up(tmp_path):
    h = _healer(tmp_path)
    tries = []
    assert h.send_email(lambda: tries.append(1) or (_ for _ in ()).throw(OSError("SMTP down"))) is False
    assert len(tries) == 3 and h.events[-1].area == "Email"

    h = _healer(tmp_path)
    tries = []

    def second_time_lucky():
        tries.append(1)
        if len(tries) == 1:
            raise OSError("SMTP busy")

    assert h.send_email(second_time_lucky) is True
    assert h.events[-1].kind == "fixed"


def test_report_and_email_section(tmp_path):
    h = _healer(tmp_path)
    assert h.email_section() == ""
    h.record("problem", "eFinancialCareers", "found 0 jobs; it usually finds about 4000", "check the scraper")
    assert "Needs a look" in h.email_section()
    h.save({"eFinancialCareers": {"found": 0, "errors": 2}}, {"jobs_in_email": 10, "new_jobs": 1})
    md = (tmp_path / "HEALTH.md").read_text()
    assert "## Needs a look" in md and "eFinancialCareers" in md and "0 (2 err)" in md


def test_corrupt_state_file_is_replaced(tmp_path):
    (tmp_path / "health.json").write_text("{not json")
    h = _healer(tmp_path)
    assert h.state["runs"] == [] and h.events[0].kind == "fixed"


def test_scrape_uses_the_problem_solver(tmp_path, monkeypatch):
    from jobscraper import main, healer as healer_mod
    from jobscraper.models import Job

    monkeypatch.setattr(healer_mod, "RETRY_PAUSE_SECONDS", 0)
    job = Job(source="Indeed", title="Quant Analyst", company="Acme", location="London", url="https://x/1")

    def boom(st):
        raise RuntimeError("blocked")

    monkeypatch.setattr(main, "plan", lambda cfg, roles, slot: {
        "Indeed": [("a", lambda st: [job]), ("b", boom)],
        "Careers sites": [("Acme Bank", boom), ("Beta Bank", lambda st: [job])],
    })
    h = Healer.load(tmp_path / "health.json", sleep=lambda s: None)
    jobs, stats = main.scrape({}, [], 0, h)
    assert len(jobs) == 2
    assert stats == {"Indeed": {"found": 1, "errors": 1}, "Careers sites": {"found": 1, "errors": 1}}
    assert h.state["sites"]["Acme Bank"]["failed_runs"] == 1


def test_platform_outage_does_not_rest_sites(tmp_path):
    from jobscraper.healer import OUTAGE_SITES

    def down(stat):
        raise RuntimeError("521 Server Error: <none> for url: https://x.wd5.myworkdayjobs.com/jobs")

    sites = [f"Bank {i}" for i in range(OUTAGE_SITES)]
    for _ in range(REST_AFTER_FAILED_RUNS + 1):
        h = _healer(tmp_path)
        for s in sites:
            assert h.call_site(s, down, {}) is None
        h.check_sources({})
        h.save({}, {})
    h = _healer(tmp_path)
    assert not any(h.site_resting(s) for s in sites)
    assert all(h.state["sites"][s].get("failed_runs", 0) == 0 for s in sites)
    assert "521" in h.state["sites"][sites[0]]["last_error"]
    assert "hosting platform" in (tmp_path / "HEALTH.md").read_text()


def test_a_few_failing_sites_still_count_towards_a_rest(tmp_path):
    from jobscraper.healer import OUTAGE_SITES

    def down(stat):
        raise ValueError("Expecting value: line 1 column 1 (char 0)")

    sites = [f"Bank {i}" for i in range(OUTAGE_SITES - 1)]
    for _ in range(REST_AFTER_FAILED_RUNS):
        h = _healer(tmp_path)
        for s in sites:
            assert h.call_site(s, down, {}) is None
        h.check_sources({})
        h.save({}, {})
    assert all(_healer(tmp_path).site_resting(s) for s in sites)
