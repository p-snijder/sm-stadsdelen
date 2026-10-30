"""Canonical URL normalization for crawl and JSON matching."""

from __future__ import annotations

from urllib.parse import urljoin, urlparse, urlunparse

CANONICAL_HOST = "www.amsterdam.nl"


def normalize(url: str, *, base: str | None = None) -> str:
    """Return a canonical https URL for equality matching.

    Rules applied after optional resolution against ``base``:

    - ``http`` and ``https`` are normalized to ``https``.
    - Host is lowercased; bare ``amsterdam.nl`` becomes ``www.amsterdam.nl``.
    - Fragments and query strings are removed entirely.
    - Path segments are lowercased; duplicate slashes are collapsed.
    - Trailing slashes are removed except for the root path ``/``.
    """
    if not isinstance(url, str) or not url.strip():
        raise ValueError("URL must be a non-empty string")

    raw = url.strip()
    if base is not None:
        raw = urljoin(base, raw)

    if raw.startswith("//"):
        raw = f"https:{raw}"

    parsed = urlparse(raw)
    if not parsed.scheme and not parsed.netloc:
        raise ValueError("Relative URL requires a base URL")

    if parsed.scheme and parsed.scheme not in ("http", "https"):
        raise ValueError("Only http and https URLs are supported")

    host = parsed.hostname
    if not host:
        raise ValueError("URL must include a host")

    host = host.lower()
    if host == "amsterdam.nl":
        host = CANONICAL_HOST

    path = _collapse_path(parsed.path)
    path = path.lower()
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    return urlunparse(("https", host, path, "", "", ""))


def resolve(url: str, base: str) -> str:
    """Resolve a possibly relative URL against ``base``, then normalize."""
    if not base.strip():
        raise ValueError("Base URL must be a non-empty string")
    return normalize(url, base=base)


def _collapse_path(path: str) -> str:
    if not path:
        return "/"
    segments = [segment for segment in path.split("/") if segment]
    if not segments:
        return "/"
    return "/" + "/".join(segments)
