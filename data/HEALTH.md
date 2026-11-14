# Quant job scraper: health report

Written by the problem solver (`jobscraper/healer.py`) at the end of every run. Sync this file into the Performance Analizer Claude project to track it there.

Last run: 2026-11-14T11:34:40+00:00

## Status

19 problem(s) need a look, 1 handled automatically.

Jobs in email: 499, new: 20, raw results: 18359, emailed: True.

## Needs a look

- **Careers sites | Apollo Global Management**: failed on 3 runs in a row (last: JSONDecodeError: Expecting value: line 1 column 1 (char 0)). Resting it until 2026-11-17, then it is tried again; if it keeps failing, check its entry in careers_sites_manual.yaml.
- **Careers sites | Brookfield**: failed on 3 runs in a row (last: JSONDecodeError: Expecting value: line 1 column 1 (char 0)). Resting it until 2026-11-17, then it is tried again; if it keeps failing, check its entry in careers_sites_manual.yaml.
- **Careers sites | Citi**: failed on 3 runs in a row (last: JSONDecodeError: Expecting value: line 1 column 1 (char 0)). Resting it until 2026-11-17, then it is tried again; if it keeps failing, check its entry in careers_sites_manual.yaml.
- **Careers sites | FIS**: failed on 3 runs in a row (last: JSONDecodeError: Expecting value: line 1 column 1 (char 0)). Resting it until 2026-11-17, then it is tried again; if it keeps failing, check its entry in careers_sites_manual.yaml.
- **Careers sites | Fifth Third Bank**: failed on 3 runs in a row (last: JSONDecodeError: Expecting value: line 1 column 1 (char 0)). Resting it until 2026-11-17, then it is tried again; if it keeps failing, check its entry in careers_sites_manual.yaml.
- **Careers sites | Fiserv**: failed on 3 runs in a row (last: JSONDecodeError: Expecting value: line 1 column 1 (char 0)). Resting it until 2026-11-17, then it is tried again; if it keeps failing, check its entry in careers_sites_manual.yaml.
- **Careers sites | Franklin Templeton**: failed on 3 runs in a row (last: JSONDecodeError: Expecting value: line 1 column 1 (char 0)). Resting it until 2026-11-17, then it is tried again; if it keeps failing, check its entry in careers_sites_manual.yaml.
- **Careers sites | KeyBank**: failed on 3 runs in a row (last: JSONDecodeError: Expecting value: line 1 column 1 (char 0)). Resting it until 2026-11-17, then it is tried again; if it keeps failing, check its entry in careers_sites_manual.yaml.
- **Careers sites | M&T Bank**: failed on 3 runs in a row (last: JSONDecodeError: Expecting value: line 1 column 1 (char 0)). Resting it until 2026-11-17, then it is tried again; if it keeps failing, check its entry in careers_sites_manual.yaml.
- **Careers sites | Morgan Stanley**: failed on 3 runs in a row (last: JSONDecodeError: Expecting value: line 1 column 1 (char 0)). Resting it until 2026-11-17, then it is tried again; if it keeps failing, check its entry in careers_sites_manual.yaml.
- **Careers sites | Morningstar**: failed on 3 runs in a row (last: JSONDecodeError: Expecting value: line 1 column 1 (char 0)). Resting it until 2026-11-17, then it is tried again; if it keeps failing, check its entry in careers_sites_manual.yaml.
- **Careers sites | PNC**: failed on 3 runs in a row (last: JSONDecodeError: Expecting value: line 1 column 1 (char 0)). Resting it until 2026-11-17, then it is tried again; if it keeps failing, check its entry in careers_sites_manual.yaml.
- **Careers sites | Prudential plc**: failed on 3 runs in a row (last: JSONDecodeError: Expecting value: line 1 column 1 (char 0)). Resting it until 2026-11-17, then it is tried again; if it keeps failing, check its entry in careers_sites_manual.yaml.
- **Careers sites | S&P Global**: failed on 3 runs in a row (last: JSONDecodeError: Expecting value: line 1 column 1 (char 0)). Resting it until 2026-11-17, then it is tried again; if it keeps failing, check its entry in careers_sites_manual.yaml.
- **Careers sites | T. Rowe Price**: failed on 3 runs in a row (last: JSONDecodeError: Expecting value: line 1 column 1 (char 0)). Resting it until 2026-11-17, then it is tried again; if it keeps failing, check its entry in careers_sites_manual.yaml.
- **Careers sites | Travelers**: failed on 3 runs in a row (last: JSONDecodeError: Expecting value: line 1 column 1 (char 0)). Resting it until 2026-11-17, then it is tried again; if it keeps failing, check its entry in careers_sites_manual.yaml.
- **Careers sites | Vanguard**: failed on 3 runs in a row (last: JSONDecodeError: Expecting value: line 1 column 1 (char 0)). Resting it until 2026-11-17, then it is tried again; if it keeps failing, check its entry in careers_sites_manual.yaml.
- **Careers sites | Wellington Management**: failed on 3 runs in a row (last: JSONDecodeError: Expecting value: line 1 column 1 (char 0)). Resting it until 2026-11-17, then it is tried again; if it keeps failing, check its entry in careers_sites_manual.yaml.
- **Indeed**: found 4 jobs; it usually finds about 84. Likely blocked or the site changed its page layout; the run carried on with the other sources. If it repeats next run, its scraper in jobscraper/sources needs a fix.

## Fixed automatically

- **Careers sites**: 1 sites are resting after repeated failures. Skipped this run; each is retried when its rest ends.

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

## Jobs found per source, last runs (oldest first)

| Source | 11-13 17:36 | 11-13 23:35 | 11-14 05:34 | 11-14 11:34 |
|---|---|---|---|---|
| Careers sites | 6435 (1 err) | 5920 (19 err) | 5410 (34 err) | 5408 (33 err) |
| Indeed | 84 | 130 | 30 | 4 |
| LinkedIn | 4802 | 5092 | 5233 | 5065 |
| NHS Jobs | 3624 | 3644 | 3640 | 3636 |
| eFinancialCareers | 4247 | 4229 | 4217 | 4246 |

## Most frequent problems, last 4 runs

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
