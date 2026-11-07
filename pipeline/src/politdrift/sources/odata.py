"""Minimal client for the OData v3 web services of the Parliamentary Services (ws.parlament.ch).

Polite by design: one shared rate limit across threads, retries with backoff on transient
errors, and no requests without a Language filter (KONZEPT 3.1).
"""

from __future__ import annotations

import datetime as dt
import re
import threading
import time
from collections.abc import Iterator, Mapping
from typing import Any, cast

import httpx

BASE_URL = "https://ws.parlament.ch/odata.svc"
USER_AGENT = "politdrift-pipeline (+https://github.com/michschl/politdrift)"
PAGE_SIZE = 1000  # server maximum for $top

_DATE_RE = re.compile(r"^/Date\((-?\d+)([+-]\d{4})?\)/$")

Row = dict[str, Any]


class ODataError(RuntimeError):
    pass


def parse_date(value: str | None) -> dt.datetime | None:
    """Parse OData v3 '/Date(ms)/' or '/Date(ms+hhmm)/' into an aware UTC datetime."""
    if value is None:
        return None
    m = _DATE_RE.match(value)
    if not m:
        raise ValueError(f"not an OData date: {value!r}")
    return dt.datetime.fromtimestamp(int(m.group(1)) / 1000, tz=dt.UTC)


class RateLimiter:
    """At most one request start per `interval` seconds, shared by all threads."""

    def __init__(self, interval: float) -> None:
        self._interval = interval
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delay = self._next - now
            self._next = max(now, self._next) + self._interval
        if delay > 0:
            time.sleep(delay)


class ODataClient:
    def __init__(
        self,
        base_url: str = BASE_URL,
        *,
        client: httpx.Client | None = None,
        min_interval: float = 0.1,
        retries: int = 3,
        timeout: float = 120.0,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._client = client or httpx.Client(
            timeout=timeout, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
        )
        self._limiter = RateLimiter(min_interval)
        self._retries = retries

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> ODataClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _get(self, entity: str, params: Mapping[str, str]) -> list[Row]:
        url = f"{self._base}/{entity}"
        query = {"$format": "json", **params}
        last: Exception | None = None
        for attempt in range(self._retries + 1):
            self._limiter.wait()
            try:
                resp = self._client.get(url, params=query)
                if resp.status_code >= 500:
                    raise ODataError(f"{entity}: HTTP {resp.status_code}")
                resp.raise_for_status()
                payload: Any = resp.json()
                data: Any = payload["d"]
                if isinstance(data, dict):
                    data = cast(dict[str, Any], data)["results"]
                return [_strip(cast(Row, r)) for r in cast(list[Any], data)]
            except (httpx.TransportError, ODataError, ValueError, KeyError) as err:
                last = err
                if attempt < self._retries:
                    time.sleep(2**attempt)
        raise ODataError(f"{entity} {dict(params)} failed after retries: {last}") from last

    def query(
        self,
        entity: str,
        filter_: str,
        *,
        select: list[str] | None = None,
        orderby: str = "ID",
        language: str = "DE",
    ) -> Iterator[Row]:
        """Yield all rows matching `filter_`, paging with $top/$skip in stable ID order."""
        skip = 0
        while True:
            params = {
                "$filter": f"Language eq '{language}' and ({filter_})",
                "$orderby": orderby,
                "$top": str(PAGE_SIZE),
                "$skip": str(skip),
            }
            if select:
                params["$select"] = ",".join(select)
            rows = self._get(entity, params)
            yield from rows
            if len(rows) < PAGE_SIZE:
                return
            skip += PAGE_SIZE


def _strip(row: Row) -> Row:
    return {k: v for k, v in row.items() if k != "__metadata" and not isinstance(v, dict)}
