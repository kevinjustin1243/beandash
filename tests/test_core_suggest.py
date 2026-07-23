from __future__ import annotations

import datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING

from fava.beans import create
from fava.core.suggest import SuggestModule
from fava.core.suggest import tokenize

if TYPE_CHECKING:  # pragma: no cover
    from fava.core import FavaLedger


def test_tokenize() -> None:
    assert tokenize("Hello, World! 123") == ["hello", "world"]
    assert tokenize("") == []
    assert tokenize("Trader Joe's #42") == ["trader", "joe", "s"]


def _txn(payee: str, narration: str, *accounts: str) -> object:
    return create.transaction(
        {},
        datetime.date(2020, 1, 1),
        "*",
        payee,
        narration,
        postings=[create.posting(account, "10 USD") for account in accounts],
    )


class _FakeLedger:
    """A stand-in for FavaLedger exposing just what SuggestModule needs."""

    def __init__(self, transactions: list[object]) -> None:
        self.all_entries_by_type = SimpleNamespace(Transaction=transactions)


def test_suggest_accounts_new_payee() -> None:
    txns = [
        _txn(
            "Costco", "groceries", "Assets:Checking", "Expenses:Food:Groceries"
        ),
        _txn(
            "Costco",
            "groceries run",
            "Assets:Checking",
            "Expenses:Food:Groceries",
        ),
        _txn(
            "Shell",
            "gas station fill up",
            "Assets:Checking",
            "Expenses:Auto:Fuel",
        ),
        _txn(
            "Netflix",
            "monthly subscription",
            "Assets:Checking",
            "Expenses:Entertainment:Streaming",
        ),
    ]
    module = SuggestModule(_FakeLedger(txns))  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]
    module.load_file()

    # A brand new payee ("Trader Joes") has never been seen, but the
    # narration text overlaps with the historic "groceries" transactions.
    result = module.suggest_accounts("Trader Joes groceries")
    assert result
    assert result[0] == "Expenses:Food:Groceries"

    result = module.suggest_accounts("Chevron gas station")
    assert result
    assert result[0] == "Expenses:Auto:Fuel"

    # Text unrelated to any historic transaction should suggest nothing.
    assert module.suggest_accounts("asdkjfh qwlekjr") == []

    # No text at all should also suggest nothing.
    assert module.suggest_accounts("") == []


def test_suggest_accounts_example_ledger(example_ledger: FavaLedger) -> None:
    suggest = example_ledger.suggest

    # "BANK FEES" / "Monthly bank fee" transactions are always posted to
    # Expenses:Financial:Fees - a new payee with an overlapping narration
    # should still surface that account.
    result = suggest.suggest_accounts("My Bank monthly banking fee charge")
    assert result
    assert result[0] == "Expenses:Financial:Fees"

    assert suggest.suggest_accounts("") == []
