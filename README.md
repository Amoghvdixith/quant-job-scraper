# Quant job digest

Every 4 hours this searches LinkedIn, Google Jobs and eFinancialCareers for the
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
- **Visa sponsorship:** postings that say they can't sponsor (or need an existing
  right to work) are dropped. Postings that offer sponsorship are listed first.
  For UK jobs, the "UK Licensed Sponsor" column checks the company against the
  Home Office register of licensed sponsors.

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

After that it runs by itself at 00:00, 04:00, 08:00, 12:00, 16:00 and 20:00 UTC.
GitHub can start scheduled runs a few minutes late.

## Changing what it searches

- Roles and keywords: `roles.yaml`
- Age limit, excluded countries, seniority words, LinkedIn locations and pages: `config.yaml`

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
