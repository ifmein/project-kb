"""Shared helpers: ID generation, timestamps."""

from __future__ import annotations

import secrets
import time


def make_id(prefix: str) -> str:
    """Generate a unique ID like ``proj_XyZaBcDe``."""
    return f"{prefix}_{secrets.token_urlsafe(8)}"


def now() -> float:
    """Current Unix timestamp."""
    return time.time()


def fmt_ts(ts: float | None) -> str:
    """Format a Unix timestamp as a local date string (YYYY-MM-DD)."""
    if ts is None:
        return ""
    return time.strftime("%Y-%m-%d", time.localtime(ts))
