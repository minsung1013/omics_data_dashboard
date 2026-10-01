"""Small shared helpers for adapters (dates, sizes, html)."""
import re
from datetime import datetime, timezone

from dateutil import parser as _dtparser


def iso_date(value):
    """Normalize many date representations to 'YYYY-MM-DD' (or None)."""
    if value is None or value == "":
        return None
    # Numeric epoch (seconds or milliseconds)
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e12:  # milliseconds
            ts /= 1000.0
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        except (OverflowError, OSError, ValueError):
            return None
    s = str(value).strip()
    # GEO style 2026/09/20
    s = s.replace("/", "-")
    try:
        return _dtparser.parse(s, fuzzy=True).strftime("%Y-%m-%d")
    except (ValueError, OverflowError):
        return None


def human_size(num_bytes):
    """Bytes -> human readable string, or None."""
    if not num_bytes:
        return None
    try:
        n = float(num_bytes)
    except (TypeError, ValueError):
        return None
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if n < 1024 or unit == "PB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return None


def strip_html(text, limit=600):
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", str(text))
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:limit]


def on_or_after(date_str, since):
    """True if 'YYYY-MM-DD' date_str is on/after `since` (datetime.date)."""
    if not date_str:
        return False
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return False
    return d >= since
