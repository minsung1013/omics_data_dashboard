"""Base classes and shared HTTP helpers for source adapters.

Each adapter subclasses SourceAdapter and implements `fetch_since(since, cap)`,
returning a list of *raw* record dicts. Adapters fill in as many fields as the
source exposes; harvest.py then applies uniform modality/cancer/license tagging
(see tagging.py), so adapters stay small.

Raw record dict fields (all optional except id, name, source, url):
    id, name, source, url, organism, size, owner, organization,
    description, published_date, updated_date, license_raw, access_level,
    assay_text   -> free-text hints used for modality/platform detection
    platform      -> explicit platform label if the source gives one
"""
import time
from abc import ABC, abstractmethod

import requests


class RateLimitedSession:
    """A requests.Session wrapper with a minimum delay between calls + retries."""

    def __init__(self, min_interval=0.34, retries=3, timeout=30, headers=None):
        self.min_interval = min_interval
        self.retries = retries
        self.timeout = timeout
        self._last = 0.0
        self.session = requests.Session()
        self.session.headers.update(
            headers or {"User-Agent": "omics-data-dashboard/0.1 (+github.com/minsung1013)"}
        )

    def _wait(self):
        elapsed = time.time() - self._last
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last = time.time()

    def get_json(self, url, params=None, **kw):
        return self._request("GET", url, params=params, **kw).json()

    def get(self, url, params=None, **kw):
        return self._request("GET", url, params=params, **kw)

    def post_json(self, url, json=None, **kw):
        return self._request("POST", url, json=json, **kw).json()

    def _request(self, method, url, **kw):
        kw.setdefault("timeout", self.timeout)
        last_err = None
        for attempt in range(self.retries):
            self._wait()
            try:
                resp = self.session.request(method, url, **kw)
                if resp.status_code in (429, 500, 502, 503, 504):
                    raise requests.HTTPError(f"{resp.status_code} from {url}")
                resp.raise_for_status()
                return resp
            except Exception as e:  # noqa: BLE001 - broad retry on transient errors
                last_err = e
                time.sleep(1.5 * (attempt + 1))
        raise last_err


class SourceAdapter(ABC):
    """Base class for a single data source."""

    name = "base"

    def __init__(self, session=None, min_interval=0.34):
        self.http = session or RateLimitedSession(min_interval=min_interval)

    @abstractmethod
    def fetch_since(self, since, cap):
        """Return a list of raw record dicts added/updated on or after `since`.

        `since` is a datetime.date; `cap` is the max number of records to return.
        """
        raise NotImplementedError
