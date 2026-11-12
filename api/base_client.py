from __future__ import annotations

from typing import Any

import requests


class BaseApiClient:
    """HTTP client that reuses one session for base URL, headers, and auth."""

    def __init__(
        self,
        base_url: str,
        headers: dict[str, str] | None = None,
        timeout: float = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )
        if headers:
            self.session.headers.update(headers)

    def post(self, path: str, json: dict[str, Any] | None = None) -> requests.Response:
        return self.session.post(
            self._url(path),
            json=json,
            timeout=self.timeout,
        )

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"
