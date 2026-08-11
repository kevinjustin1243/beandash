"""Fava's goal syntax."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from fava.core.goals import parse_goals

if TYPE_CHECKING:  # pragma: no cover
    from fava.beans.abc import Custom


def test_goals(load_doc_custom_entries: list[Custom]) -> None:
    """
    2015-04-09 custom "goal" Assets:Savings "House" 50000.00 USD 2027-06-01
    2015-04-09 custom "goal" Assets:Savings "No date goal" 1000.00 USD
    2015-04-09 custom "goal" Assets:Savings "Bad date" 1000.00 USD "not-a-date"
    2015-04-09 custom "goal" Assets:Savings "Missing amount"
    2015-04-09 custom "goal" Assets:Savings
    """
    goals, errors = parse_goals(load_doc_custom_entries)

    assert len(errors) == 3
    assert len(goals) == 2

    house_fund = goals[0]
    assert house_fund.account == "Assets:Savings"
    assert house_fund.label == "House"
    assert house_fund.target == Decimal("50000.00")
    assert house_fund.currency == "USD"
    assert house_fund.target_date == date(2027, 6, 1)
    assert house_fund.date == date(2015, 4, 9)

    no_date_goal = goals[1]
    assert no_date_goal.label == "No date goal"
    assert no_date_goal.target_date is None
