# Quant job scraper: health report

Written by the problem solver (`jobscraper/healer.py`) at the end of every run. Sync this file into the Performance Analizer Claude project to track it there.

Last run: 2026-11-20T05:21:15+00:00

## Status

2 problem(s) need a look, 0 handled automatically.

Jobs in email: 284, new: 4, raw results: 16309, emailed: True.

## Needs a look

- **Careers sites**: 51 sites failed in the same run (likely an outage or block at their hosting platform). Not counted towards resting them; they are tried again next run.
- **Indeed**: found 12 jobs; it usually finds about 66. Likely blocked or the site changed its page layout; the run carried on with the other sources. If it repeats next run, its scraper in jobscraper/sources needs a fix.

## Fixed automatically

- Nothing.

## Careers sites resting

- None.

## Jobs found per source, last runs (oldest first)

| Source | 11-17 23:17 | 11-18 05:21 | 11-18 11:32 | 11-18 17:29 | 11-18 23:30 | 11-19 05:20 | 11-19 11:28 | 11-19 17:34 | 11-19 23:30 | 11-20 05:21 |
|---|---|---|---|---|---|---|---|---|---|---|
| Careers sites | 4295 (50 err) | 4558 (37 err) | 4288 (50 err) | 4280 (51 err) | 4279 (51 err) | 4260 (51 err) | 4265 (51 err) | 4245 (51 err) | 4245 (51 err) | 4241 (51 err) |
| Indeed | 66 | 120 | 22 | 6 | 34 | 371 | 53 | 138 | 24 | 12 |
| LinkedIn | 5194 | 5073 | 4973 (1 err) | 4997 | 5200 | 5155 | 3105 (4 err) | 3752 (1 err) | 3859 (1 err) | 4242 (1 err) |
| NHS Jobs | 3542 | 3291 | 3342 | 3549 | 3555 | 3376 | 3447 | 3572 | 3574 | 3566 |
| eFinancialCareers | 4257 | 4240 | 4226 | 4226 | 4230 | 4219 | 4235 | 4237 | 4235 | 4248 |

## Most frequent problems, last 27 runs

- Careers sites: 16 run(s)
- UK sponsorship figures: 7 run(s)
- Indeed: 5 run(s)
- Careers sites | MetLife: 1 run(s)
- Careers sites | Apollo Global Management: 1 run(s)
- Careers sites | Brookfield: 1 run(s)
- Careers sites | Citi: 1 run(s)
- Careers sites | FIS: 1 run(s)
- Careers sites | Fifth Third Bank: 1 run(s)
- Careers sites | Fiserv: 1 run(s)
