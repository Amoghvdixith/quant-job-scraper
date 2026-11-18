# Quant job scraper: health report

Written by the problem solver (`jobscraper/healer.py`) at the end of every run. Sync this file into the Performance Analizer Claude project to track it there.

Last run: 2026-11-18T05:21:53+00:00

## Status

1 problem(s) need a look, 12 handled automatically.

Jobs in email: 322, new: 33, raw results: 17282, emailed: True.

## Needs a look

- **Careers sites**: 37 sites failed in the same run (likely an outage or block at their hosting platform). Not counted towards resting them; they are tried again next run.

## Fixed automatically

- **Careers sites | Houlihan Lokey**: failed (HTTPError: 429 Client Error: Too Many Requests for url: https://hl.wd1.myworkdayjobs.com/wday/cxs/hl/Campus/jobs). Worked on a second try.
- **Careers sites | T. Rowe Price**: failed (HTTPError: 429 Client Error: Too Many Requests for url: https://troweprice.wd5.myworkdayjobs.com/wday/cxs/troweprice/TRowePrice/jobs). Worked on a second try.
- **Careers sites | Vanguard**: failed (HTTPError: 429 Client Error: Too Many Requests for url: https://vanguard.wd5.myworkdayjobs.com/wday/cxs/vanguard/vanguard_external/jobs). Worked on a second try.
- **Careers sites | Wells Fargo**: failed (HTTPError: 429 Client Error: Too Many Requests for url: https://wf.wd1.myworkdayjobs.com/wday/cxs/wf/WellsFargoJobs/jobs). Worked on a second try.
- **Careers sites | Marsh**: came back after a rest. Back in every run.
- **Careers sites | Morningstar**: came back after a rest. Back in every run.
- **Careers sites | Morgan Stanley**: came back after a rest. Back in every run.
- **Careers sites | Prudential plc**: came back after a rest. Back in every run.
- **Careers sites | T. Rowe Price**: came back after a rest. Back in every run.
- **Careers sites | Wellington Management**: came back after a rest. Back in every run.
- **Careers sites | Vanguard**: came back after a rest. Back in every run.
- **Careers sites | Wells Fargo**: came back after a rest. Back in every run.

## Careers sites resting

- None.

## Jobs found per source, last runs (oldest first)

| Source | 11-15 23:29 | 11-16 05:32 | 11-16 12:11 | 11-16 17:48 | 11-16 23:33 | 11-17 05:48 | 11-17 11:49 | 11-17 17:17 | 11-17 23:17 | 11-18 05:21 |
|---|---|---|---|---|---|---|---|---|---|---|
| Careers sites | 5551 (1 err) | 5535 (1 err) | 4265 (29 err) | 4260 (29 err) | 4279 (29 err) | 4254 (50 err) | 4128 (55 err) | 4301 (50 err) | 4295 (50 err) | 4558 (37 err) |
| Indeed | 8 | 117 | 294 | 73 | 60 | 10 | 20 | 318 | 66 | 120 |
| LinkedIn | 4147 | 4800 | 4469 (3 err) | 4614 (1 err) | 4775 | 4184 (1 err) | 4392 | 5191 | 5194 | 5073 |
| NHS Jobs | 3531 | 3197 (1 err) | 3395 | 3556 | 3557 | 3314 | 3383 | 3506 | 3542 | 3291 |
| eFinancialCareers | 4256 | 4257 | 4284 | 4287 | 4264 | 4251 | 4253 | 4235 | 4257 | 4240 |

## Most frequent problems, last 19 runs

- Careers sites: 8 run(s)
- UK sponsorship figures: 7 run(s)
- Indeed: 3 run(s)
- Careers sites | MetLife: 1 run(s)
- Careers sites | Apollo Global Management: 1 run(s)
- Careers sites | Brookfield: 1 run(s)
- Careers sites | Citi: 1 run(s)
- Careers sites | FIS: 1 run(s)
- Careers sites | Fifth Third Bank: 1 run(s)
- Careers sites | Fiserv: 1 run(s)
