# Quant job scraper: health report

Written by the problem solver (`jobscraper/healer.py`) at the end of every run. Sync this file into the Performance Analizer Claude project to track it there.

Last run: 2026-11-16T23:33:49+00:00

## Status

1 problem(s) need a look, 1 handled automatically.

Jobs in email: 435, new: 16, raw results: 16935, emailed: True.

## Needs a look

- **Careers sites**: 29 sites failed in the same run (likely an outage or block at their hosting platform). Not counted towards resting them; they are tried again next run.

## Fixed automatically

- **Careers sites**: 21 sites are resting after repeated failures. Skipped this run; each is retried when its rest ends.

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

| Source | 11-14 17:36 | 11-14 23:33 | 11-15 05:34 | 11-15 11:36 | 11-15 17:32 | 11-15 23:29 | 11-16 05:32 | 11-16 12:11 | 11-16 17:48 | 11-16 23:33 |
|---|---|---|---|---|---|---|---|---|---|---|
| Careers sites | 5831 (2 err) | 5827 | 5820 | 5555 | 5559 | 5551 (1 err) | 5535 (1 err) | 4265 (29 err) | 4260 (29 err) | 4279 (29 err) |
| Indeed | 83 | 452 | 45 | 117 | 21 | 8 | 117 | 294 | 73 | 60 |
| LinkedIn | 5183 | 5113 | 5108 | 4991 | 4754 | 4147 | 4800 | 4469 (3 err) | 4614 (1 err) | 4775 |
| NHS Jobs | 3018 (2 err) | 3637 | 3535 | 3521 (1 err) | 3531 | 3531 | 3197 (1 err) | 3395 | 3556 | 3557 |
| eFinancialCareers | 4230 | 4231 | 4250 | 4262 | 4259 | 4256 | 4257 | 4284 | 4287 | 4264 |

## Most frequent problems, last 14 runs

- UK sponsorship figures: 7 run(s)
- Careers sites: 3 run(s)
- Indeed: 2 run(s)
- Careers sites | MetLife: 1 run(s)
- Careers sites | Apollo Global Management: 1 run(s)
- Careers sites | Brookfield: 1 run(s)
- Careers sites | Citi: 1 run(s)
- Careers sites | FIS: 1 run(s)
- Careers sites | Fifth Third Bank: 1 run(s)
- Careers sites | Fiserv: 1 run(s)
