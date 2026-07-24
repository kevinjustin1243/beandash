"""Flag unusual transactions and newly-seen payees.

Rather than a scheduled digest, insights are recomputed cheaply on each
request against precomputed per-payee statistics, checked against
whichever transactions are currently in view (respecting the existing
time/account/filter query params, same as any other report).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fava.beans.abc import Transaction
from fava.beans.funcs import hash_entry
from fava.core.module_base import FavaModule

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Sequence
    from datetime import date

    from fava.beans.abc import Directive
    from fava.core import FavaLedger

#: Minimum number of *other* transactions for a payee needed to consider
#: flagging one of its amounts as unusual - too few and any variation
#: looks "unusual".
MIN_HISTORY = 4

#: How many standard deviations away from a payee's average transaction
#: amount counts as unusual.
ZSCORE_THRESHOLD = 2.5


def _txn_amount(txn: Transaction) -> float | None:
    """A representative amount for a transaction (its first posting)."""
    if not txn.postings:
        return None
    return abs(float(txn.postings[0].units.number))


@dataclass(frozen=True)
class PayeeStats:
    """Running totals for a payee's transaction amounts.

    Storing sums rather than a precomputed mean/stdev lets each candidate
    transaction be checked against a "leave-one-out" baseline (see
    `excluding`) cheaply, without keeping every individual amount around.
    """

    count: int
    total: float
    total_sq: float
    first_date: date


def excluding(stats: PayeeStats, amount: float) -> tuple[float, float] | None:
    """Mean/stdev of a payee's amounts, leaving the given one out.

    Excluding the transaction being checked from its own baseline avoids
    "masking": a single outlier pulling the mean/stdev towards itself
    would otherwise make its own amount look less unusual, and a payee
    whose amount never varies would have a zero baseline stdev - which is
    exactly the case where *any* different amount is most worth flagging.

    Returns:
        `None` if there are too few other transactions for this payee to
        establish a baseline.
    """
    n = stats.count - 1
    if n < MIN_HISTORY:
        return None
    total = stats.total - amount
    mean = total / n
    variance = (stats.total_sq - amount * amount) / n - mean * mean
    return mean, math.sqrt(max(variance, 0.0))


@dataclass(frozen=True)
class Insight:
    """A single flagged item to show on the dashboard."""

    type: str
    payee: str
    message: str
    entry_hash: str


class InsightsModule(FavaModule):
    """Flag unusual transaction amounts and newly-seen payees."""

    def __init__(self, ledger: FavaLedger) -> None:
        super().__init__(ledger)
        self._payee_stats: dict[str, PayeeStats] = {}

    def load_file(self) -> None:  # noqa: D102
        totals: dict[str, float] = {}
        totals_sq: dict[str, float] = {}
        counts: dict[str, int] = {}
        first_date_by_payee: dict[str, date] = {}
        for txn in self.ledger.all_entries_by_type.Transaction:
            if not txn.payee:
                continue
            if txn.payee not in first_date_by_payee:
                first_date_by_payee[txn.payee] = txn.date
            amount = _txn_amount(txn)
            if amount is not None:
                totals[txn.payee] = totals.get(txn.payee, 0.0) + amount
                totals_sq[txn.payee] = (
                    totals_sq.get(txn.payee, 0.0) + amount * amount
                )
                counts[txn.payee] = counts.get(txn.payee, 0) + 1

        self._payee_stats = {
            payee: PayeeStats(
                count=counts.get(payee, 0),
                total=totals.get(payee, 0.0),
                total_sq=totals_sq.get(payee, 0.0),
                first_date=first_date,
            )
            for payee, first_date in first_date_by_payee.items()
        }

    def insights(self, entries: Sequence[Directive]) -> Sequence[Insight]:
        """Flag unusual transactions and new payees among `entries`.

        Args:
            entries: The (usually filtered) entries currently in view.

        Returns:
            One :class:`Insight` per flagged transaction, in the order the
            transactions appear in `entries`.
        """
        found: list[Insight] = []
        flagged_new_payees: set[str] = set()
        for entry in entries:
            if not isinstance(entry, Transaction) or not entry.payee:
                continue
            payee = entry.payee
            stats = self._payee_stats.get(payee)

            if (
                stats is not None
                and entry.date == stats.first_date
                and payee not in flagged_new_payees
            ):
                flagged_new_payees.add(payee)
                found.append(
                    Insight(
                        "new_payee",
                        payee,
                        f"New payee: {payee}",
                        hash_entry(entry),
                    ),
                )
                continue

            amount = _txn_amount(entry)
            if stats is None or amount is None:
                continue
            fit = excluding(stats, amount)
            if fit is None:
                continue
            mean, stdev = fit
            is_unusual = (
                amount != mean
                if stdev == 0
                else abs(amount - mean) / stdev > ZSCORE_THRESHOLD
            )
            if is_unusual:
                found.append(
                    Insight(
                        "unusual_transaction",
                        payee,
                        f"Unusual amount for {payee}: {amount:.2f} "
                        f"(usually around {mean:.2f})",
                        hash_entry(entry),
                    ),
                )
        return found
