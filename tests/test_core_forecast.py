from __future__ import annotations

import datetime
from decimal import Decimal

from fava.core.charts import DateAndBalance
from fava.core.forecast import Forecast
from fava.core.forecast import forecast
from fava.core.forecast import years_to_target
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
    assert forecast([]) == Forecast(points=[], by_currency={})
    assert forecast(
        _points(datetime.date(2020, 1, 1), 30, [100]),
    ) == Forecast(points=[], by_currency={})


def test_forecast_linear_trend() -> None:
    start = datetime.date(2020, 1, 1)
    data = _points(start, 30, [100, 110, 120, 130, 140, 150])

    result = forecast(data)
    assert result.points

    # The first point anchors to the last historic value, so a chart can
    # draw a continuous line without a visual gap - and has no band, since
    # it isn't actually a projection.
    first = result.points[0]
    assert first.date == start + datetime.timedelta(days=150)
    assert first.balance == {"USD (projected)": Decimal(150)}

    # 30 days later (one more "step"), the perfectly linear trend
    # continues by exactly one more increment - and a perfectly linear
    # trend has zero residual error, so the band collapses to the point
    # estimate.
    second = result.points[1]
    assert second.date == start + datetime.timedelta(days=180)
    assert second.balance["USD (projected)"] == Decimal(160)
    assert second.balance["USD (projected high)"] == Decimal(160)
    assert second.balance["USD (projected low)"] == Decimal(160)

    # ~1 year out (FORECAST_HORIZON_DAYS), continuing the same trend.
    assert result.points[-1].balance["USD (projected)"] == Decimal(
        150 + 10 * 12,
    )

    # Per-currency stats: a perfect fit has r² of 1 and a $10/step slope.
    stats = result.by_currency["USD"]
    assert stats.projected == result.points[-1].balance["USD (projected)"]
    assert stats.r_squared == 1.0
    assert stats.daily_change == Decimal(str(round(10 / 30, 2)))


def test_forecast_band_widens_with_distance() -> None:
    # A noisy (non-perfectly-linear) series has a non-zero residual stdev,
    # so the band should be a real range, and should widen further out.
    start = datetime.date(2020, 1, 1)
    values = [100, 115, 108, 130, 122, 145]
    data = _points(start, 30, values)

    result = forecast(data)
    assert result.points
    stats = result.by_currency["USD"]
    assert 0 < stats.r_squared < 1

    near = result.points[1].balance
    far = result.points[-1].balance
    near_width = near["USD (projected high)"] - near["USD (projected low)"]
    far_width = far["USD (projected high)"] - far["USD (projected low)"]
    assert near_width > 0
    assert far_width > near_width
    # The point estimate should sit inside its own band.
    assert near["USD (projected low)"] <= near["USD (projected)"]
    assert near["USD (projected)"] <= near["USD (projected high)"]


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
    assert result.points
    assert result.points[1].balance["USD (projected)"] == Decimal(140)
    assert result.points[1].balance["EUR (projected)"] == Decimal(30)
    assert set(result.by_currency) == {"USD", "EUR"}


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
    assert result.points
    last_value = 100 + 10 * 23
    assert result.points[0].balance["USD (projected)"] == Decimal(last_value)
    assert result.points[1].balance["USD (projected)"] == Decimal(
        last_value + 10,
    )


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
    assert result.points
    assert "EUR (projected)" not in result.points[-1].balance
    assert "USD (projected)" in result.points[-1].balance
    assert set(result.by_currency) == {"USD"}


def test_forecast_ignores_currency_with_no_trend() -> None:
    # Two points on the exact same date can't be fit to a line - that
    # currency should just be dropped rather than raising an error.
    same_date = datetime.date(2020, 1, 1)
    data = [
        DateAndBalance(same_date, SimpleCounterInventory({"USD": Decimal(1)})),
        DateAndBalance(same_date, SimpleCounterInventory({"USD": Decimal(2)})),
    ]
    assert forecast(data) == Forecast(points=[], by_currency={})


def test_years_to_target_already_there() -> None:
    assert years_to_target(100.0, 1.0, 50.0) == 0.0
    assert years_to_target(100.0, 1.0, 100.0) == 0.0


def test_years_to_target_never_gets_there() -> None:
    assert years_to_target(50.0, 0.0, 100.0) is None
    assert years_to_target(50.0, -1.0, 100.0) is None


def test_years_to_target_computes_years() -> None:
    # $10/day for 365 days is $3650/year: 2 years to close a $7300 gap.
    result = years_to_target(0.0, 10.0, 7300.0)
    assert result is not None
    assert round(result, 2) == 2.0
