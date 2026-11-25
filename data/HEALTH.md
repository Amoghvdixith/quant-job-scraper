# Quant job scraper: health report

Written by the problem solver (`jobscraper/healer.py`) at the end of every run. Sync this file into the Performance Analizer Claude project to track it there.

Last run: 2026-11-25T23:25:28+00:00

## Status

2 problem(s) need a look, 0 handled automatically.

Jobs in email: 264, new: 13, raw results: 17322, emailed: True.

## Needs a look

- **Careers sites**: 51 sites failed in the same run (likely an outage or block at their hosting platform). Not counted towards resting them; they are tried again next run.
- **Indeed**: found 8 jobs; it usually finds about 108. Likely blocked or the site changed its page layout; the run carried on with the other sources. If it repeats next run, its scraper in jobscraper/sources needs a fix.

## Fixed automatically

- Nothing.

## Careers sites resting

- None.

## Jobs found per source, last runs (oldest first)

| Source | 11-23 17:39 | 11-23 23:31 | 11-24 05:37 | 11-24 11:39 | 11-24 17:40 | 11-24 23:26 | 11-25 05:40 | 11-25 11:41 | 11-25 17:31 | 11-25 23:25 |
|---|---|---|---|---|---|---|---|---|---|---|
| Careers sites | 4259 (51 err) | 4255 (51 err) | 4269 (50 err) | 4267 (50 err) | 4254 (51 err) | 4278 (51 err) | 4266 (51 err) | 4265 (51 err) | 4286 (51 err) | 4305 (51 err) |
| Indeed | 312 | 108 | 58 | 15 | 23 | 368 | 89 | 162 | 25 | 8 |
| LinkedIn | 5144 (1 err) | 4914 (2 err) | 4942 (2 err) | 4166 (4 err) | 4664 (1 err) | 4371 | 4067 (5 err) | 3534 (5 err) | 4612 (2 err) | 5143 (1 err) |
| NHS Jobs | 3590 | 3592 | 3448 | 3491 | 3592 | 3594 | 3414 | 3467 | 3599 | 3602 |
| eFinancialCareers | 4275 | 4279 | 4287 | 4247 | 4248 | 4241 | 4242 | 4251 | 4261 | 4264 |

## Most frequent problems, last 40 runs

- Careers sites: 39 run(s)
- Indeed: 6 run(s)
- UK sponsorship figures: 3 run(s)
