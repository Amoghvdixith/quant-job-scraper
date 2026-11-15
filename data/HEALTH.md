# Quant job scraper: health report

Written by the problem solver (`jobscraper/healer.py`) at the end of every run. Sync this file into the Performance Analizer Claude project to track it there.

Last run: 2026-11-15T17:32:16+00:00

## Status

1 problem(s) need a look, 1 handled automatically.

Jobs in email: 480, new: 4, raw results: 18124, emailed: True.

## Needs a look

- **UK sponsorship figures**: failed (RuntimeError: UK CoS figures from Home Office FOI 2025/12841 could not be read (403 Client Error: Forbidden for url: https://www.whatdotheyknow.com/request/r...). The UK people-sponsored column is empty this run. Fix: save the FOI workbook in data/foi/ (see UK_COS_SOURCES in jobscraper/sponsor_registers.py).

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

| Source | 11-13 17:36 | 11-13 23:35 | 11-14 05:34 | 11-14 11:34 | 11-14 17:36 | 11-14 23:33 | 11-15 05:34 | 11-15 11:36 | 11-15 17:32 |
|---|---|---|---|---|---|---|---|---|---|
| Careers sites | 6435 (1 err) | 5920 (19 err) | 5410 (34 err) | 5408 (33 err) | 5831 (2 err) | 5827 | 5820 | 5555 | 5559 |
| Indeed | 84 | 130 | 30 | 4 | 83 | 452 | 45 | 117 | 21 |
| LinkedIn | 4802 | 5092 | 5233 | 5065 | 5183 | 5113 | 5108 | 4991 | 4754 |
| NHS Jobs | 3624 | 3644 | 3640 | 3636 | 3018 (2 err) | 3637 | 3535 | 3521 (1 err) | 3531 |
| eFinancialCareers | 4247 | 4229 | 4217 | 4246 | 4230 | 4231 | 4250 | 4262 | 4259 |

## Most frequent problems, last 9 runs

- UK sponsorship figures: 3 run(s)
- Careers sites | MetLife: 1 run(s)
- Careers sites | Apollo Global Management: 1 run(s)
- Careers sites | Brookfield: 1 run(s)
- Careers sites | Citi: 1 run(s)
- Careers sites | FIS: 1 run(s)
- Careers sites | Fifth Third Bank: 1 run(s)
- Careers sites | Fiserv: 1 run(s)
- Careers sites | Franklin Templeton: 1 run(s)
- Careers sites | KeyBank: 1 run(s)
