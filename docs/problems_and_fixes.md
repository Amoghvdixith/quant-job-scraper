# Scrapper (quant-job-scraper): problems and fixes

**Repo:** github.com/Amoghvdixith/quant-job-scraper, commit `0d488a2` (3 Nov 2026)
**Prepared:** 3 Nov 2026
**Status:** Fixes 1 to 8 and most of 10 are applied on the `fix/report-problems` branch. Fix 9 (repo history growth) is a recommendation only. See "What was applied" at the end.

## How this was checked

- I read every Python module, both workflows, `config.yaml`, `roles.yaml`, and the committed data files `data/last_run.json` and `data/jobs.json`.
- Your auto-mode permissions blocked running the project's own code, so I didn't run it. The timings and the slot calculation below come from small scripts I wrote myself that copy the project's logic and run it on your committed data.
- Line numbers refer to the commit above.

## Summary

| # | Problem | Impact | Severity | Fix effort |
|---|---------|--------|----------|------------|
| 1 | Google Jobs returns nothing, and that is reported as healthy | One of five sources is silently missing | High | Small |
| 2 | Two daily runs search the same rotation slice | 20% of LinkedIn/Indeed/firm searches are wasted, so target firms are covered every ~2 days | High | Small |
| 3 | A failed push after the email loses state | Duplicate emails with the same jobs marked NEW | High | Small |
| 4 | Same title at the same firm in different cities is merged | Jobs lost, and sponsorship is checked against the wrong country | Medium | Small |
| 5 | Workday jobs with an unreadable date count as "posted today" | Stale jobs pass the 5-day limit | Medium | Small |
| 6 | Sponsor-list matching scans 194k names per job | About 67 s of wasted CPU per run | Medium (performance) | Small |
| 7 | Reading descriptions has no time budget | A slow LinkedIn day can make the email late | Medium | Small |
| 8 | Your email address is in the public README | Privacy | Low | Trivial |
| 9 | Repo history grows with every run | Clones slow down over time | Low | Medium |
| 10 | Small issues: README out of date, hard-coded "5 days", counters updated by several threads at once | Confusing, not harmful | Low | Trivial |

The suggested order is: 1, 2 and 3 first (small changes, biggest effect), then 6 and 7 (speed), then 4 and 5 (accuracy).

---

## 1. Google Jobs is silently dead

### What happens

In the last run (`data/last_run.json`, 10:40 UTC today), Google Jobs found **0** jobs with **0 errors**. The warnings list contains 36 copies of `jobspy.google: no job data returned`, one for each role. Because jobspy returns an empty table instead of raising an error, `sources/google.py` returns `[]` and no error is counted. The email footer then shows "Google Jobs 0", which looks like a quiet day rather than a broken source.

### Cause

`jobscraper/sources/google.py:31`: an empty DataFrame is treated as a normal result. Google changes its page often, and jobspy's Google scraper (pinned at 1.4.1) no longer finds the job data.

### Fix

Count an empty result as an error so the problem shows in the email and in `last_run.json`:

```python
# jobscraper/sources/google.py, after scrape_jobs(...)
    if df is None or df.empty:
        stats["errors"] += 1
        return []
    jobs = []
    for row in df.to_dict("records"):
```

Then choose one of these:

- **Recommended:** remove `google` from `sources` in `config.yaml` until a newer python-jobspy release fixes Google. You lose nothing, because it finds nothing now.
- Or try upgrading `python-jobspy` in `requirements.txt` and do a manual dry run. Keep it only if Google returns jobs again.

---

## 2. Two of the five daily runs search the same rotation slice

### What happens

The rotation (which LinkedIn countries, which Indeed countries, and which target firms each run searches) is chosen by:

```python
# jobscraper/main.py:312
slot = now_utc.toordinal() * 6 + now_utc.hour // 4
```

That gives six 4-hour blocks per day. Your five runs start 55 minutes before each email time:

| Season | Run starts (UTC) | `hour // 4` |
|--------|------------------|-------------|
| Winter (GMT) | 04:05, 10:05, 16:05, **22:05, 23:05** | 1, 2, 4, **5, 5** |
| Summer (BST) | 03:05, 09:05, 15:05, **21:05, 22:05** | 0, 2, 3, **5, 5** |

The last two runs of each day fall in the same block, so they get the same slot and repeat exactly the same countries and firms. Only four distinct slices are searched per day. With 50 firms per run and about 400 firms that have no readable careers site, a full pass takes about two days, not "roughly once a day" as the README says.

### Fix

Number the runs by email slot, so every scheduled run gets its own number. Add this to `jobscraper/schedule.py`:

```python
def slot_number(cfg: dict, now: datetime) -> int:
    """A different number for every email slot: day * slots_per_day + slot index."""
    tz = ZoneInfo(cfg.get("email_timezone", "UTC"))
    lead = timedelta(minutes=cfg.get("run_lead_minutes", 40))
    email = (latest_start(cfg, now) + lead).astimezone(tz)
    times = sorted(cfg["email_times"])
    return email.date().toordinal() * len(times) + times.index(email.strftime("%H:%M"))
```

In `jobscraper/main.py`:

```python
from .schedule import slot_number
...
    now_utc = datetime.now(timezone.utc)
    slot = slot_number(cfg, now_utc)
```

Now the five runs of a day get five consecutive numbers, and the rotation moves forward exactly one step per run. A manual run between slots reuses the last slot's number, which is fine.

If you want the firm list covered once a day, also set `linkedin_target_firms_per_run: 80` (about 400 firms ÷ 5 runs). It is 50 now. Watch the time budget in `last_run.json` after changing it.

---

## 3. A failed push after the email can cause a repeat email

### What happens

The order in a run is: send the email, write `data/last_email_utc` and `data/jobs.json`, and then the workflow step commits and pushes them. The step ends like this (`.github/workflows/scrape.yml:73-82`):

```yaml
if: success() && steps.due.outputs.due == 'true'
...
git pull --rebase --autostash || true
git push
```

Two ways this goes wrong:

1. **Rebase conflict.** Both workflows commit `data/sponsor_registers.json`. `main.py` re-downloads it when a list is missing, and the weekly discovery job always does. If both change it at the same time, the rebase stops with a conflict, `|| true` hides it, and `git push` fails.
2. **A crash after the email.** If anything fails after `send()`, for example `write_report`, the step is skipped because of `success()`.

Either way, `last_email_utc` and the "emailed" flags never reach the repo. The next run thinks the email is still due, sends it again, and marks the same jobs as NEW.

### Fix

Retry the push, resolve conflicts in favour of this run's files, and save the state even if the run failed after emailing:

```yaml
      - name: Save which jobs were already emailed
        if: always() && steps.due.outputs.due == 'true'
        run: |
          git config user.name "job-digest-bot"
          git config user.email "job-digest-bot@users.noreply.github.com"
          git add data/jobs.json data/last_run.json data/sponsor_registers.json
          [ -f data/last_email_utc ] && git add data/last_email_utc
          git diff --cached --quiet && exit 0
          git commit -m "Update seen jobs [skip ci]"
          for i in 1 2 3 4; do
            # During a rebase, "theirs" is this run's commit, so our state wins a conflict.
            if git pull --rebase -X theirs origin main && git push origin HEAD:main; then exit 0; fi
            git rebase --abort 2>/dev/null || true
            sleep $((i * 10))
          done
          echo "::error::Could not save state; the next run may resend this email"
          exit 1
```

Make the same change to the "Save the list" step in `discover.yml`, but leave out `-X theirs` there, so the scraper's newer `jobs.json` is never overwritten.

**Optional extra:** in `main.py`, call `save_store(store)` right after `send(...)` and before the report, so the "emailed" flags are on disk as early as possible.

---

## 4. Same title at the same firm in different cities is merged into one job

### What happens

```python
# jobscraper/models.py:40-41
@property
def key(self) -> str:
    return f"{_norm(self.title)}|{_company_key(self.company)}"
```

"Market Risk Analyst" at Barclays in London and the same title at Barclays in New York get the same key. `apply_filters` keeps only the first one. Then:

- you only see one of the two jobs, and
- the visa check uses that one location. If the kept copy is in a country whose register doesn't list the firm, the job is dropped as "employer not on a sponsor list", even though the other copy would have passed.

### Fix

Add the country to the key. Using the country rather than the full location text keeps the cross-source merging that works today: LinkedIn's "London, England, United Kingdom" and Indeed's "London" both map to `UK`.

```python
# jobscraper/models.py
    @property
    def key(self) -> str:
        from .sponsor_registers import country_of
        return f"{_norm(self.title)}|{_company_key(self.company)}|{country_of(self.location)}"
```

`country_of` only recognises the UK, the US and the Netherlands, so jobs in other countries keep today's behaviour (an empty country part). That covers the common case. For finer splitting later, extend `country_of` with more countries.

**What to expect on the next run:** `load_store()` already re-keys the saved jobs, so nothing is lost and jobs that were already emailed stay marked as emailed. Any newly split city copy of a job you already received appears once as NEW.

---

## 5. Workday jobs with an unreadable date count as "posted today"

### What happens

```python
# jobscraper/sources/careers.py:154
jobs.setdefault(url, _job(site, p.get("title"), p.get("locationsText"), url, posted or date.today()))
```

`_workday_posted` only understands English text like "Posted Today", "Posted Yesterday", "Posted 3 Days Ago" and "Posted 30+ Days Ago". When the text is anything else (a non-English site, a missing field, a new wording), the job is given today's date. It then passes the 5-day age check, and keeps passing it every day.

### Fix

Don't invent a date. Leave it empty and count it:

```python
# jobscraper/sources/careers.py, in _workday
                if posted is None and p.get("postedOn"):
                    log.info("%s: unreadable Workday date %r", site["institution"], p.get("postedOn"))
                url = f"{base}/{path}{p.get('externalPath', '')}"
                jobs.setdefault(url, _job(site, p.get("title"), p.get("locationsText"), url, posted))
```

`apply_filters` already drops undated jobs from every source except LinkedIn, so these postings are skipped instead of reported as fresh. If you see many "unreadable Workday date" lines in the logs for one firm, add that wording to `_workday_posted`.

---

## 6. Sponsor-list matching is slow (performance)

### What happens

On every run, `registers.status()` is called for **every** saved job (2,674 today). For any company that isn't an exact match, `_on()` loops in Python over the whole register looking for a name that starts with the company key:

```python
# jobscraper/sponsor_registers.py:107-112
return len(key) >= 6 and any(n.startswith(key) for n in names if len(n) - len(key) <= 12)
```

The registers hold 121,195 (UK), 59,725 (US) and 13,017 (NL) names. I copied this logic into my own script and ran it on your data: about **67 seconds per run**. Only 1,442 of the 2,674 jobs have distinct companies, so most of that work is repeated.

### Fix

Keep a sorted copy of each register, jump to the first possible match with `bisect`, and cache the answer per company:

```python
# jobscraper/sponsor_registers.py
from bisect import bisect_left


class SponsorRegisters:
    def __init__(self) -> None:
        data = json.loads(FILE.read_text()) if FILE.exists() else {}
        self.lists = {c: set(data.get(c, [])) for c in COUNTRIES}
        self.loaded = {c: bool(self.lists[c]) for c in COUNTRIES}
        self._sorted = {c: sorted(self.lists[c]) for c in COUNTRIES}
        self._cache: dict[str, list[str]] = {}

    def _on(self, country: str, key: str) -> bool:
        if key in self.lists[country]:
            return True
        if len(key) < 6:
            return False
        names = self._sorted[country]
        i = bisect_left(names, key)
        while i < len(names) and names[i].startswith(key):
            if len(names[i]) - len(key) <= 12:
                return True
            i += 1
        return False

    def status(self, company: str, location: str) -> str:
        key = clean(company)
        if len(key) < 3:
            return ""
        if key not in self._cache:
            self._cache[key] = [c for c in COUNTRIES if self.lists[c] and self._on(c, key)]
        on = self._cache[key]
        if not on:
            return ""
        here = country_of(location)
        if here in on:
            return f"Yes ({here} register)"
        return f"Sponsors in {'/'.join(on)}"
```

**Result from my script:** the same answers as the current code on a 600-job sample, and **0.04 seconds** for all 2,674 jobs instead of about 67 seconds.

---

## 7. Reading descriptions has no time budget

### What happens

The 40-minute `source_time_budget_minutes` limits only the searches. After that, `enrich_all` (`main.py:271`) reads up to 400 LinkedIn postings one at a time. Each read waits 1 to 2.5 seconds, and a rate limit adds 10 to 30 seconds per retry. That can take 10 to 25 minutes. A run starts only 55 minutes before the email time, so a slow LinkedIn day can push the email late. Today's 11:00 run finished at 10:40, which leaves a 20-minute margin.

### Fix

Give description reading its own budget. Jobs that don't get read are handled the same way as jobs past the 400 cap: they are marked "Not checked" and read on the next run.

```yaml
# config.yaml
description_time_budget_minutes: 10
```

```python
# jobscraper/main.py
def enrich_all(jobs: list[Job], budget_minutes: float) -> None:
    deadline = time.monotonic() + budget_minutes * 60
    slow = [j for j in jobs if "linkedin.com" in j.url and len(j.description or "") < 600]
    fast = [j for j in jobs if j not in slow]

    def one(job: Job) -> None:
        ...  # unchanged

    def run_slow() -> None:
        for i, job in enumerate(slow):
            if i >= MAX_DESCRIPTION_FETCHES or time.monotonic() > deadline:
                enrich(job, job.description or "")  # read on the next run
                job.sponsorship = "Not checked"
            else:
                one(job)
    ...

# in main():
    enrich_all([job for _, job, _ in to_read], cfg.get("description_time_budget_minutes", 10))
```

Searches (40 min) plus descriptions (10 min) then fit inside the 55-minute lead time.

---

## 8. Your email address is in the public README

`README.md:48` shows your personal address as the example for `MAIL_TO`, and the repo is public. Replace it with a placeholder:

```markdown
   - `MAIL_TO`: where the digest goes (e.g. `you@example.com`)
```

It stays in old commits, but it won't be on the front page.

**Why not make the repo private instead:** on a free plan, private repos get 2,000 Actions minutes a month. Five scrape runs of about 50 minutes each come to about 7,500 minutes a month, and the `timer` job sleeps on a runner almost all day on top of that. A private repo would run out of minutes within days. Public repos get unlimited free minutes, so keep it public and keep personal details out of it.

---

## 9. Repo history grows with every run

`data/jobs.json` (2.5 MB) is rewritten and committed up to five times a day, and `data/sponsor_registers.json` (3.8 MB) is committed every week. Git compresses these files, but the history still grows steadily, and clones and checkouts get slower. I couldn't measure the actual repo size from here.

**Fix (when it starts to matter):** keep the state files on a separate `state` branch that always holds a single commit. Each run checks that branch out into `data/`, then force-pushes one new commit to replace it, so no history builds up. This means changing both workflows and how `schedule.py` reads `last_email_utc`, so it is worth doing only once checkouts get noticeably slow. A cheaper first step: write `jobs.json` without indentation (`json.dumps(store, sort_keys=True)`), but that only saves about 7% (2.48 MB down to 2.31 MB on today's file), so the separate branch is the real fix.

---

## 10. Small issues

| Where | Problem | Fix |
|-------|---------|-----|
| `README.md:67,70` | Says 80 firms and six LinkedIn countries per run. `config.yaml` has 50 and 4. | Update the README, or set the config to match (see fix 2). |
| `mailer.py:16` | The subject always says "in the last 5 days", even if you change `max_age_days`. | Pass `cfg["max_age_days"]` into `build_email` and use it in the subject and the body text. |
| `main.py:99,114` | Several careers-site threads update `stats[label]["errors"]` at the same time without a lock. Rarely, a count could be off by one. | Add `lock = threading.Lock()` and wrap the increment in `with lock:`. |
| `careers.py:_workday` | The comment says "keep scanning this page", but the loop then stops after the page whenever any old job was seen. | Harmless, because results are mostly newest first. Fix the comment, or stop only when the whole page is old. |
| Terms of use | LinkedIn's and eFinancialCareers' logged-out pages are scraped. That is against their terms and breaks whenever they change their layout. | Already noted in the README. The fix for problem 1 (counting empty results as errors) makes this kind of breakage visible. Apply the same check in `linkedin.py` and `efinancialcareers.py`. |

---

## How to test the fixes

1. `python -m pytest`. The 20 existing filter tests should still pass.
2. Add tests for the new behaviour:
   - `slot_number` gives five different, consecutive numbers for the five run times of one day, in both winter and summer.
   - `SponsorRegisters.status` gives the same results before and after fix 6 for a list of company names.
   - Two jobs with the same title and company in London and New York get different keys, and LinkedIn "London, England, United Kingdom" and Indeed "London" still get the same key.
3. Run a dry run from the Actions tab with "Send the email" unticked. Then check `data/last_run.json`: Google Jobs shows errors (or is gone), the rotation slot changes from run to run, and the total run time is shorter.

---

## What was applied on this branch

| # | Applied | Files |
|---|---------|-------|
| 1 | Yes. Empty Google results now count as errors, and `google` is removed from `sources`. | `sources/google.py`, `config.yaml`, `README.md` |
| 2 | Yes. `slot_number()` gives each email slot its own number. `linkedin_target_firms_per_run` stays at 50. | `schedule.py`, `main.py` |
| 3 | Yes. The save step runs with `always()` and retries the push 4 times. Same retry added to `discover.yml`. | `.github/workflows/scrape.yml`, `.github/workflows/discover.yml` |
| 4 | Yes. The country is part of the job key. | `models.py` |
| 5 | Yes. An unreadable Workday date stays empty and gets logged. | `sources/careers.py` |
| 6 | Yes. Binary search plus a per-employer cache. The sorted copies are built on first use, so the existing tests that create the object without `__init__` keep working. 0.13 s for all saved jobs, down from about 67 s. | `sponsor_registers.py` |
| 7 | Yes. `description_time_budget_minutes: 10`. | `main.py`, `config.yaml` |
| 8 | Yes. The README uses a placeholder address. | `README.md` |
| 9 | No. Recommendation only. | |
| 10 | Mostly. README numbers fixed, the email uses `max_age_days`, the careers error counter has a lock, and the Workday comment is corrected. The empty-result check is not yet added to LinkedIn and eFinancialCareers. | `README.md`, `mailer.py`, `main.py`, `sources/careers.py` |

New tests are in `tests/test_fixes.py`. All 24 tests pass.
