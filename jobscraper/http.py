from __future__ import annotations

import logging
import random
import time

import requests

log = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
]


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-GB,en;q=0.9",
    })
    return s


def polite_get(s: requests.Session, url: str, *, delay=(1.5, 3.5), retries=3, **kwargs) -> requests.Response | None:
    """GET with a random pause before each request and backoff on 429/5xx."""
    for attempt in range(retries):
        time.sleep(random.uniform(*delay))
        try:
            r = s.get(url, timeout=30, **kwargs)
        except requests.RequestException as e:
            log.warning("GET %s failed: %s", url, e)
            continue
        if r.status_code == 200:
            return r
        if r.status_code in (429, 500, 502, 503, 999):
            wait = 10 * (attempt + 1)
            log.warning("GET %s -> %s, waiting %ss", url, r.status_code, wait)
            time.sleep(wait)
            continue
        log.warning("GET %s -> %s", url, r.status_code)
        return None
    return None
