# Quant job digest

Four times a day this searches LinkedIn, Indeed, eFinancialCareers and
the careers sites of the 500 institutions in `institutions.csv` for the
entry-level quant / risk / valuation roles in `roles.yaml`, and emails an Excel
file of matching jobs posted in the last 5 days. There is no website: it runs on
GitHub Actions and the email is the only output.

## What gets kept

- **Role match:** the job title has to match one of the keywords in `roles.yaml`
  (taken from the Tier 1 and Tier 2 sheets of `Quant_Finance_Job_Roles.xlsx`).
- **Graduate schemes** anywhere in the world, remote or on-site: titles like "Graduate
  Programme", "Analyst Program" or "Graduate Scheme 2027" in a finance area (markets, risk,
  banking, investment...), or any graduate scheme at a firm in `institutions.csv`. They have
  their own "Graduate Schemes" sheet and email section; the other rules still apply.
- **Fresh:** posted within `max_age_days` (5).
- **Entry level:** titles with Senior, Lead, VP, Director, Manager and similar
  words are dropped, and so are postings that ask for any work experience: a years figure
  ("1+ years of experience") or wording like "proven experience in" or "you have experience
  with". Internship or university experience doesn't count. See `experience_filter`. LinkedIn searches are limited to Internship,
  Entry level and Associate.
- **No professional qualifications asked:** postings that ask for CA, ACA, ACCA, CIMA, CPA,
  CFA, FRM, CQF, CAIA, actuarial or similar (required or preferred) are dropped, unless the
  employer is offering to train you for it.
- **Anywhere except India and the Middle East**, remote jobs included. Every run also
  searches LinkedIn for remote jobs worldwide; remote jobs are marked in the "Work Type"
  column, listed in their own "Remote Jobs" sheet and in a section of the email.
- **Visa sponsorship:** a job is kept only if the posting offers sponsorship, or the
  employer is on the government sponsor list for the job's country: the UK Home Office
  register of licensed sponsors, the US H-1B employer data, or the Dutch IND register.
  For countries without a public list (e.g. Singapore), an employer on any of those lists
  counts. Postings that say "no sponsorship" are always dropped. Change this with
  `sponsorship_filter` in `config.yaml`.

**How many people each employer has sponsored** is in three columns of every jobs sheet and in
short form under "Visa sponsorship" in the email. Numbers come only from published government data;
nothing is estimated:

- **UK People Sponsored (CoS):** certificates of sponsorship the employer was assigned per year, from
  the Home Office's Freedom of Information release FOI 2025/12841, which covers every licensed sponsor
  for 2021-2024 (Skilled Worker, plus Global Business Mobility / ICT shown separately). One certificate
  is one sponsored job offer. The Home Office shows 1 to 4 as "*", written here as "1-4". Newer
  releases can be added to `UK_COS_SOURCES` in `jobscraper/sponsor_registers.py`. A firm that isn't in
  the figures shows "Not found", never 0.
- **UK Sponsor Licence:** licence rating and visa routes from the Home Office register.
- **US H-1B Approvals:** approved H-1B petitions in the latest fiscal years (new employment and
  extensions), from the USCIS H-1B Employer Data Hub.
- The Netherlands' IND register publishes names only, so there is no Dutch number.

Each job has an **Apply Link**: the employer's own application page when one is found
(careers sites, LinkedIn "Apply on company website" jobs, Indeed), otherwise the listing itself.

Each job also has two Claude links (in the email tables and as columns in every jobs sheet):
**Tailor CV** opens claude.ai with a cv-tailoring request for that job typed in, and
**Apply with Claude** also has Claude in Chrome fill the employer's application form from your
apply profile. It stops before Submit, so you review and submit yourself. Setup and limits are in
[docs/APPLY_ASSISTANT.md](docs/APPLY_ASSISTANT.md). The fields the apply profile needs are listed in
`apply_profile.example.yaml`. This repo is public, so keep your real answers in the private
apply-assistant skill.

Each email holds every matching job from the last 5 days. Jobs that weren't in
any earlier email are marked **NEW** and listed first. `data/jobs.json` remembers
what was already sent; the workflow commits it back after each run.

## Problem solver and health report

`jobscraper/healer.py` watches every run and deals with what goes wrong instead of just logging it:

- **Failed search** (timeout, connection reset, parse error): tried once more after a pause.
- **Site that keeps failing within a run** (5 failures in a row): its remaining searches are skipped,
  so it stops eating the time budget, and the other sites still finish before the email.
- **Careers site that fails on 3 runs in a row**: rested for 3 days, then tried again automatically.
- **Sudden drop**: a source that finds under 20% of its usual number (median of recent runs) is flagged as
  a likely block or page-layout change, with the file to look at.
- **Email failure**: retried 3 times with backoff. If it still fails, the jobs are not marked as emailed,
  so the next run sends them, and the run shows as failed in the Actions tab.
- **Sponsor lists, hackathons, startups**: a failure there no longer stops the run. It is recorded and
  the email goes out without that part.

Each run writes `data/health.json` (state between runs) and **`data/HEALTH.md`**, a readable report
covering what needs a look, what was fixed automatically, resting careers sites, jobs found per source over
the last 10 runs and the most frequent problems. The email gets a short "Run health" section whenever
something happened.

To follow it in a Claude project (e.g. "Performance Analizer"): in that project choose **Add content →
GitHub**, pick this repo and select `data/HEALTH.md` (and `data/last_run.json` if you want the raw
figures). Press sync in the project to pull the latest report, then ask Claude about it there.

## Setup

1. In the repo, go to **Settings → Secrets and variables → Actions → New repository secret** and add:
   - `GMAIL_USER`: the Gmail address that sends the email
   - `GMAIL_APP_PASSWORD`: a Gmail App Password for that account (https://myaccount.google.com/apppasswords; needs 2-step verification)
   - `MAIL_TO`: where the digest goes (e.g. `you@example.com`)
2. **Actions** tab → enable workflows if asked → **Quant job digest** → **Run workflow** to test it straight away.
   Untick "Send the email" for a dry run; the Excel file is then downloadable from the run page.

After that it runs by itself. The email arrives at the times in `email_times` in
`config.yaml` (00:00, 06:00, 12:00 and 18:00 UK time); each run starts 55 minutes
earlier. GitHub's own schedule skips many runs, so each run starts the next one itself
(the `timer` job), and an hourly check catches any slot that was still missed. The
timer waits at most 5.5 hours (a GitHub job may run for 6), so across the long
12:00 to 00:00 gap it starts one extra run that finds nothing due and just waits again.

## Target institutions

`institutions.csv` is your list of 500 firms. They are covered three ways:

- **Their own careers sites.** The weekly "Find careers sites" workflow works out
  which hiring platform each firm uses (Workday, Oracle, Greenhouse, Lever, Ashby,
  SmartRecruiters) and saves it to `data/careers_sites.json`. Every run then reads
  those sites directly. If a firm is missing or wrong, add it to
  `careers_sites_manual.yaml`.
- **LinkedIn by company name** for firms without a readable careers site,
  50 firms per run in rotation (`linkedin_target_firms_per_run`), so with three runs a day the whole list
  is covered about every three days.
- The **"On Your Target List"** column marks any job, from any source, at one of these firms.

LinkedIn also searches four extra countries per run and Indeed five
countries per run, in rotation (see `config.yaml`). After each run,
`data/last_run.json` shows how many jobs each source returned and any errors.

## Changing what it searches

- Roles and keywords: `roles.yaml`
- Age limit, excluded countries, seniority words, countries, pages per search: `config.yaml`
- Target institutions: `institutions.csv`

How it all works, with a diagram: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

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
- Google Jobs is switched off in `config.yaml` because python-jobspy 1.4.1 no longer gets any
  results from it. When it was on, it went through the MIT-licensed [python-jobspy](https://github.com/speedyapply/JobSpy) library.

## UK government jobs

A "Government Jobs" sheet and email section list NHS and Civil Service roles in finance, economics,
data, risk, audit, procurement and similar areas. The same rules apply as for every other job
(entry level, last 5 days, no experience or professional qualification asked, sponsorship).
NHS Bands 7 and above and Civil Service Grade 6/7, SEO and SCS roles count as too senior.

- NHS Jobs: read from its public search feed.
- Civil Service: Civil Service Jobs puts a "prove you're human" check in front of every page, and
  Find a Job (DWP) blocks GitHub's servers, so civil service roles come from the departments'
  own LinkedIn postings (list in `config.yaml` under `government`).
- Civil Service Careers and the Government Recruitment Service are guidance sites with no job listings.

## Internships

An "Internships" sheet and email section list internships, placements, summer and off-cycle
programmes worldwide (remote and on-site) in risk work across lending and consumer credit,
payments, wealth-tech, insurtech, market infrastructure, crypto and climate/energy, plus the
usual finance areas. LinkedIn is searched at its "Internship" level for these. The usual rules
(last 5 days, no experience or qualification asked, sponsorship, excluded countries) still apply.

## Quant finance hackathons

A separate "Hackathons" sheet and email section list hackathons, trading competitions and
financial ML challenges tied to quantitative finance (trading, markets, portfolios, risk,
derivatives, alpha research...) that **graduates can enter**, so student-only events are left out.
It isn't a job list: it has its own columns (organiser, focus, who can enter in the organiser's
words, dates and deadline, days left, format, prize, link). Hackathons not in an earlier email
are marked NEW.

- **Quant Challenges** (quantchallenges.com), an independent registry of quant trading and
  financial ML competitions: its "Open now" list and first pages are read, then each listing's
  "Who can enter", deadline, status, organiser and prize.
- **Devpost**: hackathons with the Fintech theme or matching words like quant, trading, finance
  or hedge fund, kept only when the hackathon itself is about quant finance. Eligibility comes
  from its "Who can participate" box.
- **`hackathons.yaml`**: always-open competitions added by hand (Numerai, Numerai Signals, Crunch).

A hackathon is dropped when its eligibility says students only (e.g. "must be currently enrolled",
"undergraduate students"), when it isn't about quant finance, or when its deadline has passed or
entries are closed. "Open to graduates" means the wording names graduates, professionals or
anyone; "No student requirement stated" means it doesn't limit entry to students; "Not stated"
means no eligibility wording was found, so check the rules. Settings are under `hackathons` in
`config.yaml`.

## Startups and boutique firms that take graduates

A separate "Startups & Boutiques" sheet and email section list open roles that **a recent
graduate could get** at:

- **quant and fintech startups** (trading and market making, market data, prediction markets,
  DeFi risk, AI for investment research, lending and credit risk, financial crime, payments and
  investing apps);
- **boutique firms**: small proprietary trading firms, boutique quant hedge funds, independent
  advisory banks (M&A, restructuring) and risk/treasury consultancies.

Both are listed in **`startups.yaml`** (`startups` and `boutiques`: name, what they do, stage or
kind of firm, HQ and, when known, their job board); add or remove firms there. The sheet's
"Firm Type" column says which list a firm is on. Their open roles are read from
the startup's public Greenhouse, Lever, Ashby or SmartRecruiters board. A firm without a board
in the file is looked up by name on each platform, a few per run, and the answer is remembered.

A role is kept when it isn't senior or an internship, is in a quant, trading, risk, data,
finance, advisory or engineering area (not sales, marketing, legal...), isn't in an excluded country, the
posting doesn't rule out visa sponsorship, and a graduate could get it:

- **Graduate / junior role**: the title says graduate, new grad, junior, entry level, early
  career, associate, analyst programme or level I;
- **Welcomes graduates**: the description says new grads, recent graduates, early career,
  entry level, "0-2 years" or "no experience required";
- **No experience asked**: no years of experience and no "proven experience in..." wording.

Roles asking for more than 2 years are dropped. Unlike the Jobs sheet, every open role is listed
(not only the last 5 days), since startups hire less often; new ones are marked NEW. The sheet also
shows whether the posting offers sponsorship and whether the employer is on a sponsor register.
Settings are under `startups` in `config.yaml`.
