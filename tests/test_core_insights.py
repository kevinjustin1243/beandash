from __future__ import annotations

import datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING

from fava.beans import create
from fava.core.insights import InsightsModule

if TYPE_CHECKING:  # pragma: no cover
    from fava.beans.abc import Transaction


def _txn(day: int, payee: str, amount: str) -> Transaction:
    return create.transaction(
        {},
        datetime.date(2020, 1, day),
        "*",
        payee,
        "narration",
        postings=[
            create.posting("Assets:Checking", f"-{amount} USD"),
            create.posting("Expenses:Misc", f"{amount} USD"),
        ],
    )


class _FakeLedger:
    def __init__(self, transactions: list[Transaction]) -> None:
        self.all_entries_by_type = SimpleNamespace(Transaction=transactions)


def test_new_payee_flagged_once() -> None:
    txns = [
        _txn(1, "Costco", "50"),
        _txn(15, "Costco", "55"),
    ]
    module = InsightsModule(_FakeLedger(txns))  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]
    module.load_file()

    # Passing only the first (new-payee) transaction: flagged.
    result = module.insights([txns[0]])
    assert len(result) == 1
    assert result[0].type == "new_payee"
    assert result[0].payee == "Costco"

    # The later transaction for the same payee is not "new".
    result = module.insights([txns[1]])
    assert result == []


def test_normal_recurring_amounts_not_flagged() -> None:
    # No false positives: normal recurring amounts, checked alongside a
    # genuine outlier, should not themselves be flagged.
    regular = [_txn(i, "Netflix", "15") for i in range(1, 8, 1)]
    unusual = _txn(20, "Netflix", "500")
    module = InsightsModule(_FakeLedger([*regular, unusual]))  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]
    module.load_file()

    result = module.insights(regular[1:])
    assert result == []


def test_unusual_amount_needs_minimum_history() -> None:
    # Too few prior transactions to establish what's "usual".
    txns = [_txn(1, "Rare Shop", "10"), _txn(2, "Rare Shop", "1000")]
    module = InsightsModule(_FakeLedger(txns))  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]
    module.load_file()

    # The second entry isn't the payee's first, so it's checked for being
    # unusual - but there isn't enough history to say either way.
    result = module.insights([txns[1]])
    assert result == []


def test_matching_zero_variance_baseline_not_flagged() -> None:
    # A payee whose amount never varies (e.g. a fixed subscription) has a
    # baseline stdev of 0 - an amount that still matches it is not unusual.
    txns = [_txn(i, "Same Every Time", "20") for i in range(1, 8)]
    module = InsightsModule(_FakeLedger(txns))  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]
    module.load_file()

    result = module.insights(txns[1:])
    assert result == []


def test_unusual_amount_flagged_even_with_zero_variance_baseline() -> None:
    # A payee whose amount has *always* been identical is exactly the
    # case where a sudden different amount is most worth flagging - it
    # must not be excused just because the historic stdev is 0. This also
    # guards against "masking": computed naively (including the outlier
    # itself in the baseline), the one different amount would inflate its
    # own stdev and could hide itself.
    regular = [_txn(i, "Netflix", "15") for i in range(1, 8)]
    unusual = _txn(20, "Netflix", "500")
    module = InsightsModule(_FakeLedger([*regular, unusual]))  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]
    module.load_file()

    result = module.insights([unusual])
    assert len(result) == 1
    assert result[0].type == "unusual_transaction"


def test_no_transactions_or_payee() -> None:
    module = InsightsModule(_FakeLedger([]))  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]
    module.load_file()
    assert module.insights([]) == []

    no_payee = create.transaction(
        {},
        datetime.date(2020, 1, 1),
        "*",
        None,
        "narration",
        postings=[create.posting("Assets:Checking", "-1 USD")],
    )
    assert module.insights([no_payee]) == []


def test_transaction_with_no_postings_does_not_crash() -> None:
    # A transaction can have a payee but (e.g. while still being entered)
    # no postings yet - this shouldn't crash `load_file`.
    empty = create.transaction(
        {}, datetime.date(2020, 1, 1), "*", "Some Payee", "narration"
    )
    module = InsightsModule(_FakeLedger([empty]))  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]
    module.load_file()

    # Still flagged as a new payee - there's just no amount to check.
    result = module.insights([empty])
    assert len(result) == 1
    assert result[0].type == "new_payee"


def test_later_transaction_with_no_postings_is_ignored() -> None:
    # A known payee's later transaction with no postings yet (not its
    # first appearance, so not a "new payee") has no amount to check.
    regular = [_txn(i, "Costco", "50") for i in range(1, 6)]
    empty = create.transaction(
        {}, datetime.date(2020, 1, 10), "*", "Costco", "narration"
    )
    module = InsightsModule(_FakeLedger([*regular, empty]))  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]
    module.load_file()

    assert module.insights([empty]) == []


def test_unknown_payee_is_ignored() -> None:
    # An entry for a payee that load_file never saw at all (e.g. entries
    # passed in weren't part of the ledger it was built from) is a no-op
    # rather than a crash.
    module = InsightsModule(_FakeLedger([_txn(1, "Costco", "50")]))  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]
    module.load_file()

    assert module.insights([_txn(2, "Unknown Payee", "10")]) == []
