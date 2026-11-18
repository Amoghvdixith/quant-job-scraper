# Quant job scraper: health report

Written by the problem solver (`jobscraper/healer.py`) at the end of every run. Sync this file into the Performance Analizer Claude project to track it there.

Last run: 2026-11-18T17:29:26+00:00

## Status

2 problem(s) need a look, 0 handled automatically.

Jobs in email: 354, new: 24, raw results: 17058, emailed: True.

## Needs a look

- **Careers sites**: 51 sites failed in the same run (likely an outage or block at their hosting platform). Not counted towards resting them; they are tried again next run.
- **Indeed**: found 6 jobs; it usually finds about 73. Likely blocked or the site changed its page layout; the run carried on with the other sources. If it repeats next run, its scraper in jobscraper/sources needs a fix.

## Fixed automatically

- Nothing.

## Careers sites resting

- None.

## Jobs found per source, last runs (oldest first)

| Source | 11-16 12:11 | 11-16 17:48 | 11-16 23:33 | 11-17 05:48 | 11-17 11:49 | 11-17 17:17 | 11-17 23:17 | 11-18 05:21 | 11-18 11:32 | 11-18 17:29 |
|---|---|---|---|---|---|---|---|---|---|---|
| Careers sites | 4265 (29 err) | 4260 (29 err) | 4279 (29 err) | 4254 (50 err) | 4128 (55 err) | 4301 (50 err) | 4295 (50 err) | 4558 (37 err) | 4288 (50 err) | 4280 (51 err) |
| Indeed | 294 | 73 | 60 | 10 | 20 | 318 | 66 | 120 | 22 | 6 |
| LinkedIn | 4469 (3 err) | 4614 (1 err) | 4775 | 4184 (1 err) | 4392 | 5191 | 5194 | 5073 | 4973 (1 err) | 4997 |
| NHS Jobs | 3395 | 3556 | 3557 | 3314 | 3383 | 3506 | 3542 | 3291 | 3342 | 3549 |
| eFinancialCareers | 4284 | 4287 | 4264 | 4251 | 4253 | 4235 | 4257 | 4240 | 4226 | 4226 |

## Most frequent problems, last 21 runs

- Careers sites: 10 run(s)
- UK sponsorship figures: 7 run(s)
- Indeed: 4 run(s)
- Careers sites | MetLife: 1 run(s)
- Careers sites | Apollo Global Management: 1 run(s)
- Careers sites | Brookfield: 1 run(s)
- Careers sites | Citi: 1 run(s)
- Careers sites | FIS: 1 run(s)
- Careers sites | Fifth Third Bank: 1 run(s)
- Careers sites | Fiserv: 1 run(s)
