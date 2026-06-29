"""Brickognize REST client.

One part per image. POSTs a multipart image to the predict endpoint and normalises
the response into our `BrickognizeResult` schema. Free API, no auth.

The exact response field names should be confirmed against
https://api.brickognize.com/docs — this client parses defensively (keeping the raw
payload) so a field-name change degrades to "raw is still there" rather than a crash.
Known shape at time of writing: the response has an ``items`` list, each item with
``id``, ``name``, ``category``, ``type``, ``score``, ``img_url``.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import requests

from data.schema import BrickognizeItem, BrickognizeResult

# Brickognize wants a real-ish browser content-type on the file part.
_DEFAULT_URL = "https://api.brickognize.com/predict/"
# Field name for the uploaded image in the multipart form.
_FILE_FIELD = "query_image"


class BrickognizeError(RuntimeError):
    pass


def _parse_item(d: dict) -> BrickognizeItem:
    return BrickognizeItem(
        id=d.get("id"),
        name=d.get("name"),
        category=d.get("category"),
        type=d.get("type"),
        score=d.get("score"),
        img_url=d.get("img_url"),
        raw=d,
    )


def _parse_response(payload: dict) -> BrickognizeResult:
    items_raw = payload.get("items") or []
    items = [_parse_item(d) for d in items_raw if isinstance(d, dict)]
    # Brickognize returns items already sorted best-first; fall back to max score.
    best: Optional[BrickognizeItem] = None
    if items:
        best = max(items, key=lambda it: (it.score is not None, it.score or 0.0))
    return BrickognizeResult(best=best, items=items, raw=payload)


class BrickognizeClient:
    def __init__(
        self,
        url: str = _DEFAULT_URL,
        *,
        timeout_s: float = 30.0,
        max_retries: int = 4,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.url = url
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.session = session or requests.Session()

    def predict_path(self, image_path: str | Path) -> BrickognizeResult:
        image_path = Path(image_path)
        with image_path.open("rb") as f:
            return self.predict_bytes(f.read(), filename=image_path.name)

    def predict_bytes(self, image_bytes: bytes, *, filename: str = "crop.jpg") -> BrickognizeResult:
        content_type = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
        last_err: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                resp = self.session.post(
                    self.url,
                    files={_FILE_FIELD: (filename, image_bytes, content_type)},
                    timeout=self.timeout_s,
                )
            except requests.RequestException as e:
                last_err = e
                self._backoff(attempt)
                continue

            # Retry on rate-limit / transient server errors; honour Retry-After.
            if resp.status_code in (429, 500, 502, 503, 504):
                last_err = BrickognizeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
                self._backoff(attempt, retry_after=resp.headers.get("Retry-After"))
                continue

            if not resp.ok:
                raise BrickognizeError(f"HTTP {resp.status_code}: {resp.text[:200]}")

            try:
                return _parse_response(resp.json())
            except ValueError as e:
                raise BrickognizeError(f"Non-JSON response: {resp.text[:200]}") from e

        raise BrickognizeError(
            f"Brickognize request failed after {self.max_retries} attempts"
        ) from last_err

    def _backoff(self, attempt: int, retry_after: str | None = None) -> None:
        if retry_after:
            try:
                time.sleep(min(float(retry_after), 60.0))
                return
            except ValueError:
                pass
        time.sleep(min(2.0**attempt, 30.0))  # exponential: 1, 2, 4, 8, ...
