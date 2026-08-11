"""Parsing goal directives.

A goal is a `custom "goal"` directive naming an account, a label, a target
amount, and an optional target date - the definition mechanism mirrors
`custom "budget"` directives (see `core/budgets.py`) so goals stay versioned
in the ledger alongside the data they describe, with no new config surface.
"""

from __future__ import annotations

from datetime import date
from typing import NamedTuple
from typing import TYPE_CHECKING

from fava.core.module_base import FavaModule
from fava.helpers import BeancountError

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Sequence
    from decimal import Decimal

    from fava.beans.abc import Custom
    from fava.core import FavaLedger


class Goal(NamedTuple):
    """A savings or payoff goal."""

    account: str
    label: str
    target: Decimal
    currency: str
    target_date: date | None
    date: date
    """The date the goal was declared - the baseline for payoff progress."""


class GoalError(BeancountError):
    """Error with a goal."""


class GoalsModule(FavaModule):
    """Parses goal entries."""

    def __init__(self, ledger: FavaLedger) -> None:
        super().__init__(ledger)
        self.goals: Sequence[Goal] = []
        self.errors: Sequence[GoalError] = []

    def load_file(self) -> None:  # noqa: D102
        self.goals, self.errors = parse_goals(
            self.ledger.all_entries_by_type.Custom,
        )


def parse_goals(
    custom_entries: Sequence[Custom],
) -> tuple[Sequence[Goal], Sequence[GoalError]]:
    """Parse goal directives from custom entries.

    Args:
        custom_entries: the Custom entries to parse goals from.

    Returns:
        A list of goals, in the order they were declared.

    Example:
        2015-04-09 custom "goal" Assets:Savings "House" 50000.00 USD 2027-06-01
    """
    goals: list[Goal] = []
    errors: list[GoalError] = []

    for entry in (e for e in custom_entries if e.type == "goal"):
        try:
            account = entry.values[0].value
            label = entry.values[1].value
            amount = entry.values[2].value
            target_date: date | None = None
            if len(entry.values) > 3:
                target_date = entry.values[3].value
                if not isinstance(target_date, date):
                    errors.append(
                        GoalError(
                            entry.meta,
                            "Invalid target date for goal entry",
                            entry,
                        ),
                    )
                    continue
            goals.append(
                Goal(
                    account=account,
                    label=label,
                    target=amount.number,
                    currency=amount.currency,
                    target_date=target_date,
                    date=entry.date,
                ),
            )
        except (IndexError, TypeError, AttributeError):
            errors.append(
                GoalError(entry.meta, "Failed to parse goal entry", entry),
            )

    return goals, errors
