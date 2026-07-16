#!/usr/bin/env python3
"""Robust generic REST client: auth + retries (backoff+jitter) + Retry-After + pagination.

Zero hard deps beyond httpx and tenacity:
    pip install "httpx>=0.27" "tenacity>=8.2"

Use as a library (import ApiClient) or CLI smoke test:
    python api_client.py https://api.github.com/repositories --paginate --max-pages 2
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import time
from typing import Any, Callable, Iterator

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
    before_sleep_log,
)

log = logging.getLogger("api_client")

# Status codes worth a retry: throttling + transient server faults.
RETRY_STATUS = {429, 500, 502, 503, 504}
DEFAULT_ATTEMPTS = 5
DEFAULT_TIMEOUT = 30.0


def _should_retry(exc: BaseException) -> bool:
    if isinstance(exc, (httpx.TransportError, httpx.TimeoutException)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRY_STATUS
    return False


def build_auth_headers(
    *,
    bearer: str | None = None,
    api_key: str | None = None,
    api_key_header: str = "X-API-Key",
) -> dict[str, str]:
    """Return auth headers. Never hardcode secrets — pass from env."""
    headers: dict[str, str] = {}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    if api_key:
        headers[api_key_header] = api_key
    return headers


class ApiClient:
    """Thin wrapper over httpx.Client with disciplined retries + pagination."""

    def __init__(
        self,
        base_url: str = "",
        *,
        headers: dict[str, str] | None = None,
        attempts: int = DEFAULT_ATTEMPTS,
        timeout: float = DEFAULT_TIMEOUT,
        client: httpx.Client | None = None,
    ) -> None:
        self.attempts = attempts
        self._client = client or httpx.Client(
            base_url=base_url,
            headers={"Accept": "application/json", **(headers or {})},
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ApiClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def request(self, method: str, url: str, **kw: Any) -> httpx.Response:
        # tenacity wraps a fresh closure each call so `attempts` is honoured.
        @retry(
            stop=stop_after_attempt(self.attempts),
            wait=wait_exponential_jitter(initial=1, max=30),
            retry=retry_if_exception(_should_retry),
            before_sleep=before_sleep_log(log, logging.WARNING),
            reraise=True,
        )
        def _do() -> httpx.Response:
            resp = self._client.request(method, url, **kw)
            # Honour server-dictated backoff before raising to trigger retry.
            if resp.status_code in RETRY_STATUS:
                retry_after = resp.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    time.sleep(min(int(retry_after), 60))
            resp.raise_for_status()
            return resp

        return _do()

    def get_json(self, url: str, **kw: Any) -> Any:
        return self.request("GET", url, **kw).json()

    def paginate(
        self,
        url: str,
        *,
        next_link: Callable[[httpx.Response], str | None] | None = None,
        params: dict[str, Any] | None = None,
        max_pages: int = 50,
        **kw: Any,
    ) -> Iterator[httpx.Response]:
        """Yield pages. Defaults to RFC-5988 Link rel="next" (GitHub-style)."""
        next_link = next_link or _link_header_next
        page = 0
        current: str | None = url
        first = True
        while current and page < max_pages:
            resp = self.request("GET", current, params=params if first else None, **kw)
            yield resp
            page += 1
            first = False
            current = next_link(resp)


def _link_header_next(resp: httpx.Response) -> str | None:
    return resp.links.get("next", {}).get("url")


def _cli() -> None:
    ap = argparse.ArgumentParser(description="Smoke-test the robust API client.")
    ap.add_argument("url")
    ap.add_argument("--bearer-env", help="env var name holding a bearer token")
    ap.add_argument("--paginate", action="store_true")
    ap.add_argument("--max-pages", type=int, default=3)
    args = ap.parse_args()
    logging.basicConfig(level=logging.WARNING)

    bearer = os.environ.get(args.bearer_env) if args.bearer_env else None
    with ApiClient(headers=build_auth_headers(bearer=bearer)) as api:
        if args.paginate:
            total = 0
            for resp in api.paginate(args.url, max_pages=args.max_pages):
                body = resp.json()
                n = len(body) if isinstance(body, list) else 1
                total += n
                print(f"page {resp.url} -> {n} items")
            print(f"total items: {total}")
        else:
            print(json.dumps(api.get_json(args.url), indent=2)[:2000])


if __name__ == "__main__":
    _cli()
