# Quant job scraper: health report

Written by the problem solver (`jobscraper/healer.py`) at the end of every run. Sync this file into the Performance Analizer Claude project to track it there.

Last run: 2026-11-14T17:36:28+00:00

## Status

2 problem(s) need a look, 1 handled automatically.

Jobs in email: 525, new: 26, raw results: 18345, emailed: True.

## Needs a look

- **Careers sites | Marsh**: failed on 3 runs in a row (last: JSONDecodeError: Expecting value: line 1 column 1 (char 0)). Resting it until 2026-11-17, then it is tried again; if it keeps failing, check its entry in careers_sites_manual.yaml.
- **Careers sites | Wells Fargo**: failed on 3 runs in a row (last: JSONDecodeError: Expecting value: line 1 column 1 (char 0)). Resting it until 2026-11-17, then it is tried again; if it keeps failing, check its entry in careers_sites_manual.yaml.

## Fixed automatically

- **Careers sites**: 19 sites are resting after repeated failures. Skipped this run; each is retried when its rest ends.

## Careers sites resting

- Apollo Global Management: until 2026-11-17 (last error: JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- Brookfield: until 2026-11-17 (last error: JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- Citi: until 2026-11-17 (last error: JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- FIS: until 2026-11-17 (last error: JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- Fifth Third Bank: until 2026-11-17 (last error: JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- Fiserv: until 2026-11-17 (last error: JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- Franklin Templeton: until 2026-11-17 (last error: JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- KeyBank: until 2026-11-17 (last error: JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- M&T Bank: until 2026-11-17 (last error: JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- Marsh: until 2026-11-17 (last error: JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- MetLife: until 2026-11-17 (last error: HTTPError: 404 Client Error: Not Found for url: https://api.lever.co/v0/postings/metlife?mode=json)
- Morgan Stanley: until 2026-11-17 (last error: JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- Morningstar: until 2026-11-17 (last error: JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- PNC: until 2026-11-17 (last error: JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- Prudential plc: until 2026-11-17 (last error: JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- S&P Global: until 2026-11-17 (last error: JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- T. Rowe Price: until 2026-11-17 (last error: JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- Travelers: until 2026-11-17 (last error: JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- Vanguard: until 2026-11-17 (last error: JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- Wellington Management: until 2026-11-17 (last error: JSONDecodeError: Expecting value: line 1 column 1 (char 0))
- Wells Fargo: until 2026-11-17 (last error: JSONDecodeError: Expecting value: line 1 column 1 (char 0))

## Jobs found per source, last runs (oldest first)

| Source | 11-13 17:36 | 11-13 23:35 | 11-14 05:34 | 11-14 11:34 | 11-14 17:36 |
|---|---|---|---|---|---|
| Careers sites | 6435 (1 err) | 5920 (19 err) | 5410 (34 err) | 5408 (33 err) | 5831 (2 err) |
| Indeed | 84 | 130 | 30 | 4 | 83 |
| LinkedIn | 4802 | 5092 | 5233 | 5065 | 5183 |
| NHS Jobs | 3624 | 3644 | 3640 | 3636 | 3018 (2 err) |
| eFinancialCareers | 4247 | 4229 | 4217 | 4246 | 4230 |

## Most frequent problems, last 5 runs

- Careers sites | MetLife: 1 run(s)
- Careers sites | Apollo Global Management: 1 run(s)
- Careers sites | Brookfield: 1 run(s)
- Careers sites | Citi: 1 run(s)
- Careers sites | FIS: 1 run(s)
- Careers sites | Fifth Third Bank: 1 run(s)
- Careers sites | Fiserv: 1 run(s)
- Careers sites | Franklin Templeton: 1 run(s)
- Careers sites | KeyBank: 1 run(s)
- Careers sites | M&T Bank: 1 run(s)
