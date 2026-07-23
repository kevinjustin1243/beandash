"""Simple statistical forecasting over existing chart data.

Rather than a trained model, this fits a linear trend to historic
(date, balance) data - e.g. net worth over time - and projects it
forward. That is easy to reason about and cheap to compute at the scale
of a personal ledger, and needs no extra dependency.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from fava.core.charts import DateAndBalance
from fava.core.inventory import SimpleCounterInventory

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Sequence

#: Suffix added to a currency to mark it as a projected (not historic) series.
PROJECTED_SUFFIX = " (projected)"

#: Roughly how far into the future to project.
FORECAST_HORIZON_DAYS = 365

#: Number of most-recent historic points to fit the trend to. Using only a
#: recent window (rather than the entire history) means a years-long flat
#: stretch early on doesn't drag down a fit that should reflect where things
#: stand now.
TREND_WINDOW = 24


def _linear_fit(
    points: Sequence[tuple[int, float]],
) -> tuple[float, float] | None:
    """Least-squares fit of ``y = slope * x + intercept``.

    Returns:
        The ``(slope, intercept)`` or ``None`` if there are too few (or
        degenerate, e.g. all on the same date) points to fit a line.
    """
    n = len(points)
    if n < 2:
        return None
    sum_x = sum(x for x, _y in points)
    sum_y = sum(y for _x, y in points)
    sum_xy = sum(x * y for x, y in points)
    sum_xx = sum(x * x for x, _y in points)
    denominator = n * sum_xx - sum_x * sum_x
    if denominator == 0:
        return None
    slope = (n * sum_xy - sum_x * sum_y) / denominator
    intercept = (sum_y - slope * sum_x) / n
    return slope, intercept


def forecast(data: Sequence[DateAndBalance]) -> Sequence[DateAndBalance]:
    """Project each currency in `data` forward using a linear trend.

    Args:
        data: Historic (date, balance) points, e.g. from
            `ChartModule.net_worth`, in chronological order.

    Returns:
        Points continuing after the last date in `data`, one every as many
        days apart as the input's own spacing, covering roughly
        `FORECAST_HORIZON_DAYS`. Only the most recent `TREND_WINDOW` points
        are used to fit the trend, so it reflects where things stand now
        rather than being dragged down (or up) by a long-past stretch. The
        first point repeats the last historic balance so a chart can draw a
        continuous line. Each currency is suffixed to distinguish it from
        the historic series when both are rendered on the same chart. Empty
        if there is too little data to fit a trend.
    """
    if len(data) < 2:
        return []

    window = data[-TREND_WINDOW:]
    by_currency: dict[str, list[tuple[int, float]]] = {}
    for point in window:
        x = point.date.toordinal()
        for currency, value in point.balance.items():
            by_currency.setdefault(currency, []).append((x, float(value)))

    fits = {
        currency: fit
        for currency, points in by_currency.items()
        if (fit := _linear_fit(points)) is not None
    }
    if not fits:
        return []

    last_point = data[-1]
    step_days = max(
        (window[-1].date - window[0].date).days // (len(window) - 1),
        1,
    )
    periods = max(FORECAST_HORIZON_DAYS // step_days, 1)

    forecasted = [
        DateAndBalance(
            last_point.date,
            SimpleCounterInventory(
                {
                    f"{currency}{PROJECTED_SUFFIX}": value
                    for currency, value in last_point.balance.items()
                    if currency in fits
                },
            ),
        ),
    ]
    for i in range(1, periods + 1):
        future_date = last_point.date + timedelta(days=step_days * i)
        x = future_date.toordinal()
        forecasted.append(
            DateAndBalance(
                future_date,
                SimpleCounterInventory(
                    {
                        f"{currency}{PROJECTED_SUFFIX}": Decimal(
                            str(round(slope * x + intercept, 2)),
                        )
                        for currency, (slope, intercept) in fits.items()
                    },
                ),
            ),
        )
    return forecasted
