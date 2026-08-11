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

    def __init__(
        self,
        transactions: list[object],
        uncategorized_account: str = "Expenses:Uncategorized",
    ) -> None:
        self.all_entries_by_type = SimpleNamespace(Transaction=transactions)
        self.fava_options = SimpleNamespace(
            uncategorized_account=uncategorized_account,
        )


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
    assert result[0][0] == "Expenses:Food:Groceries"
    assert result[0][1] > 0

    result = module.suggest_accounts("Chevron gas station")
    assert result
    assert result[0][0] == "Expenses:Auto:Fuel"

    # Text unrelated to any historic transaction should suggest nothing.
    assert module.suggest_accounts("asdkjfh qwlekjr") == []

    # No text at all should also suggest nothing.
    assert module.suggest_accounts("") == []


def test_suggest_accounts_excludes_placeholder_account() -> None:
    # A payee with too little history that the placeholder account it was
    # posted to would otherwise be the (only, or top) suggestion - a no-op
    # that looks like a real categorization. It must never be suggested.
    txns = [
        _txn(
            "Kettle & Vine",
            "lunch, offsite",
            "Liabilities:Chase",
            "Expenses:Uncategorized",
        ),
    ]
    module = SuggestModule(_FakeLedger(txns))  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]
    module.load_file()

    result = module.suggest_accounts("Kettle & Vine lunch, offsite")
    assert all(
        account != "Expenses:Uncategorized" for account, _score in result
    )

    # With a custom placeholder account configured, that one is excluded
    # instead - the default name isn't special-cased.
    fake_ledger = _FakeLedger(txns, uncategorized_account="Liabilities:Chase")
    module = SuggestModule(fake_ledger)  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]
    module.load_file()

    result = module.suggest_accounts("Kettle & Vine lunch, offsite")
    assert all(account != "Liabilities:Chase" for account, _score in result)
    assert any(
        account == "Expenses:Uncategorized" for account, _score in result
    )


def test_suggest_accounts_example_ledger(example_ledger: FavaLedger) -> None:
    suggest = example_ledger.suggest

    # "BANK FEES" / "Monthly bank fee" transactions are always posted to
    # Expenses:Financial:Fees - a new payee with an overlapping narration
    # should still surface that account.
    result = suggest.suggest_accounts("My Bank monthly banking fee charge")
    assert result
    assert result[0][0] == "Expenses:Financial:Fees"

    assert suggest.suggest_accounts("") == []
