# Quant job scraper: health report

Written by the problem solver (`jobscraper/healer.py`) at the end of every run. Sync this file into the Performance Analizer Claude project to track it there.

Last run: 2026-11-17T05:48:57+00:00

## Status

2 problem(s) need a look, 0 handled automatically.

Jobs in email: 315, new: 5, raw results: 16013, emailed: True.

## Needs a look

- **Careers sites**: 50 sites failed in the same run (likely an outage or block at their hosting platform). Not counted towards resting them; they are tried again next run.
- **Indeed**: found 10 jobs; it usually finds about 83. Likely blocked or the site changed its page layout; the run carried on with the other sources. If it repeats next run, its scraper in jobscraper/sources needs a fix.

## Fixed automatically

- Nothing.

## Careers sites resting

- None.

## Jobs found per source, last runs (oldest first)

| Source | 11-14 23:33 | 11-15 05:34 | 11-15 11:36 | 11-15 17:32 | 11-15 23:29 | 11-16 05:32 | 11-16 12:11 | 11-16 17:48 | 11-16 23:33 | 11-17 05:48 |
|---|---|---|---|---|---|---|---|---|---|---|
| Careers sites | 5827 | 5820 | 5555 | 5559 | 5551 (1 err) | 5535 (1 err) | 4265 (29 err) | 4260 (29 err) | 4279 (29 err) | 4254 (50 err) |
| Indeed | 452 | 45 | 117 | 21 | 8 | 117 | 294 | 73 | 60 | 10 |
| LinkedIn | 5113 | 5108 | 4991 | 4754 | 4147 | 4800 | 4469 (3 err) | 4614 (1 err) | 4775 | 4184 (1 err) |
| NHS Jobs | 3637 | 3535 | 3521 (1 err) | 3531 | 3531 | 3197 (1 err) | 3395 | 3556 | 3557 | 3314 |
| eFinancialCareers | 4231 | 4250 | 4262 | 4259 | 4256 | 4257 | 4284 | 4287 | 4264 | 4251 |

## Most frequent problems, last 15 runs

- UK sponsorship figures: 7 run(s)
- Careers sites: 4 run(s)
- Indeed: 3 run(s)
- Careers sites | MetLife: 1 run(s)
- Careers sites | Apollo Global Management: 1 run(s)
- Careers sites | Brookfield: 1 run(s)
- Careers sites | Citi: 1 run(s)
- Careers sites | FIS: 1 run(s)
- Careers sites | Fifth Third Bank: 1 run(s)
- Careers sites | Fiserv: 1 run(s)
