# Quant job scraper: health report

Written by the problem solver (`jobscraper/healer.py`) at the end of every run. Sync this file into the Performance Analizer Claude project to track it there.

Last run: 2026-11-14T05:34:58+00:00

## Status

1 problem(s) need a look, 0 handled automatically.

Jobs in email: 479, new: 20, raw results: 18530, emailed: True.

## Needs a look

- **Careers sites | MetLife**: failed on 3 runs in a row (last: HTTPError: 404 Client Error: Not Found for url: https://api.lever.co/v0/postings/metlife?mode=json). Resting it until 2026-11-17, then it is tried again; if it keeps failing, check its entry in careers_sites_manual.yaml.

## Fixed automatically

- Nothing.

## Careers sites resting

- MetLife: until 2026-11-17 (last error: HTTPError: 404 Client Error: Not Found for url: https://api.lever.co/v0/postings/metlife?mode=json)

## Jobs found per source, last runs (oldest first)

| Source | 11-13 17:36 | 11-13 23:35 | 11-14 05:34 |
|---|---|---|---|
| Careers sites | 6435 (1 err) | 5920 (19 err) | 5410 (34 err) |
| Indeed | 84 | 130 | 30 |
| LinkedIn | 4802 | 5092 | 5233 |
| NHS Jobs | 3624 | 3644 | 3640 |
| eFinancialCareers | 4247 | 4229 | 4217 |

## Most frequent problems, last 3 runs

- Careers sites | MetLife: 1 run(s)
