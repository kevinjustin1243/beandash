"""JSON API.

This module contains the url endpoints of the JSON API that is used by the web
interface for asynchronous functionality.
"""

from __future__ import annotations

import logging
from abc import abstractmethod
from dataclasses import dataclass
from dataclasses import fields
from decimal import Decimal
from functools import wraps
from http import HTTPStatus
from inspect import Parameter
from inspect import signature
from pathlib import Path
from pprint import pformat
from typing import Any
from typing import TYPE_CHECKING

from flask import Blueprint
from flask import get_template_attribute
from flask import jsonify
from flask import request
from flask_babel import gettext

from fava.beans.funcs import hash_entry
from fava.context import g
from fava.core import EntryNotFoundForHashError
from fava.core.charts import DateAndBalance
from fava.core.conversion import AT_VALUE
from fava.core.documents import filepath_in_document_folder
from fava.core.documents import is_document_file
from fava.core.file import GeneratedEntryError
from fava.core.file import get_entry_slice
from fava.core.filters import FilterError
from fava.core.forecast import forecast
from fava.core.forecast import PROJECTED_SUFFIX
from fava.core.forecast import years_to_target
from fava.core.inventory import SimpleCounterInventory
from fava.core.inventory import ZERO
from fava.core.misc import align
from fava.core.query import QueryResultTable
from fava.helpers import FavaAPIError
from fava.internal_api import BalancesChart
from fava.internal_api import ChartApi
from fava.internal_api import get_errors
from fava.internal_api import get_ledger_data
from fava.serialisation import deserialise
from fava.serialisation import serialise
from fava.util.date import Month
from fava.util.live_prices import fetch_quotes

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable
    from collections.abc import Iterable
    from collections.abc import Mapping
    from collections.abc import Sequence
    from datetime import date

    from flask.wrappers import Response

    from fava.beans.abc import Directive
    from fava.core.charts import DateAndBalanceWithBudget
    from fava.core.insights import Insight
    from fava.core.query import QueryResultText
    from fava.core.tree import SerialisedTreeNode
    from fava.internal_api import ChartData
    from fava.util.date import DateRange
    from fava.util.live_prices import Quote


json_api = Blueprint("json_api", __name__)
log = logging.getLogger(__name__)


class ValidationError(Exception):
    """Validation of data failed."""


class MissingParameterValidationError(ValidationError):
    """Validation failed due to missing parameter."""

    def __init__(self, param: str) -> None:
        super().__init__(f"Parameter `{param}` is missing.")


class IncorrectTypeValidationError(ValidationError):
    """Validation failed due to incorrect type of parameter."""

    def __init__(self, param: str, expected: type) -> None:
        super().__init__(
            f"Parameter `{param}` of incorrect type - expected {expected}.",
        )


class InvalidJsonRequestError(ValidationError):
    """Validation failed due to invalid JSON in body."""

    def __init__(self) -> None:
        super().__init__("Invalid JSON body.")


def json_err(msg: str, status: HTTPStatus) -> Response:
    """Jsonify the error message."""
    res = jsonify({"error": msg})
    res.status = status
    return res


def json_success(data: Any) -> Response:
    """Jsonify the response."""
    return jsonify(
        {"data": data, "mtime": str(g.ledger.mtime)},
    )


class FavaJSONAPIError(FavaAPIError):
    """An error with a HTTPStatus."""

    @property
    @abstractmethod
    def status(self) -> HTTPStatus:
        """HTTP status that should be used for the response."""


class NotFoundError(FavaJSONAPIError):
    """Not found."""

    status = HTTPStatus.NOT_FOUND

    def __init__(self) -> None:
        super().__init__("Not found.")


class TargetPathAlreadyExistsError(FavaJSONAPIError):
    """The given path already exists."""

    status = HTTPStatus.CONFLICT

    def __init__(self, path: Path) -> None:
        super().__init__(f"{path} already exists.")


class DocumentDirectoryMissingError(FavaJSONAPIError):
    """No document directory was specified."""

    status = HTTPStatus.UNPROCESSABLE_ENTITY

    def __init__(self) -> None:
        super().__init__("You need to set a documents folder.")


class NoFileUploadedError(FavaJSONAPIError):
    """No file uploaded."""

    status = HTTPStatus.BAD_REQUEST

    def __init__(self) -> None:
        super().__init__("No file uploaded.")


class UploadedFileIsMissingFilenameError(FavaJSONAPIError):
    """Uploaded file is missing filename."""

    status = HTTPStatus.BAD_REQUEST

    def __init__(self) -> None:
        super().__init__("Uploaded file is missing filename.")


class NotAValidDocumentFileError(FavaJSONAPIError):
    """Not a valid document file."""

    status = HTTPStatus.BAD_REQUEST

    def __init__(self, filename: str) -> None:
        super().__init__(f"Not a valid document file: '{filename}'.")


@json_api.errorhandler(FavaAPIError)
def _(error: FavaAPIError) -> Response:
    log.error("Encountered FavaAPIError.", exc_info=error)
    return json_err(error.message, HTTPStatus.INTERNAL_SERVER_ERROR)


@json_api.errorhandler(FavaJSONAPIError)
def _(error: FavaJSONAPIError) -> Response:
    return json_err(error.message, error.status)


@json_api.errorhandler(FilterError)
def _(error: FilterError) -> Response:
    return json_err(error.message, HTTPStatus.BAD_REQUEST)


@json_api.errorhandler(OSError)
def _(error: OSError) -> Response:  # pragma: no cover
    log.error("Encountered OSError.", exc_info=error)
    return json_err(error.strerror or "", HTTPStatus.INTERNAL_SERVER_ERROR)


@json_api.errorhandler(ValidationError)
def _(error: ValidationError) -> Response:
    return json_err(f"Invalid API request: {error!s}", HTTPStatus.BAD_REQUEST)


@json_api.errorhandler(EntryNotFoundForHashError)
def _(error: EntryNotFoundForHashError) -> Response:
    return json_err(error.message, HTTPStatus.NOT_FOUND)


@json_api.errorhandler(GeneratedEntryError)
def _(error: GeneratedEntryError) -> Response:
    return json_err(error.message, HTTPStatus.UNPROCESSABLE_ENTITY)


def validate_func_arguments(
    func: Callable[..., Any],
) -> Callable[[Mapping[str, str]], list[str]] | None:
    """Validate arguments for a function.

    This currently only works for strings and lists (but only does a shallow
    validation for lists).

    Args:
        func: The function to check parameters for.

    Returns:
        A function, which takes a Mapping and tries to construct a list of
        positional parameters for the given function or None if the function
        has no parameters.
    """
    sig = signature(func)
    params: list[tuple[str, Any]] = []
    for param in sig.parameters.values():
        if param.annotation not in {"str", "list[Any]"}:  # pragma: no cover
            msg = (f"Type of param {param.name} needs to str or list",)
            raise ValueError(msg)
        if param.kind != Parameter.POSITIONAL_OR_KEYWORD:  # pragma: no cover
            msg2 = f"Param {param.name} should be positional"
            raise ValueError(msg2)
        params.append((param.name, str if param.annotation == "str" else list))

    if not params:
        return None

    def validator(mapping: Mapping[str, str]) -> list[str]:
        args: list[str] = []
        for param, type_ in params:
            val = mapping.get(param, None)
            if val is None:
                raise MissingParameterValidationError(param)
            if not isinstance(val, type_):
                raise IncorrectTypeValidationError(param, type_)
            args.append(val)
        return args

    return validator


def api_endpoint(func: Callable[..., Any]) -> Callable[[], Response]:
    """Register an API endpoint.

    The part of the function name up to the first underscore determines
    the accepted HTTP method. For GET and DELETE endpoints, the function
    parameters are extracted from the URL query string and passed to the
    decorated endpoint handler.
    """
    method, _, name = func.__name__.partition("_")  # ty:ignore[unresolved-attribute]
    if method not in {"get", "delete", "put"}:  # pragma: no cover
        msg = f"Invalid endpoint function name: {func.__name__}"  # ty:ignore[unresolved-attribute]
        raise ValueError(msg)
    validator = validate_func_arguments(func)

    @json_api.route(f"/{name}", methods=[method])
    @wraps(func)
    def _wrapper() -> Response:
        if validator is not None:
            if method == "put":
                request_json = request.get_json(silent=True)
                if request_json is None:
                    raise InvalidJsonRequestError
                data = request_json
            else:
                data = request.args
            res = func(*validator(data))
        else:
            res = func()
        return json_success(res)

    return _wrapper


@api_endpoint
def get_changed() -> bool:
    """Check for file changes."""
    return g.ledger.changed()


api_endpoint(get_errors)
api_endpoint(get_ledger_data)


@api_endpoint
def get_payee_accounts(payee: str) -> Sequence[str]:
    """Rank accounts for the given payee."""
    return g.ledger.attributes.payee_accounts(payee)


@api_endpoint
def get_suggest_accounts() -> Sequence[str]:
    """Suggest accounts based on the text of the payee/narration."""
    payee = request.args.get("payee", "")
    narration = request.args.get("narration", "")
    scored = g.ledger.suggest.suggest_accounts(f"{payee} {narration}")
    return [account for account, _score in scored]


@api_endpoint
def get_query(query_string: str) -> QueryResultTable | QueryResultText:
    """Run a Beancount query."""
    return g.ledger.query_shell.execute_query_serialised(
        g.filtered.entries_with_all_prices, query_string
    )


@dataclass(frozen=True)
class Context:
    """Context for an entry."""

    entry: Any
    balances_before: Mapping[str, Sequence[str]] | None
    balances_after: Mapping[str, Sequence[str]] | None


@api_endpoint
def get_context(entry_hash: str) -> Context:
    """Entry context."""
    entry, before, after = g.ledger.context(entry_hash)
    return Context(serialise(entry), before, after)


@dataclass(frozen=True)
class SourceSlice:
    """Source slice for an entry."""

    sha256sum: str
    slice: str


@api_endpoint
def get_source_slice(entry_hash: str) -> SourceSlice:
    """Entry slice."""
    entry = g.ledger.get_entry(entry_hash)
    source_slice, sha256sum = get_entry_slice(entry)
    return SourceSlice(sha256sum, source_slice)


@api_endpoint
def get_payee_transaction(payee: str) -> Any:
    """Last transaction for the given payee."""
    entry = g.ledger.attributes.payee_transaction(payee)
    return serialise(entry) if entry else None


@api_endpoint
def get_narration_transaction(narration: str) -> Any:
    """Last transaction for the given narration."""
    entry = g.ledger.attributes.narration_transaction(narration)
    return serialise(entry) if entry else None


@api_endpoint
def get_narrations() -> Sequence[str]:
    """List of all narrations in the ledger."""
    return g.ledger.attributes.narrations


@api_endpoint
def put_source_slice(entry_hash: str, source: str, sha256sum: str) -> str:
    """Write an entry source slice and return the updated sha256sum."""
    return g.ledger.file.save_entry_slice(entry_hash, source, sha256sum)


@api_endpoint
def put_format_source(source: str) -> str:
    """Format a beancount source slice (aligns currency columns)."""
    return align(source, g.ledger.fava_options.currency_column)


@api_endpoint
def delete_source_slice(entry_hash: str, sha256sum: str) -> str:
    """Delete an entry source slice."""
    g.ledger.file.delete_entry_slice(entry_hash, sha256sum)
    return f"Deleted entry {entry_hash}."


class FileDoesNotExistError(FavaAPIError):
    """The given file does not exist."""

    def __init__(self, filename: str) -> None:
        super().__init__(f"{filename} does not exist.")


@api_endpoint
def delete_document(filename: str) -> str:
    """Delete a document."""
    if not is_document_file(filename, g.ledger):
        raise NotAValidDocumentFileError(filename)

    file_path = Path(filename)
    if not file_path.exists():
        raise FileDoesNotExistError(filename)

    file_path.unlink()
    return f"Deleted {filename}."


@api_endpoint
def put_add_document() -> str:
    """Upload a document."""
    if not g.ledger.options["documents"]:
        raise DocumentDirectoryMissingError

    upload = request.files.get("file", None)

    if upload is None:
        raise NoFileUploadedError
    if not upload.filename:
        raise UploadedFileIsMissingFilenameError

    filepath = filepath_in_document_folder(
        request.form["folder"],
        request.form["account"],
        upload.filename,
        g.ledger,
    )

    if filepath.exists():
        raise TargetPathAlreadyExistsError(filepath)

    filepath.parent.mkdir(parents=True, exist_ok=True)
    upload.save(filepath)

    if request.form.get("hash"):
        g.ledger.file.insert_metadata(
            request.form["hash"],
            "document",
            filepath.name,
        )
    return f"Uploaded to {filepath}"


@api_endpoint
def put_attach_document(filename: str, entry_hash: str) -> str:
    """Attach a document to an entry."""
    g.ledger.file.insert_metadata(entry_hash, "document", filename)
    return f"Attached '{filename}' to entry."


@api_endpoint
def put_add_entries(entries: list[Any]) -> str:
    """Add multiple entries."""
    try:
        entries = [deserialise(entry) for entry in entries]
    except KeyError as error:  # pragma: no cover
        msg = f"KeyError: {error}"
        raise FavaAPIError(msg) from error

    g.ledger.file.insert_entries(entries)

    return f"Stored {len(entries)} entries."


########################################################################
# Reports


@api_endpoint
def get_journal() -> Sequence[Directive]:
    """Get all (filtered) entries."""
    g.ledger.changed()
    return [serialise(e) for e in g.filtered.entries]


@dataclass(frozen=True)
class JournalPage:
    """A rendered journal page."""

    page: int
    total_pages: int
    journal: str


@api_endpoint
def get_journal_page(page: str, order: str) -> JournalPage:
    """Get the HTML contents for a Journal page."""
    page_number = int(page)
    journal_table_contents = get_template_attribute(
        "_journal_table.html", "journal_table_contents"
    )
    if page == "1":
        g.ledger.changed()
    journal_page = g.filtered.paginate_journal(
        page_number, order="asc" if order == "asc" else "desc"
    )
    if journal_page is None:
        raise NotFoundError
    return JournalPage(
        page=page_number,
        total_pages=journal_page.total_pages,
        journal=journal_table_contents(journal_page.entries),
    )


@dataclass(frozen=True)
class Options:
    """Fava and Beancount options as strings."""

    fava_options: Mapping[str, str]
    beancount_options: Mapping[str, str]


@api_endpoint
def get_options() -> Options:
    """Get all options, rendered to strings for displaying in the frontend."""
    g.ledger.changed()

    fava_options = g.ledger.fava_options
    pprinted_fava_options = {
        field.name.replace("_", "-"): pformat(
            getattr(fava_options, field.name)
        )
        for field in fields(fava_options)
    }
    return Options(
        pprinted_fava_options,
        {key: str(value) for key, value in g.ledger.options.items()},
    )


@dataclass(frozen=True)
class CommodityPairWithPrices:
    """A pair of commodities and prices for them."""

    base: str
    quote: str
    prices: Sequence[tuple[date, Decimal]]


@api_endpoint
def get_commodities() -> Sequence[CommodityPairWithPrices]:
    """Get the prices for all commodity pairs."""
    g.ledger.changed()
    ret = []
    for base, quote in g.ledger.commodity_pairs():
        prices = g.filtered.prices(base, quote)
        if prices:
            ret.append(CommodityPairWithPrices(base, quote, prices))

    return ret


@dataclass(frozen=True)
class TreeReport:
    """Data for the tree reports."""

    date_range: DateRange | None
    charts: Sequence[ChartData]
    trees: Sequence[SerialisedTreeNode]


@api_endpoint
def get_income_statement() -> TreeReport:
    """Get the data for the income statement."""
    g.ledger.changed()
    options = g.ledger.options
    invert = g.ledger.fava_options.invert_income_liabilities_equity

    charts = [
        ChartApi.interval_totals(
            g.interval,
            (options["name_income"], options["name_expenses"]),
            label=gettext("Net Profit"),
            invert=invert,
        ),
        ChartApi.interval_totals(
            g.interval,
            options["name_income"],
            label=f"{gettext('Income')} ({g.interval.label})",
            invert=invert,
        ),
        ChartApi.interval_totals(
            g.interval,
            options["name_expenses"],
            label=f"{gettext('Expenses')} ({g.interval.label})",
        ),
    ]
    root_tree = g.filtered.root_tree
    trees = [
        root_tree.get(options["name_income"]),
        root_tree.net_profit(options, gettext("Net Profit")),
        root_tree.get(options["name_expenses"]),
    ]

    return TreeReport(
        g.filtered.date_range,
        charts,
        trees=[tree.serialise_with_context() for tree in trees],
    )


@api_endpoint
def get_balance_sheet() -> TreeReport:
    """Get the data for the balance sheet."""
    g.ledger.changed()
    options = g.ledger.options

    charts = [ChartApi.net_worth()]
    root_tree_closed = g.filtered.root_tree_closed
    trees = [
        root_tree_closed.get(options["name_assets"]),
        root_tree_closed.get(options["name_liabilities"]),
        root_tree_closed.get(options["name_equity"]),
    ]

    return TreeReport(
        g.filtered.date_range,
        charts,
        trees=[tree.serialise_with_context() for tree in trees],
    )


@dataclass(frozen=True)
class AllocationEntry:
    """One top-level Assets category, for the allocation tile grid."""

    account: str
    name: str
    balance: Decimal
    pct: float


@dataclass(frozen=True)
class DashboardReport:
    """Data for the dashboard."""

    date_range: DateRange | None
    charts: Sequence[ChartData]
    currency: str
    unrealized_gain: Decimal | None
    allocation: Sequence[AllocationEntry]
    liquid_cash: Decimal


def _allocation(
    assets_node: SerialisedTreeNode,
    currency: str,
) -> Sequence[AllocationEntry]:
    """Direct children of the Assets root, as shares of the total."""
    total = assets_node.balance_children.get(currency, ZERO)
    if total <= 0:
        return []
    entries = [
        AllocationEntry(
            account=child.account,
            name=child.account.rsplit(":", maxsplit=1)[-1],
            balance=balance,
            pct=float(balance / total),
        )
        for child in assets_node.children
        if (balance := child.balance_children.get(currency, ZERO)) > 0
    ]
    entries.sort(key=lambda entry: entry.balance, reverse=True)
    return entries


LIQUID_CASH_QUERY = """
SELECT currency, cost_currency, sum(number(units(position))) as amount
WHERE account_sortkey(account) ~ "^0"
GROUP BY currency, cost_currency
""".strip()


def _liquid_cash(currency: str) -> Decimal:
    """Plain (uncosted) balance of `currency` held directly in Assets.

    Uses a query scoped to Assets only (unlike `HOLDINGS_QUERY`, which
    also includes Liabilities) so this can't be dragged negative by an
    unrelated credit-card balance in the same currency.
    """
    result = g.ledger.query_shell.execute_query_serialised(
        g.filtered.entries_with_all_prices, LIQUID_CASH_QUERY
    )
    assert isinstance(result, QueryResultTable)  # noqa: S101
    return next(
        (
            amount
            for row_currency, cost_currency, amount in result.rows
            if row_currency == currency
            and cost_currency is None
            and isinstance(amount, Decimal)
        ),
        ZERO,
    )


@api_endpoint
def get_dashboard() -> DashboardReport:
    """Get the data for the dashboard."""
    g.ledger.changed()
    options = g.ledger.options

    net_worth_data = g.ledger.charts.net_worth(g.filtered, g.interval, g.conv)
    charts = [
        BalancesChart(
            gettext("Net Worth"),
            [*net_worth_data, *forecast(net_worth_data).points],
        ),
        ChartApi.hierarchy(options["name_assets"]),
    ]

    # Always valued at market price (regardless of the currently selected
    # chart conversion) so unrealized gain is meaningful even when viewing
    # the chart "at cost".
    currency = next(iter(options["operating_currency"]), "")
    assets_node = g.filtered.root_tree.get(options["name_assets"]).serialise(
        AT_VALUE,
        g.ledger.prices,
        g.filtered.end_date,
        with_cost=True,
    )
    unrealized_gain = None
    market = assets_node.balance_children.get(currency)
    cost = (
        assets_node.cost_children.get(currency)
        if assets_node.cost_children
        else None
    )
    if market is not None and cost is not None:
        unrealized_gain = market - cost

    return DashboardReport(
        g.filtered.date_range,
        charts,
        currency,
        unrealized_gain,
        _allocation(assets_node, currency),
        _liquid_cash(currency),
    )


def _totals_as_date_balance(
    totals: Iterable[DateAndBalanceWithBudget],
    *,
    negate: bool = False,
) -> list[DateAndBalance]:
    """Convert interval totals into plain (date, balance) points."""
    return [
        DateAndBalance(
            t.date,
            SimpleCounterInventory(
                {c: (-v if negate else v) for c, v in t.balance.items()},
            ),
        )
        for t in totals
    ]


#: Average number of days in a month, for annualised-rate-to-per-month
#: conversions (e.g. turning a forecast's daily trend into "$X/mo").
AVG_DAYS_PER_MONTH = Decimal("30.44")


@dataclass(frozen=True)
class Predictions:
    """Forecast-derived summary stats for the dashboard's forecast tiles."""

    currency: str
    net_worth: Decimal
    net_worth_projected: Decimal
    net_worth_r_squared: float
    net_worth_monthly_change: Decimal | None
    savings_rate: float | None
    spend_next_period: Decimal | None
    spend_trailing_monthly: Decimal
    cash_flow_90d: Decimal | None
    fi_target: Decimal
    fi_years: float | None


@api_endpoint
def get_predictions() -> Predictions:
    """Get forecast-derived stats: spend, cash flow, and FI target."""
    g.ledger.changed()
    options = g.ledger.options
    currency = next(iter(options["operating_currency"]), "")
    zero = Decimal(0)

    net_worth_data = g.ledger.charts.net_worth(g.filtered, Month, g.conv)
    net_worth_forecast = forecast(net_worth_data)
    nw_stats = net_worth_forecast.by_currency.get(currency)
    current_net_worth = (
        net_worth_data[-1].balance.get(currency, zero)
        if net_worth_data
        else zero
    )

    expense_totals = list(
        g.ledger.charts.interval_totals(
            g.filtered, Month, options["name_expenses"], g.conv
        ),
    )
    income_totals = list(
        g.ledger.charts.interval_totals(
            g.filtered, Month, options["name_income"], g.conv
        ),
    )
    expense_forecast = forecast(_totals_as_date_balance(expense_totals))
    income_forecast = forecast(
        _totals_as_date_balance(income_totals, negate=True),
    )
    expense_points = expense_forecast.points
    income_points = income_forecast.points
    has_expense_trend = currency in expense_forecast.by_currency
    has_income_trend = currency in income_forecast.by_currency

    key = f"{currency}{PROJECTED_SUFFIX}"

    spend_next_period = (
        expense_points[1].balance[key]
        if has_expense_trend and len(expense_points) > 1
        else None
    )

    cash_flow_90d = None
    if (
        has_expense_trend
        and has_income_trend
        and len(expense_points) > 3
        and len(income_points) > 3
    ):
        cash_flow_90d = sum(
            (
                income_points[i].balance[key] - expense_points[i].balance[key]
                for i in range(1, 4)
            ),
            zero,
        )

    trailing_expenses = [
        t.balance.get(currency, zero) for t in expense_totals[-12:]
    ]
    trailing_annual_spend = (
        (sum(trailing_expenses, zero) / len(trailing_expenses) * 12).quantize(
            Decimal("0.01")
        )
        if trailing_expenses
        else zero
    )
    fi_target = (trailing_annual_spend * 25).quantize(Decimal("0.01"))
    spend_trailing_monthly = (trailing_annual_spend / 12).quantize(
        Decimal("0.01"),
    )

    savings_rate = None
    trailing_income_6 = [
        -t.balance.get(currency, zero) for t in income_totals[-6:]
    ]
    trailing_expenses_6 = [
        t.balance.get(currency, zero) for t in expense_totals[-6:]
    ]
    total_income = sum(trailing_income_6, zero)
    total_expense = sum(trailing_expenses_6, zero)
    if total_income > 0:
        savings_rate = float((total_income - total_expense) / total_income)

    fi_years = (
        years_to_target(
            float(current_net_worth),
            float(nw_stats.daily_change),
            float(fi_target),
        )
        if nw_stats is not None
        else None
    )
    net_worth_monthly_change = (
        (nw_stats.daily_change * AVG_DAYS_PER_MONTH).quantize(Decimal("0.01"))
        if nw_stats is not None
        else None
    )

    return Predictions(
        currency=currency,
        net_worth=current_net_worth,
        net_worth_projected=nw_stats.projected if nw_stats else zero,
        net_worth_r_squared=nw_stats.r_squared if nw_stats else 0.0,
        net_worth_monthly_change=net_worth_monthly_change,
        savings_rate=savings_rate,
        spend_next_period=spend_next_period,
        spend_trailing_monthly=spend_trailing_monthly,
        cash_flow_90d=cash_flow_90d,
        fi_target=fi_target,
        fi_years=fi_years,
    )


@dataclass(frozen=True)
class UncategorizedTransaction:
    """A transaction still posted to the placeholder account.

    Includes suggested accounts to replace it.
    """

    entry: Any
    entry_hash: str
    placeholder_account: str
    suggestions: Sequence[tuple[str, float]]


@api_endpoint
def get_uncategorized_transaction() -> UncategorizedTransaction | None:
    """Find the most recent transaction still needing categorization.

    "Needing categorization" means it has a posting to the ledger's
    configured placeholder account (`uncategorized-account` fava-option,
    default `Expenses:Uncategorized`), together with suggested accounts
    to replace it with.
    """
    g.ledger.changed()
    placeholder = g.ledger.fava_options.uncategorized_account

    txn = None
    for candidate in reversed(g.ledger.all_entries_by_type.Transaction):
        if any(
            posting.account == placeholder for posting in candidate.postings
        ):
            txn = candidate
            break
    if txn is None:
        return None

    suggestions = g.ledger.suggest.suggest_accounts(
        f"{txn.payee or ''} {txn.narration}",
    )
    return UncategorizedTransaction(
        entry=serialise(txn),
        entry_hash=hash_entry(txn),
        placeholder_account=placeholder,
        suggestions=suggestions[:5],
    )


HOLDINGS_QUERY = """
SELECT
  currency,
  cost_currency,
  units(sum(position)) as units,
  first(getprice(currency, cost_currency)) as price,
  cost(sum(position)) as book_value,
  value(sum(position)) as market_value,
  safediv(
    (abs(sum(number(value(position)))) - abs(sum(number(cost(position))))),
    sum(number(cost(position)))
  ) * 100 as unrealized_profit_pct
WHERE account_sortkey(account) ~ "^[01]"
GROUP BY currency, cost_currency
ORDER BY currency, cost_currency
""".strip()

#: BQL only supports DISTINCT as a statement-level modifier, not inside an
#: aggregate function, so counting distinct accounts per holding isn't
#: possible in the same query above - this gets the distinct count across
#: the whole holdings universe instead, for a summary line rather than a
#: per-row breakdown.
ACCOUNT_COUNT_QUERY = """
SELECT DISTINCT account
WHERE account_sortkey(account) ~ "^[01]"
""".strip()


@dataclass(frozen=True)
class Holding:
    """A single commodity holding, aggregated across accounts."""

    currency: str
    cost_currency: str | None
    units: Decimal
    price: Decimal | None
    book_value: Decimal | None
    market_value: Decimal | None
    unrealized_profit_pct: Decimal


@dataclass(frozen=True)
class HoldingsReport:
    """Holdings aggregated by commodity, plus how many accounts hold them."""

    holdings: Sequence[Holding]
    account_count: int


def _as_inventory(value: object) -> SimpleCounterInventory:
    assert isinstance(value, SimpleCounterInventory)  # noqa: S101
    return value


@api_endpoint
def get_holdings() -> HoldingsReport:
    """Get holdings aggregated by commodity, for the richer holdings table."""
    g.ledger.changed()
    result = g.ledger.query_shell.execute_query_serialised(
        g.filtered.entries_with_all_prices, HOLDINGS_QUERY
    )
    assert isinstance(result, QueryResultTable)  # noqa: S101

    holdings = []
    for row in result.rows:
        (
            currency,
            cost_currency,
            units,
            price,
            book_value,
            market_value,
            pct,
        ) = row
        assert isinstance(currency, str)  # noqa: S101
        assert isinstance(pct, Decimal)  # noqa: S101
        cost_currency = (
            cost_currency if isinstance(cost_currency, str) else None
        )
        units_inventory = _as_inventory(units)
        book_inventory = _as_inventory(book_value)
        market_inventory = _as_inventory(market_value)
        holdings.append(
            Holding(
                currency=currency,
                cost_currency=cost_currency,
                units=units_inventory.get(currency, ZERO),
                price=price if isinstance(price, Decimal) else None,
                book_value=book_inventory.get(cost_currency, ZERO)
                if cost_currency
                else None,
                # market_value is left as None (rather than defaulting to
                # ZERO) when there's no recorded price to convert into the
                # cost currency, so "no data" isn't shown as "worthless".
                market_value=market_inventory.get(cost_currency)
                if cost_currency
                else None,
                unrealized_profit_pct=pct,
            ),
        )
    account_result = g.ledger.query_shell.execute_query_serialised(
        g.filtered.entries_with_all_prices, ACCOUNT_COUNT_QUERY
    )
    assert isinstance(account_result, QueryResultTable)  # noqa: S101

    return HoldingsReport(holdings, len(account_result.rows))


@api_endpoint
def get_live_prices(tickers: str) -> Mapping[str, Quote]:
    """Get live quotes for the given comma-separated ticker symbols.

    Assumes the ledger's commodity codes match Finnhub ticker symbols.
    Symbols Finnhub can't quote (or all of them, if FINNHUB_API_KEY is
    unset) are simply omitted from the result rather than erroring.
    """
    symbols = [ticker for ticker in tickers.split(",") if ticker]
    return fetch_quotes(symbols)


@api_endpoint
def get_insights() -> Sequence[Insight]:
    """Flag unusual transactions and newly-seen payees currently in view."""
    g.ledger.changed()
    return g.ledger.insights.insights(g.filtered.entries)


@api_endpoint
def get_trial_balance() -> TreeReport:
    """Get the data for the trial balance."""
    g.ledger.changed()

    trees = [g.filtered.root_tree.get("")]

    return TreeReport(
        g.filtered.date_range,
        charts=[],
        trees=[tree.serialise_with_context() for tree in trees],
    )


@dataclass(frozen=True)
class AccountBudget:
    """Budgets for an account."""

    budget: Mapping[str, Decimal]
    budget_children: Mapping[str, Decimal]


@dataclass(frozen=True)
class AccountReportJournal:
    """Data for the journal account report."""

    charts: Sequence[ChartData]
    journal: str


@dataclass(frozen=True)
class AccountReportTree:
    """Data for the tree account reports."""

    charts: Sequence[ChartData]
    interval_balances: Sequence[SerialisedTreeNode]
    budgets: Mapping[str, Sequence[AccountBudget]]
    dates: Sequence[DateRange]


@api_endpoint
def get_account_report() -> AccountReportJournal | AccountReportTree:
    """Get the data for the account report."""
    g.ledger.changed()

    account_name = request.args.get("a", "")
    subreport = request.args.get("r")

    charts = [
        ChartApi.account_balance(account_name),
        ChartApi.interval_totals(
            g.interval,
            account_name,
            label=gettext("Changes"),
        ),
    ]

    if subreport in {"changes", "balances"}:
        accumulate = subreport == "balances"
        interval_balances, dates = g.ledger.interval_balances(
            g.filtered,
            g.interval,
            account_name,
            accumulate=accumulate,
        )

        all_accounts = (
            interval_balances[0].accounts if interval_balances else []
        )
        budget_accounts = [
            a for a in all_accounts if a.startswith(account_name)
        ]
        budgets_mod = g.ledger.budgets
        first_date_range = dates[-1]
        budgets = {
            account: [
                AccountBudget(
                    budgets_mod.calculate(
                        account,
                        (first_date_range if accumulate else date_range).begin,
                        date_range.end,
                    ),
                    budgets_mod.calculate_children(
                        account,
                        (first_date_range if accumulate else date_range).begin,
                        date_range.end,
                    ),
                )
                for date_range in dates
            ]
            for account in budget_accounts
        }

        return AccountReportTree(
            charts,
            interval_balances=[
                tree.get(account_name).serialise(
                    g.conv,
                    g.ledger.prices,
                    date_range.end_inclusive,
                    with_cost=False,
                )
                for tree, date_range in zip(
                    interval_balances, dates, strict=True
                )
            ],
            dates=dates,
            budgets=budgets,
        )

    journal_table_contents = get_template_attribute(
        "_journal_table.html", "journal_table_contents"
    )
    entries = reversed(
        g.ledger.account_journal(
            g.filtered,
            account_name,
            g.conv,
            with_children=g.ledger.fava_options.account_journal_include_children,
        )
    )
    return AccountReportJournal(
        charts,
        journal=journal_table_contents(entries, show_change_and_balance=True),
    )
