"""Simple statistical forecasting over existing chart data.

Rather than a trained model, this fits a linear trend to historic
(date, balance) data - e.g. net worth over time - and projects it
forward, together with a widening confidence band and the fit's r².
That is easy to reason about and cheap to compute at the scale of a
personal ledger, and needs no extra dependency.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from fava.core.charts import DateAndBalance
from fava.core.inventory import SimpleCounterInventory

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Mapping
    from collections.abc import Sequence

#: Suffix added to a currency to mark it as a projected (not historic) series.
PROJECTED_SUFFIX = " (projected)"
#: Suffixes for the upper/lower confidence-band series of a projected currency.
PROJECTED_HIGH_SUFFIX = " (projected high)"
PROJECTED_LOW_SUFFIX = " (projected low)"

#: Roughly how far into the future to project.
FORECAST_HORIZON_DAYS = 365

#: Number of most-recent historic points to fit the trend to. Using only a
#: recent window (rather than the entire history) means a years-long flat
#: stretch early on doesn't drag down a fit that should reflect where things
#: stand now.
TREND_WINDOW = 24

#: z-score for an (approximate) 80% two-sided confidence band.
BAND_Z_SCORE = 1.2816


@dataclass(frozen=True)
class LinearFit:
    """A least-squares line fit to a series of (day-ordinal, value) points."""

    slope: float
    intercept: float
    r_squared: float
    residual_stdev: float
    window_size: int

    def predict(self, x: int) -> float:
        """Predicted value at a given day-ordinal."""
        return self.slope * x + self.intercept

    def band_half_width(self, periods_ahead: int) -> float:
        """Half-width of an ~80% prediction interval `periods_ahead` out.

        Widens with distance from the fitted window, approximating how
        much less certain a projection gets the further out it goes.
        """
        return (
            BAND_Z_SCORE
            * self.residual_stdev
            * math.sqrt(
                1 + periods_ahead / self.window_size,
            )
        )


def _fit(points: Sequence[tuple[int, float]]) -> LinearFit | None:
    """Least-squares fit of ``y = slope * x + intercept``.

    Returns:
        A :class:`LinearFit`, or ``None`` if there are too few (or
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

    mean_y = sum_y / n
    ss_tot = sum((y - mean_y) ** 2 for _x, y in points)
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in points)
    r_squared = 1.0 if ss_tot == 0 else 1 - ss_res / ss_tot

    return LinearFit(
        slope=slope,
        intercept=intercept,
        r_squared=r_squared,
        residual_stdev=math.sqrt(ss_res / n),
        window_size=n,
    )


def fit_currencies(data: Sequence[DateAndBalance]) -> Mapping[str, LinearFit]:
    """Fit a trend line per currency, using only the most recent window.

    Args:
        data: Historic (date, balance) points, e.g. from
            `ChartModule.net_worth` or `ChartModule.interval_totals`, in
            chronological order.
    """
    window = data[-TREND_WINDOW:]
    by_currency: dict[str, list[tuple[int, float]]] = {}
    for point in window:
        x = point.date.toordinal()
        for currency, value in point.balance.items():
            by_currency.setdefault(currency, []).append((x, float(value)))

    return {
        currency: fit
        for currency, points in by_currency.items()
        if (fit := _fit(points)) is not None
    }


@dataclass(frozen=True)
class CurrencyForecast:
    """Forecast summary for a single currency."""

    #: Value at the end of the forecast horizon.
    projected: Decimal
    #: How well the trend line fits the recent window (0-1, higher is better).
    r_squared: float
    #: Average day-over-day change, in the same units as the balance.
    daily_change: Decimal


@dataclass(frozen=True)
class Forecast:
    """A forecast: chart points to extend a balances chart, plus stats."""

    #: Points continuing after the last date in the input, spaced like the
    #: input's own spacing, covering roughly `FORECAST_HORIZON_DAYS`. The
    #: first point repeats the last historic balance (anchored, zero-width
    #: band) so a chart can draw a continuous line with no visual gap. Each
    #: currency appears three times, suffixed to distinguish the point
    #: estimate and the upper/lower confidence band from the historic
    #: series when rendered on the same chart.
    points: Sequence[DateAndBalance]
    #: Per-currency summary stats, for currencies with enough history to
    #: fit a trend.
    by_currency: Mapping[str, CurrencyForecast]


def forecast(data: Sequence[DateAndBalance]) -> Forecast:
    """Project each currency in `data` forward using a linear trend.

    Args:
        data: Historic (date, balance) points, e.g. from
            `ChartModule.net_worth`, in chronological order.

    Returns:
        An empty forecast if there is too little data to fit a trend.
    """
    if len(data) < 2:
        return Forecast(points=[], by_currency={})

    fits = fit_currencies(data)
    if not fits:
        return Forecast(points=[], by_currency={})

    window = data[-TREND_WINDOW:]
    last_point = data[-1]
    step_days = max(
        (window[-1].date - window[0].date).days // (len(window) - 1),
        1,
    )
    periods = max(FORECAST_HORIZON_DAYS // step_days, 1)

    anchor = {
        currency: value
        for currency, value in last_point.balance.items()
        if currency in fits
    }
    forecasted = [
        DateAndBalance(
            last_point.date,
            SimpleCounterInventory(
                {f"{c}{PROJECTED_SUFFIX}": v for c, v in anchor.items()},
            ),
        ),
    ]
    for i in range(1, periods + 1):
        future_date = last_point.date + timedelta(days=step_days * i)
        x = future_date.toordinal()
        point: dict[str, Decimal] = {}
        for currency, fit in fits.items():
            predicted = fit.predict(x)
            half_width = fit.band_half_width(i)
            point[f"{currency}{PROJECTED_SUFFIX}"] = Decimal(
                str(round(predicted, 2)),
            )
            point[f"{currency}{PROJECTED_HIGH_SUFFIX}"] = Decimal(
                str(round(predicted + half_width, 2)),
            )
            point[f"{currency}{PROJECTED_LOW_SUFFIX}"] = Decimal(
                str(round(predicted - half_width, 2)),
            )
        forecasted.append(
            DateAndBalance(future_date, SimpleCounterInventory(point)),
        )

    final_x = forecasted[-1].date.toordinal()
    by_currency = {
        currency: CurrencyForecast(
            projected=Decimal(str(round(fit.predict(final_x), 2))),
            r_squared=fit.r_squared,
            daily_change=Decimal(str(round(fit.slope, 2))),
        )
        for currency, fit in fits.items()
    }
    return Forecast(points=forecasted, by_currency=by_currency)


def years_to_target(
    current_value: float,
    daily_change: float,
    target_value: float,
) -> float | None:
    """Years until a linearly-trending value reaches a target.

    Args:
        current_value: The value now.
        daily_change: Average change per day (a forecast's trend slope).
        target_value: The value to reach.

    Returns:
        `0.0` if the target is already reached, `None` if the trend is
        flat or moving away from the target (it will never be reached),
        otherwise the number of years until it is.
    """
    if current_value >= target_value:
        return 0.0
    if daily_change <= 0:
        return None
    return (target_value - current_value) / daily_change / 365
