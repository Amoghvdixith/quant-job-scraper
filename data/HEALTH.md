# Quant job scraper: health report

Written by the problem solver (`jobscraper/healer.py`) at the end of every run. Sync this file into the Performance Analizer Claude project to track it there.

Last run: 2026-11-21T17:41:25+00:00

## Status

2 problem(s) need a look, 0 handled automatically.

Jobs in email: 328, new: 14, raw results: 16497, emailed: True.

## Needs a look

- **Careers sites**: 52 sites failed in the same run (likely an outage or block at their hosting platform). Not counted towards resting them; they are tried again next run.
- **Indeed**: found 13 jobs; it usually finds about 71. Likely blocked or the site changed its page layout; the run carried on with the other sources. If it repeats next run, its scraper in jobscraper/sources needs a fix.

## Fixed automatically

- Nothing.

## Careers sites resting

- None.

## Jobs found per source, last runs (oldest first)

| Source | 11-19 11:28 | 11-19 17:34 | 11-19 23:30 | 11-20 05:21 | 11-20 11:31 | 11-20 17:29 | 11-20 23:30 | 11-21 05:28 | 11-21 11:39 | 11-21 17:41 |
|---|---|---|---|---|---|---|---|---|---|---|
| Careers sites | 4265 (51 err) | 4245 (51 err) | 4245 (51 err) | 4241 (51 err) | 4258 (51 err) | 4267 (51 err) | 4313 (50 err) | 4286 (52 err) | 4288 (52 err) | 4289 (52 err) |
| Indeed | 53 | 138 | 24 | 12 | 59 | 428 | 71 | 161 | 31 | 13 |
| LinkedIn | 3105 (4 err) | 3752 (1 err) | 3859 (1 err) | 4242 (1 err) | 2785 (4 err) | 3048 (4 err) | 2300 (9 err) | 2667 (5 err) | 3816 (2 err) | 4258 (4 err) |
| NHS Jobs | 3447 | 3572 | 3574 | 3566 | 3600 | 3681 | 3686 | 3683 | 3685 | 3684 |
| eFinancialCareers | 4235 | 4237 | 4235 | 4248 | 4284 | 4287 | 4275 | 4285 | 4279 | 4253 |

## Most frequent problems, last 33 runs

- Careers sites: 22 run(s)
- UK sponsorship figures: 7 run(s)
- Indeed: 6 run(s)
- Careers sites | MetLife: 1 run(s)
- Careers sites | Apollo Global Management: 1 run(s)
- Careers sites | Brookfield: 1 run(s)
- Careers sites | Citi: 1 run(s)
- Careers sites | FIS: 1 run(s)
- Careers sites | Fifth Third Bank: 1 run(s)
- Careers sites | Fiserv: 1 run(s)
