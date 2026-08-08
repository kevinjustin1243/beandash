from __future__ import annotations

import json
import urllib.request
from typing import TYPE_CHECKING

import pytest

from fava.util import live_prices
from fava.util.live_prices import fetch_quotes
from fava.util.live_prices import Quote

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Self


class _FakeResponse:
    def __init__(self, payload: Mapping[str, object]) -> None:
        self._body = json.dumps(payload).encode()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def read(self) -> bytes:
        return self._body


def test_fetch_quotes_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    assert fetch_quotes(["AAPL"]) == {}


def test_fetch_quotes_uses_and_populates_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FINNHUB_API_KEY", "test-key")
    live_prices._cache.clear()

    calls: list[str] = []

    def fake_fetch_quote(symbol: str, api_key: str) -> Quote | None:
        calls.append(symbol)
        assert api_key == "test-key"
        if symbol == "AAPL":
            return Quote(price=210.0, day_change_pct=1.5, as_of=123)
        return None

    monkeypatch.setattr(live_prices, "_fetch_quote", fake_fetch_quote)

    result = fetch_quotes(["AAPL", "UNKNOWN"])
    expected = Quote(price=210.0, day_change_pct=1.5, as_of=123)
    assert result == {"AAPL": expected}
    assert calls == ["AAPL", "UNKNOWN"]

    # A second call within the TTL should be served from the cache.
    result_cached = fetch_quotes(["AAPL"])
    assert result_cached == result
    assert calls == ["AAPL", "UNKNOWN"]


def test_fetch_quote_success(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(url: str, timeout: float) -> _FakeResponse:  # noqa: ARG001
        return _FakeResponse({"c": 100.0, "pc": 90.0, "t": 42})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    quote = live_prices._fetch_quote("AAPL", "test-key")
    assert quote is not None
    assert quote.price == 100.0
    assert quote.as_of == 42
    assert quote.day_change_pct == pytest.approx((100.0 - 90.0) / 90.0 * 100)


def test_fetch_quote_missing_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(url: str, timeout: float) -> _FakeResponse:  # noqa: ARG001
        return _FakeResponse({"c": 0, "pc": 0, "t": 0})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    assert live_prices._fetch_quote("AAPL", "test-key") is None


def test_fetch_quote_request_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(url: str, timeout: float) -> _FakeResponse:  # noqa: ARG001
        raise OSError

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    assert live_prices._fetch_quote("AAPL", "test-key") is None


def test_fetch_quote_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    class _BadResponse(_FakeResponse):
        def read(self) -> bytes:
            return b"not json"

    def fake_urlopen(url: str, timeout: float) -> _BadResponse:  # noqa: ARG001
        return _BadResponse({})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    assert live_prices._fetch_quote("AAPL", "test-key") is None
