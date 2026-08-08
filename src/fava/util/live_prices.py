"""Fetch live stock/ETF quotes from Finnhub's free-tier quote endpoint."""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Mapping
    from collections.abc import Sequence

QUOTE_URL = "https://finnhub.io/api/v1/quote"
CACHE_TTL_SECONDS = 15
REQUEST_TIMEOUT_SECONDS = 5


@dataclass(frozen=True)
class Quote:
    """A live quote for a single ticker."""

    price: float
    day_change_pct: float
    as_of: int


_cache: dict[str, tuple[float, Quote]] = {}


def _fetch_quote(symbol: str, api_key: str) -> Quote | None:
    """Fetch a single quote from Finnhub, or None if unavailable."""
    query = urllib.parse.urlencode({"symbol": symbol, "token": api_key})
    url = f"{QUOTE_URL}?{query}"
    try:
        with urllib.request.urlopen(  # noqa: S310
            url, timeout=REQUEST_TIMEOUT_SECONDS
        ) as response:
            payload = json.loads(response.read())
    except (OSError, ValueError):
        return None
    price = payload.get("c")
    previous_close = payload.get("pc")
    as_of = payload.get("t")
    if not price or not previous_close or not as_of:
        return None
    return Quote(
        price=price,
        day_change_pct=(price - previous_close) / previous_close * 100,
        as_of=as_of,
    )


def fetch_quotes(symbols: Sequence[str]) -> Mapping[str, Quote]:
    """Fetch live quotes for the given ticker symbols.

    Reads the API key from the FINNHUB_API_KEY environment variable only;
    returns an empty mapping if it is not set. Symbols that Finnhub can't
    quote are simply omitted from the result. Uses a short in-memory TTL
    cache to dedupe rapid repeated calls and stay within the free tier's
    rate limit.
    """
    api_key = os.environ.get("FINNHUB_API_KEY")
    if not api_key:
        return {}
    now = time.time()
    quotes: dict[str, Quote] = {}
    for symbol in symbols:
        cached = _cache.get(symbol)
        if cached is not None and now - cached[0] < CACHE_TTL_SECONDS:
            quotes[symbol] = cached[1]
            continue
        quote = _fetch_quote(symbol, api_key)
        if quote is not None:
            _cache[symbol] = (now, quote)
            quotes[symbol] = quote
    return quotes
