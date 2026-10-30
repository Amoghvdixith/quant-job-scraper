# Quant job digest

Every 4 hours this searches LinkedIn, Indeed, Google Jobs, eFinancialCareers and
the careers sites of the 500 institutions in `institutions.csv` for the
entry-level quant / risk / valuation roles in `roles.yaml`, and emails an Excel
file of matching jobs posted in the last 5 days. There is no website: it runs on
GitHub Actions and the email is the only output.

## What gets kept

- **Role match:** the job title has to match one of the keywords in `roles.yaml`
  (taken from the Tier 1 and Tier 2 sheets of `Quant_Finance_Job_Roles.xlsx`).
- **Fresh:** posted within `max_age_days` (5).
- **Entry level:** titles with Senior, Lead, VP, Director, Manager and similar
  words are dropped, and so are postings asking for more than
  `max_years_experience` (2) years. LinkedIn searches are limited to Internship,
  Entry level and Associate.
- **Anywhere except India and the UAE**, remote jobs included.
- **Visa sponsorship:** a job is kept only if the posting offers sponsorship, or the
  employer is on the government sponsor list for the job's country: the UK Home Office
  register of licensed sponsors, the US H-1B employer data, or the Dutch IND register.
  For countries without a public list (e.g. Singapore), an employer on any of those lists
  counts. Postings that say "no sponsorship" are always dropped. Change this with
  `sponsorship_filter` in `config.yaml`.

Each job has an **Apply Link**: the employer's own application page when one is found
(careers sites, LinkedIn "Apply on company website" jobs, Indeed), otherwise the listing itself.

Each email holds every matching job from the last 5 days. Jobs that weren't in
any earlier email are marked **NEW** and listed first. `data/jobs.json` remembers
what was already sent; the workflow commits it back after each run.

## Setup

1. In the repo, go to **Settings → Secrets and variables → Actions → New repository secret** and add:
   - `GMAIL_USER`: the Gmail address that sends the email
   - `GMAIL_APP_PASSWORD`: a Gmail App Password for that account (https://myaccount.google.com/apppasswords; needs 2-step verification)
   - `MAIL_TO`: where the digest goes (e.g. `avdixith@gmail.com`)
2. **Actions** tab → enable workflows if asked → **Quant job digest** → **Run workflow** to test it straight away.
   Untick "Send the email" for a dry run; the Excel file is then downloadable from the run page.

After that it runs by itself. The email arrives at the times in `email_times` in
`config.yaml` (00:00, 05:00, 11:00, 17:00 and 23:00 UK time); each run starts 40 minutes
earlier. GitHub's own schedule skips many runs, so each run starts the next one itself
(the `timer` job), and an hourly check catches any slot that was still missed.

## Target institutions

`institutions.csv` is your list of 500 firms. They are covered three ways:

- **Their own careers sites.** The weekly "Find careers sites" workflow works out
  which hiring platform each firm uses (Workday, Oracle, Greenhouse, Lever, Ashby,
  SmartRecruiters) and saves it to `data/careers_sites.json`. Every run then reads
  those sites directly. If a firm is missing or wrong, add it to
  `careers_sites_manual.yaml`.
- **LinkedIn by company name** for firms without a readable careers site,
  80 firms per run in rotation, so the whole list is covered roughly once a day.
- The **"On Your Target List"** column marks any job, from any source, at one of these firms.

LinkedIn also searches a couple of extra countries per run and Indeed three
countries per run, in rotation (see `config.yaml`). After each run,
`data/last_run.json` shows how many jobs each source returned and any errors.

## Changing what it searches

- Roles and keywords: `roles.yaml`
- Age limit, excluded countries, seniority words, countries, pages per search: `config.yaml`
- Target institutions: `institutions.csv`

## Run locally

```bash
pip install -r requirements.txt
python -m jobscraper.main --no-email          # writes out/quant_jobs_*.xlsx
python -m jobscraper.main --no-email --roles T1-1,T2-1   # just a couple of roles
python -m pytest
```

## Notes

- LinkedIn and Google Jobs are read from their public, logged-out pages, and
  eFinancialCareers from the data its website loads. None of them offer an
  official free API, so a source can occasionally block a run or change its
  layout. The "Run Summary" sheet and the email footer show how many jobs each
  source returned and how many requests failed, so a broken source is easy to spot.
- Google Jobs goes through the MIT-licensed [python-jobspy](https://github.com/speedyapply/JobSpy) library.
