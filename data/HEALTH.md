# Quant job scraper: health report

Written by the problem solver (`jobscraper/healer.py`) at the end of every run. Sync this file into the Performance Analizer Claude project to track it there.

Last run: 2026-11-24T11:39:33+00:00

## Status

2 problem(s) need a look, 0 handled automatically.

Jobs in email: 233, new: 2, raw results: 16186, emailed: True.

## Needs a look

- **Careers sites**: 50 sites failed in the same run (likely an outage or block at their hosting platform). Not counted towards resting them; they are tried again next run.
- **Indeed**: found 15 jobs; it usually finds about 108. Likely blocked or the site changed its page layout; the run carried on with the other sources. If it repeats next run, its scraper in jobscraper/sources needs a fix.

## Fixed automatically

- Nothing.

## Careers sites resting

- None.

## Jobs found per source, last runs (oldest first)

| Source | 11-22 05:16 | 11-22 11:38 | 11-22 17:37 | 11-22 23:36 | 11-23 05:39 | 11-23 11:40 | 11-23 17:39 | 11-23 23:31 | 11-24 05:37 | 11-24 11:39 |
|---|---|---|---|---|---|---|---|---|---|---|
| Careers sites | 4291 (52 err) | 4311 (51 err) | 4296 (51 err) | 4314 (50 err) | 4260 (51 err) | 4251 (51 err) | 4259 (51 err) | 4255 (51 err) | 4269 (50 err) | 4267 (50 err) |
| Indeed | 437 | 55 | 144 | 23 | 18 | 128 | 312 | 108 | 58 | 15 |
| LinkedIn | 5165 | 5134 (2 err) | 5137 (2 err) | 5065 (2 err) | 5102 (2 err) | 3747 (10 err) | 5144 (1 err) | 4914 (2 err) | 4942 (2 err) | 4166 (4 err) |
| NHS Jobs | 3583 | 3582 | 3582 | 3581 | 3439 | 3493 | 3590 | 3592 | 3448 | 3491 |
| eFinancialCareers | 4279 | 4248 | 4254 | 4240 | 4271 | 4270 | 4275 | 4279 | 4287 | 4247 |

## Most frequent problems, last 40 runs

- Careers sites: 33 run(s)
- UK sponsorship figures: 7 run(s)
- Indeed: 6 run(s)
- Careers sites | Marsh: 1 run(s)
- Careers sites | Wells Fargo: 1 run(s)
