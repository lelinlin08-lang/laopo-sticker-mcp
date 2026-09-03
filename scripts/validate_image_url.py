#!/usr/bin/env python3
"""Check the properties that make a public image URL suitable for chat rendering."""

from __future__ import annotations

import argparse
import sys
from urllib.parse import urlparse

import httpx

ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif", "image/svg+xml"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    args = parser.parse_args()

    parsed = urlparse(args.url)
    failures: list[str] = []
    if parsed.scheme != "https":
        failures.append("URL is not HTTPS")
    if not parsed.netloc:
        failures.append("URL has no public hostname")

    try:
        with httpx.Client(timeout=20, follow_redirects=False) as client:
            response = client.get(args.url, headers={"Accept": "image/*"})
    except httpx.HTTPError as exc:
        raise SystemExit(f"FAIL network error: {exc}") from exc

    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
    if response.status_code != 200:
        failures.append(f"HTTP status is {response.status_code}, expected 200 without redirect")
    if content_type not in ALLOWED_TYPES:
        failures.append(f"Content-Type is {content_type or 'missing'}")
    if response.headers.get("content-disposition", "").lower().startswith("attachment"):
        failures.append("Content-Disposition forces a download")
    if not response.content:
        failures.append("Response body is empty")

    print(f"status={response.status_code}")
    print(f"content_type={content_type or 'missing'}")
    print(f"bytes={len(response.content)}")
    print(f"redirect={response.is_redirect}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        raise SystemExit(1)
    print("PASS: URL is a direct HTTPS image response")


if __name__ == "__main__":
    main()
