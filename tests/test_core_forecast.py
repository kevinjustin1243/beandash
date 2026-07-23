from __future__ import annotations

import datetime
from decimal import Decimal

from fava.core.charts import DateAndBalance
from fava.core.forecast import forecast
from fava.core.inventory import SimpleCounterInventory


def _points(
    start: datetime.date,
    step_days: int,
    values: list[int],
    currency: str = "USD",
) -> list[DateAndBalance]:
    return [
        DateAndBalance(
            start + datetime.timedelta(days=step_days * i),
            SimpleCounterInventory({currency: Decimal(value)}),
        )
        for i, value in enumerate(values)
    ]


def test_forecast_too_little_data() -> None:
    assert forecast([]) == []
    assert forecast(_points(datetime.date(2020, 1, 1), 30, [100])) == []


def test_forecast_linear_trend() -> None:
    start = datetime.date(2020, 1, 1)
    data = _points(start, 30, [100, 110, 120, 130, 140, 150])

    result = forecast(data)
    assert result

    # The first point anchors to the last historic value, so a chart can
    # draw a continuous line without a visual gap.
    assert result[0].date == start + datetime.timedelta(days=150)
    assert result[0].balance == {"USD (projected)": Decimal(150)}

    # 30 days later (one more "step"), the perfectly linear trend
    # continues by exactly one more increment.
    assert result[1].date == start + datetime.timedelta(days=180)
    assert result[1].balance["USD (projected)"] == Decimal(160)

    # ~1 year out (FORECAST_HORIZON_DAYS), continuing the same trend.
    assert result[-1].balance["USD (projected)"] == Decimal(150 + 10 * 12)


def test_forecast_multiple_currencies() -> None:
    data = [
        DateAndBalance(
            datetime.date(2020, 1, 1) + datetime.timedelta(days=30 * i),
            SimpleCounterInventory(
                {"USD": Decimal(100 + 10 * i), "EUR": Decimal(50 - 5 * i)},
            ),
        )
        for i in range(4)
    ]

    result = forecast(data)
    assert result
    assert result[1].balance["USD (projected)"] == Decimal(140)
    assert result[1].balance["EUR (projected)"] == Decimal(30)


def test_forecast_uses_recent_trend_not_whole_history() -> None:
    # A long flat stretch followed by a recent uptrend should forecast a
    # continuation of the *recent* uptrend, not an average across the
    # whole history (which would drag the trend down towards flat/declining,
    # since most of the points contributed no growth at all).
    flat = _points(datetime.date(2000, 1, 1), 30, [100] * 40)
    uptrend_start = flat[-1].date + datetime.timedelta(days=30)
    uptrend = _points(uptrend_start, 30, [100 + 10 * i for i in range(24)])
    data = [*flat, *uptrend]

    result = forecast(data)
    assert result
    last_value = 100 + 10 * 23
    assert result[0].balance["USD (projected)"] == Decimal(last_value)
    assert result[1].balance["USD (projected)"] == Decimal(last_value + 10)


def test_forecast_ignores_currency_seen_only_once() -> None:
    # A currency that only shows up in one historic point (e.g. newly
    # acquired) can't be fit to a trend and should just be dropped.
    data = [
        DateAndBalance(
            datetime.date(2020, 1, 1),
            SimpleCounterInventory({"USD": Decimal(100)}),
        ),
        DateAndBalance(
            datetime.date(2020, 1, 31),
            SimpleCounterInventory({"USD": Decimal(110), "EUR": Decimal(5)}),
        ),
    ]

    result = forecast(data)
    assert result
    assert "EUR (projected)" not in result[-1].balance
    assert "USD (projected)" in result[-1].balance


def test_forecast_ignores_currency_with_no_trend() -> None:
    # Two points on the exact same date can't be fit to a line - that
    # currency should just be dropped rather than raising an error.
    same_date = datetime.date(2020, 1, 1)
    data = [
        DateAndBalance(same_date, SimpleCounterInventory({"USD": Decimal(1)})),
        DateAndBalance(same_date, SimpleCounterInventory({"USD": Decimal(2)})),
    ]
    assert forecast(data) == []
