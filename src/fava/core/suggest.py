"""Suggest accounts for a transaction based on its payee/narration text.

This supplements the payee-based suggestions in :class:`.AttributesModule`,
which can only suggest accounts for a payee that has been seen before. This
module instead scores accounts by how similar the words of a query text are
to the words of transactions historically posted to each account (a simple
TF-IDF-weighted bag-of-words match), so it can also suggest accounts for a
brand new payee or an unseen narration.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import TYPE_CHECKING

from fava.core.module_base import FavaModule

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Sequence

    from fava.core import FavaLedger

_TOKEN_RE = re.compile(r"[^\W\d_]+")


def tokenize(text: str) -> list[str]:
    """Split text into lowercase word tokens, ignoring numbers/punctuation."""
    return _TOKEN_RE.findall(text.lower())


class SuggestModule(FavaModule):
    """Suggest accounts for a payee/narration based on historic word usage."""

    def __init__(self, ledger: FavaLedger) -> None:
        super().__init__(ledger)
        self._account_tokens: dict[str, Counter[str]] = {}
        self._idf: dict[str, float] = {}

    def load_file(self) -> None:  # noqa: D102
        # Exclude the placeholder account itself from the candidates: it is
        # where a transaction *starts*, not a real category to suggest as a
        # replacement, and with too little other history for a payee it
        # could otherwise rank as the top (or only) suggestion - a no-op
        # that looks like a real categorization.
        placeholder = self.ledger.fava_options.uncategorized_account
        account_tokens: dict[str, Counter[str]] = {}
        for txn in self.ledger.all_entries_by_type.Transaction:
            tokens = tokenize(f"{txn.payee or ''} {txn.narration}")
            if not tokens:
                continue
            for posting in txn.postings:
                if posting.account == placeholder:
                    continue
                counter = account_tokens.setdefault(posting.account, Counter())
                counter.update(tokens)
        self._account_tokens = account_tokens

        num_accounts = len(account_tokens)
        document_frequency: Counter[str] = Counter()
        for counter in account_tokens.values():
            document_frequency.update(counter.keys())
        self._idf = {
            token: math.log((1 + num_accounts) / (1 + freq)) + 1
            for token, freq in document_frequency.items()
        }

    def suggest_accounts(self, text: str) -> Sequence[tuple[str, float]]:
        """Rank accounts by similarity of the given text to their history.

        Args:
            text: Free-form text, e.g. a transaction's payee and narration.

        Returns:
            ``(account, score)`` pairs with a non-zero match, best match
            first. The score is an unbounded TF-IDF-style dot product, not
            a calibrated probability - callers wanting a 0-100% confidence
            should normalise it themselves (e.g. relative to the top score).
        """
        tokens = tokenize(text)
        if not tokens:
            return []
        scores: dict[str, float] = {}
        for account, counter in self._account_tokens.items():
            total = counter.total()
            score = sum(
                counter[t] / total * self._idf.get(t, 0.0) for t in tokens
            )
            if score:
                scores[account] = score
        return sorted(scores.items(), key=lambda item: item[1], reverse=True)
