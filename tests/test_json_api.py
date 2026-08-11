from __future__ import annotations

import datetime
from difflib import Differ
from http import HTTPStatus
from io import BytesIO
from pathlib import Path
from typing import Any
from typing import TYPE_CHECKING

import pytest

import fava.json_api
from fava.beans.funcs import hash_entry
from fava.context import g
from fava.core.file import get_entry_slice
from fava.core.misc import align
from fava.json_api import validate_func_arguments
from fava.json_api import ValidationError
from fava.util.live_prices import Quote

if TYPE_CHECKING:  # pragma: no cover
    from flask import Flask
    from flask.testing import FlaskClient
    from werkzeug.test import TestResponse

    from fava.core import FavaLedger

    from .conftest import GetFavaLedger
    from .conftest import SnapshotFunc


def diff_strings(a: str, b: str) -> list[str]:
    """Diff two strings and return the list of differing lines."""
    differ = Differ()
    return [
        line
        for line in differ.compare(a.splitlines(), b.splitlines())
        if line.startswith(("+", "-"))
    ]


def test_validate_get_args() -> None:
    def noparams() -> None:
        pass

    assert validate_func_arguments(noparams) is None

    def func(test: str) -> None:
        assert test
        assert isinstance(test, str)

    validator = validate_func_arguments(func)
    assert validator
    with pytest.raises(ValidationError):
        validator({"notest": "value"})
    assert validator({"test": "value"}) == ["value"]


def assert_api_error(
    response: TestResponse,
    msg: str | None = None,
    status: HTTPStatus = HTTPStatus.INTERNAL_SERVER_ERROR,
) -> str:
    """Asserts that the response errored and contains the message."""
    assert response.status_code == status.value
    assert response.json
    err_msg = response.json["error"]
    assert isinstance(err_msg, str)
    if msg:
        assert msg == err_msg
    return err_msg


def assert_api_success(response: TestResponse, data: Any | None = None) -> Any:
    """Asserts that the request was successful and contains the data."""
    assert response.status_code == HTTPStatus.OK.value
    assert response.json
    if data is not None:
        assert data == response.json["data"]
    return response.json["data"]


def test_api_changed(test_client: FlaskClient) -> None:
    response = test_client.get("/long-example/api/changed")
    assert_api_success(response, data=False)


def test_api_add_document_and_delete(
    app: Flask,
    test_client: FlaskClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    add_url = "/long-example/api/add_document"
    get_url = "/long-example/document/"
    delete_url = "/long-example/api/document"
    account = "Expenses:Food:Restaurant"
    account_dir = tmp_path / "Expenses" / "Food" / "Restaurant"

    def _data(
        filename: str,
    ) -> dict[str, str | tuple[BytesIO, str]]:
        return {
            "folder": str(tmp_path),
            "account": account,
            "file": (BytesIO(b"asdfasdf"), filename),
        }

    with app.test_request_context("/long-example/"):
        app.preprocess_request()

        # error when no documents dir is set
        monkeypatch.setitem(g.ledger.options, "documents", [])  # ty:ignore[invalid-argument-type]

        response = test_client.put(add_url)
        assert_api_error(
            response,
            "You need to set a documents folder.",
            HTTPStatus.UNPROCESSABLE_ENTITY,
        )

        # upload to temporary directory
        monkeypatch.setitem(g.ledger.options, "documents", [str(tmp_path)])  # ty:ignore[invalid-argument-type]

        response = test_client.put(add_url)
        assert_api_error(response, "No file uploaded.", HTTPStatus.BAD_REQUEST)

        response = test_client.put(add_url, data=_data(""))
        assert_api_error(
            response,
            "Uploaded file is missing filename.",
            HTTPStatus.BAD_REQUEST,
        )

        filename = account_dir / "2015-12-12 test"
        assert not filename.exists()
        response = test_client.put(add_url, data=_data("2015-12-12 test"))
        assert_api_success(response, f"Uploaded to {filename}")
        assert filename.read_text() == "asdfasdf"
        assert filename.is_file()

        response = test_client.get(
            get_url, query_string={"filename": str(filename)}
        )
        assert response.status_code == HTTPStatus.OK.value
        assert response.get_data() == b"asdfasdf"

        response = test_client.put(add_url, data=_data("2015-12-12 test"))
        assert_api_error(
            response, f"{filename} already exists.", HTTPStatus.CONFLICT
        )

        # delete
        invalid_filename = tmp_path.parent / "asdf"
        response = test_client.delete(
            delete_url,
            query_string={"filename": str(invalid_filename)},
        )
        assert_api_error(
            response,
            f"Not a valid document file: '{invalid_filename}'.",
            HTTPStatus.BAD_REQUEST,
        )

        missing_filename = account_dir / "does-not-exist"
        response = test_client.delete(
            delete_url,
            query_string={"filename": str(missing_filename)},
        )
        assert_api_error(response, f"{missing_filename} does not exist.")

        response = test_client.delete(
            delete_url,
            query_string={"filename": str(filename)},
        )
        assert_api_success(response, f"Deleted {filename}.")


def test_api_errors(test_client: FlaskClient, snapshot: SnapshotFunc) -> None:
    response = test_client.get("/long-example/api/errors")
    assert_api_success(response, [])
    response = test_client.get("/errors/api/errors")
    data = assert_api_success(response)

    def get_message(err: Any) -> str:
        return str(err["message"])

    snapshot(sorted(data, key=get_message), json=True)


def test_api_context(
    test_client: FlaskClient,
    snapshot: SnapshotFunc,
    example_ledger: FavaLedger,
) -> None:
    response = test_client.get("/long-example/api/context")
    assert_api_error(
        response,
        "Invalid API request: Parameter `entry_hash` is missing.",
        HTTPStatus.BAD_REQUEST,
    )

    response = test_client.get(
        "/long-example/api/context",
        query_string={"entry_hash": "not_found"},
    )
    assert_api_error(
        response,
        'No entry found for hash "not_found"',
        HTTPStatus.NOT_FOUND,
    )

    balance_entry_hash = hash_entry(
        example_ledger.all_entries_by_type.Balance[0]
    )
    response = test_client.get(
        "/long-example/api/context",
        query_string={"entry_hash": balance_entry_hash},
    )
    data = assert_api_success(response)
    assert data["balances_before"]
    assert not data["balances_after"]

    entry_hash = hash_entry(
        next(
            entry
            for entry in example_ledger.all_entries_by_type.Transaction
            if entry.narration == r"Investing 40% of cash in VBMPX"
            and entry.date == datetime.date(2016, 5, 9)
        ),
    )

    response = test_client.get(
        "/long-example/api/context",
        query_string={"entry_hash": entry_hash},
    )
    data = assert_api_success(response)
    snapshot(data, json=True)
    response = test_client.get(
        "/long-example/api/source_slice",
        query_string={"entry_hash": entry_hash},
    )
    data = assert_api_success(response)
    snapshot(data, json=True)

    entry_hash = hash_entry(example_ledger.all_entries[10])
    response = test_client.get(
        "/long-example/api/context",
        query_string={"entry_hash": entry_hash},
    )
    data = assert_api_success(response)
    snapshot(data, json=True)
    assert not data.get("balances_before")
    response = test_client.get(
        "/long-example/api/source_slice",
        query_string={"entry_hash": entry_hash},
    )
    data = assert_api_success(response)
    snapshot(data, json=True)


def test_api_payee_accounts(
    test_client: FlaskClient,
    snapshot: SnapshotFunc,
) -> None:
    response = test_client.get("/long-example/api/payee_accounts")
    assert_api_error(response, status=HTTPStatus.BAD_REQUEST)

    response = test_client.get(
        "/long-example/api/payee_accounts",
        query_string={"payee": "EDISON POWER"},
    )
    data = assert_api_success(response)
    assert data[0] == "Assets:US:BofA:Checking"
    assert data[1] == "Expenses:Home:Electricity"
    snapshot(data, json=True)


def test_api_dashboard_unrealized_gain(test_client: FlaskClient) -> None:
    response = test_client.get("/long-example/api/dashboard")
    data = assert_api_success(response)
    assert data["currency"] == "USD"
    assert data["unrealized_gain"] is not None
    assert data["allocation"]
    assert sum(entry["pct"] for entry in data["allocation"]) <= 1.0
    # Sorted descending by balance.
    balances = [entry["balance"] for entry in data["allocation"]]
    assert balances == sorted(balances, reverse=True)
    # Only counts cash held directly in Assets - unaffected by the
    # Liabilities:US:Chase:Slate credit card balance in the same currency.
    assert 0 < data["liquid_cash"] < sum(balances)

    # Narrowing to a period with no assets in USD at all: unrealized gain
    # and allocation can't be computed, but this shouldn't error.
    response = test_client.get(
        "/long-example/api/dashboard", query_string={"time": "1990"}
    )
    data = assert_api_success(response)
    assert data["unrealized_gain"] is None
    assert data["allocation"] == []
    assert data["liquid_cash"] == 0

    # A period whose plain-USD Assets balance nets to exactly zero (funded,
    # then fully spent on commodity purchases).
    response = test_client.get(
        "/long-example/api/dashboard", query_string={"time": "2000"}
    )
    data = assert_api_success(response)
    assert data["allocation"]
    assert data["liquid_cash"] == 0
    assert data["liquid_cash"] == 0


def test_api_suggest_accounts(test_client: FlaskClient) -> None:
    # Neither payee nor narration is required - e.g. while a new payee is
    # still being typed and no narration has been entered yet.
    response = test_client.get("/long-example/api/suggest_accounts")
    assert_api_success(response, [])

    response = test_client.get(
        "/long-example/api/suggest_accounts",
        query_string={
            "payee": "My Bank",
            "narration": "monthly banking fee charge",
        },
    )
    data = assert_api_success(response)
    assert data[0] == "Expenses:Financial:Fees"


def test_api_insights(test_client: FlaskClient) -> None:
    response = test_client.get("/long-example/api/insights")
    data = assert_api_success(response)
    assert data
    assert all(
        item.keys()
        == {"type", "payee", "title", "detail", "value", "tone", "entry_hash"}
        for item in data
    )
    assert all(
        item["type"] in {"new_payee", "unusual_transaction"} for item in data
    )
    assert all(item["tone"] in {"amber", "red"} for item in data)

    # Narrowing to a period with no transactions at all: nothing flagged.
    response = test_client.get(
        "/long-example/api/insights", query_string={"time": "1990"}
    )
    assert_api_success(response, [])


def test_api_predictions(test_client: FlaskClient) -> None:
    response = test_client.get("/long-example/api/predictions")
    data = assert_api_success(response)
    assert data.keys() == {
        "currency",
        "net_worth",
        "net_worth_projected",
        "net_worth_r_squared",
        "net_worth_monthly_change",
        "savings_rate",
        "spend_next_period",
        "spend_trailing_monthly",
        "cash_flow_90d",
        "fi_target",
        "fi_years",
    }
    assert data["currency"] == "USD"
    assert isinstance(data["net_worth_r_squared"], float)
    assert data["fi_target"] is not None
    assert data["spend_trailing_monthly"] is not None
    assert data["net_worth_monthly_change"] is not None

    # Narrowing to a period with no transactions at all: everything about
    # the (nonexistent) trend is empty/unknown, but this shouldn't error.
    response = test_client.get(
        "/long-example/api/predictions", query_string={"time": "1990"}
    )
    data = assert_api_success(response)
    assert data["savings_rate"] is None
    assert data["fi_years"] is None
    assert data["net_worth_monthly_change"] is None


def test_api_goals(test_client: FlaskClient) -> None:
    response = test_client.get("/long-example/api/goals")
    data = assert_api_success(response)
    assert len(data) == 4
    by_label = {goal["label"]: goal for goal in data}

    assert by_label.keys() == {
        "Emergency fund",
        "Pay off Slate card",
        "Brokerage cash",
        "Someday fund",
    }
    for goal in data:
        assert goal.keys() == {
            "account",
            "label",
            "target",
            "currency",
            "target_date",
            "balance",
            "pct_complete",
            "is_payoff",
            "eta_years",
            "on_track",
        }

    # A savings goal: balance / target, straightforwardly.
    savings = by_label["Emergency fund"]
    assert savings["account"] == "Assets:US:BofA:Checking"
    assert savings["is_payoff"] is False
    assert savings["target"] == 5000.0
    assert savings["balance"] == 1632.79
    assert savings["pct_complete"] == pytest.approx(1632.79 / 5000)
    # The account's recent trend isn't headed toward the target, so there's
    # no ETA - and therefore nothing to call "on track".
    assert savings["eta_years"] is None
    assert savings["on_track"] is False

    # A payoff goal against a liability: Chase:Slate's debt has actually
    # grown since the goal's declared date in this fixture (a revolving
    # card, not a loan being paid down), so progress is clamped at 0%
    # rather than going negative.
    payoff = by_label["Pay off Slate card"]
    assert payoff["account"] == "Liabilities:US:Chase:Slate"
    assert payoff["is_payoff"] is True
    assert payoff["target"] == 0.0
    assert payoff["balance"] == 2935.65
    assert payoff["pct_complete"] == 0.0

    # A savings goal whose account has a genuine favourable trend gets a
    # real ETA, and is "on track" since that ETA lands before the target
    # date.
    on_track_goal = by_label["Brokerage cash"]
    assert on_track_goal["account"] == "Assets:US:ETrade:Cash"
    assert on_track_goal["eta_years"] == pytest.approx(0.7939889675879936)
    assert on_track_goal["on_track"] is True

    # A goal with no target date has nothing to be "on track" against -
    # progress is still shown, just no ETA verdict.
    no_date_goal = by_label["Someday fund"]
    assert no_date_goal["target_date"] is None
    assert no_date_goal["on_track"] is None

    # A ledger with no `custom "goal"` directives returns an empty list,
    # not an error.
    response = test_client.get("/example/api/goals")
    assert_api_success(response, [])


def test_api_uncategorized_transaction(
    test_client: FlaskClient,
    app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # long-example.beancount has no postings to the default placeholder
    # account, so there's nothing to categorize.
    response = test_client.get("/long-example/api/uncategorized_transaction")
    assert_api_success(response, None)

    # Point the placeholder at an account that does have postings. In
    # real usage `uncategorized_account` is a beancount custom-option
    # parsed once per `load_file()`, in the same pass that rebuilds the
    # suggester's index - so re-run that here too, rather than leaving
    # the index built against the (unpatched) default placeholder.
    with app.test_request_context("/long-example/"):
        app.preprocess_request()
        monkeypatch.setattr(
            g.ledger.fava_options,
            "uncategorized_account",
            "Expenses:Financial:Fees",
        )
        g.ledger.suggest.load_file()

        response = test_client.get(
            "/long-example/api/uncategorized_transaction",
        )
        data = assert_api_success(response)
        assert data["placeholder_account"] == "Expenses:Financial:Fees"
        assert data["entry"]["payee"] == "BANK FEES"
        assert data["suggestions"]
        # The placeholder account itself is never suggested as a
        # replacement for itself - the funding account is the next best
        # match instead.
        assert data["suggestions"][0][0] == "Assets:US:BofA:Checking"
        assert all(
            account != "Expenses:Financial:Fees"
            for account, _score in data["suggestions"]
        )


def test_api_holdings(
    test_client: FlaskClient,
    snapshot: SnapshotFunc,
) -> None:
    response = test_client.get("/long-example/api/holdings")
    data = assert_api_success(response)
    assert data["account_count"] > 0
    by_currency = {
        holding["currency"]: holding for holding in data["holdings"]
    }

    # A holding with a recorded price: units/book/market value and percent
    # gain are all populated.
    itot = by_currency["ITOT"]
    assert itot["cost_currency"] == "USD"
    assert itot["price"] == 92.68
    assert itot["market_value"] is not None

    # ABC has cost basis but no recorded price for it, so market_value
    # can't be computed - it should be omitted rather than shown as 0.
    abc = by_currency["ABC"]
    assert abc["price"] is None
    assert abc["market_value"] is None
    assert abc["book_value"] is not None

    # USD itself is held directly (no cost basis / cost currency).
    usd = by_currency["USD"]
    assert usd["cost_currency"] is None
    assert usd["book_value"] is None

    snapshot(data, json=True)


def test_api_live_prices(
    test_client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_fetch_quotes(symbols: list[str]) -> dict[str, Quote]:
        assert symbols == ["AAPL", "MSFT"]
        return {"AAPL": Quote(price=210.0, day_change_pct=1.5, as_of=42)}

    monkeypatch.setattr(fava.json_api, "fetch_quotes", fake_fetch_quotes)

    response = test_client.get(
        "/long-example/api/live_prices",
        query_string={"tickers": "AAPL,MSFT"},
    )
    data = assert_api_success(response)
    assert data == {
        "AAPL": {"price": 210.0, "day_change_pct": 1.5, "as_of": 42},
    }


def test_api_payee_transaction(
    test_client: FlaskClient,
    snapshot: SnapshotFunc,
) -> None:
    response = test_client.get(
        "/long-example/api/payee_transaction",
        query_string={"payee": "EDISON POWER"},
    )
    data = assert_api_success(response)
    snapshot(data, json=True)


def test_api_narration_transaction(
    test_client: FlaskClient,
) -> None:
    response = test_client.get(
        "/long-example/api/narration_transaction",
        query_string={"narration": "Buying groceries"},
    )
    data = assert_api_success(response)
    assert data["date"] == "2016-04-21"
    assert data["narration"] == "Buying groceries"
    assert data["payee"] == "Farmer Fresh"
    assert len(data["postings"]) == 2
    assert data["t"] == "Transaction"


def test_api_get_source_slice_unprocessable(
    test_client: FlaskClient, get_ledger: GetFavaLedger
) -> None:
    generated_open_entry = get_ledger("edit-example").all_entries[0]
    entry_hash = hash_entry(generated_open_entry)
    response = test_client.get(
        "/edit-example/api/source_slice",
        query_string={"entry_hash": entry_hash},
    )
    assert_api_error(
        response,
        status=HTTPStatus.UNPROCESSABLE_ENTITY,
    )


def test_api_source_slice_and_insert_metadata(app_in_tmp_dir: Flask) -> None:
    test_client = app_in_tmp_dir.test_client()
    ledger = app_in_tmp_dir.config["LEDGERS"]["edit-example"]
    path = Path(ledger.beancount_file_path)

    source = path.read_text("utf-8")

    # get entry context and update an entry slice
    first_txn = next(e for e in ledger.all_entries if hasattr(e, "postings"))
    assert first_txn.payee == "Kin Soy"
    entry_hash = hash_entry(first_txn)
    response = test_client.get(
        "/edit-example/api/source_slice",
        query_string={"entry_hash": entry_hash},
    )
    data = assert_api_success(response)
    assert "Kin Soy" in data["slice"]

    response = test_client.put(
        "/edit-example/api/source_slice",
        json={
            "entry_hash": entry_hash,
            "sha256sum": data["sha256sum"],
            "source": data["slice"].replace("Kin Soy", "Lorem Ipsum"),
        },
    )
    assert_api_success(response)
    assert diff_strings(source, path.read_text("utf-8")) == [
        '- 2014-01-04 * "Kin Soy" "Eating out with Sue"',
        '+ 2014-01-04 * "Lorem Ipsum" "Eating out with Sue"',
    ]
    ledger.load_file()
    first_txn = next(e for e in ledger.all_entries if hasattr(e, "postings"))
    assert first_txn.payee == "Lorem Ipsum"
    entry_hash = hash_entry(first_txn)

    response = test_client.put(
        "/edit-example/api/attach_document",
        json={
            "entry_hash": entry_hash,
            "filename": "edit-example.beancount",
        },
    )
    assert_api_success(response)
    assert diff_strings(source, path.read_text("utf-8")) == [
        '- 2014-01-04 * "Kin Soy" "Eating out with Sue"',
        '+ 2014-01-04 * "Lorem Ipsum" "Eating out with Sue"',
        '+   document: "edit-example.beancount"',
    ]

    ledger.load_file()
    first_txn = next(e for e in ledger.all_entries if hasattr(e, "postings"))
    assert first_txn.payee == "Lorem Ipsum"
    entry_hash = hash_entry(first_txn)

    ledger.options["documents"] = [str(path.parent)]
    target_path = (
        path.parent
        / "Expenses"
        / "Food"
        / "Restaurant"
        / "2022-12-12 asdf.txt"
    )
    response = test_client.put(
        "/edit-example/api/add_document",
        data={
            "folder": str(path.parent),
            "account": "Expenses:Food:Restaurant",
            "file": (BytesIO(b"asdfasdf"), "2022-12-12 asdf.txt"),
            "hash": entry_hash,
        },
    )
    assert_api_success(response)
    assert target_path.exists()
    assert diff_strings(source, path.read_text("utf-8")) == [
        '- 2014-01-04 * "Kin Soy" "Eating out with Sue"',
        '+ 2014-01-04 * "Lorem Ipsum" "Eating out with Sue"',
        '+   document-2: "2022-12-12 asdf.txt"',
        '+   document: "edit-example.beancount"',
    ]


def test_api_format_source(
    test_client: FlaskClient,
    example_ledger: FavaLedger,
) -> None:
    path = Path(example_ledger.beancount_file_path)
    url = "/long-example/api/format_source"

    response = test_client.put(url)
    assert_api_error(
        response,
        "Invalid API request: Invalid JSON body.",
        HTTPStatus.BAD_REQUEST,
    )

    payload = path.read_text("utf-8")

    response = test_client.put(url, json={"source": payload})
    assert_api_success(response, align(payload, 61))


def test_api_format_source_options(
    app: Flask,
    test_client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with app.test_request_context("/long-example/"):
        app.preprocess_request()
        path = Path(g.ledger.beancount_file_path)
        payload = path.read_text("utf-8")

        monkeypatch.setattr(g.ledger.fava_options, "currency_column", 90)

        response = test_client.put(
            "/long-example/api/format_source",
            json={"source": payload},
        )
        assert_api_success(response, align(payload, 90))


def test_api_source_slice_delete(app_in_tmp_dir: Flask) -> None:
    test_client = app_in_tmp_dir.test_client()
    ledger = app_in_tmp_dir.config["LEDGERS"]["edit-example"]
    path = Path(ledger.beancount_file_path)

    contents = path.read_text("utf-8")
    assert '2016-05-03 * "Chichipotle" "Eating out with Joe"' in contents

    url = "/edit-example/api/source_slice"
    # test bad request
    response = test_client.delete(url)
    assert_api_error(
        response,
        "Invalid API request: Parameter `entry_hash` is missing.",
        HTTPStatus.BAD_REQUEST,
    )

    entry = ledger.all_entries[-1]
    entry_hash = hash_entry(entry)
    _entry_source, sha256sum = get_entry_slice(entry)

    # delete entry
    response = test_client.delete(
        url,
        query_string={"entry_hash": entry_hash, "sha256sum": sha256sum},
    )
    assert_api_success(response, f"Deleted entry {entry_hash}.")
    assert (
        '2016-05-03 * "Chichipotle" "Eating out with Joe"'
        not in path.read_text("utf-8")
    )


def test_api_add_entries(
    app: Flask,
    test_client: FlaskClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with app.test_request_context("/long-example/"):
        app.preprocess_request()
        test_file = tmp_path / "test_file"
        test_file.touch()
        monkeypatch.setattr(g.ledger, "beancount_file_path", str(test_file))

        entries = [
            {
                "t": "Transaction",
                "date": "2017-12-12",
                "flag": "*",
                "payee": "Test3",
                "tags": [],
                "links": [],
                "narration": "",
                "meta": {},
                "postings": [
                    {"account": "Assets:US:ETrade:Cash", "amount": "100 USD"},
                    {"account": "Assets:US:ETrade:GLD"},
                ],
            },
            {
                "t": "Transaction",
                "date": "2017-01-12",
                "flag": "*",
                "payee": "Test1",
                "tags": [],
                "links": [],
                "narration": "",
                "meta": {},
                "postings": [
                    {"account": "Assets:US:ETrade:Cash", "amount": "100 USD"},
                    {"account": "Assets:US:ETrade:GLD"},
                ],
            },
            {
                "t": "Transaction",
                "date": "2017-02-12",
                "flag": "*",
                "payee": "Test",
                "tags": [],
                "links": [],
                "narration": "Test",
                "meta": {},
                "postings": [
                    {"account": "Assets:US:ETrade:Cash", "amount": "100 USD"},
                    {"account": "Assets:US:ETrade:GLD"},
                ],
            },
        ]

        url = "/long-example/api/add_entries"

        err = test_client.put(url, json={"entries": "string"})
        assert_api_error(
            err,
            "Invalid API request: Parameter `entries`"
            " of incorrect type - expected <class 'list'>.",
            HTTPStatus.BAD_REQUEST,
        )

        response = test_client.put(url, json={"entries": entries})
        assert_api_success(response, "Stored 3 entries.")

        assert (
            test_file.read_text("utf-8")
            == """
2017-01-12 * "Test1" ""
  Assets:US:ETrade:Cash                                 100 USD
  Assets:US:ETrade:GLD

2017-02-12 * "Test" "Test"
  Assets:US:ETrade:Cash                                 100 USD
  Assets:US:ETrade:GLD

2017-12-12 * "Test3" ""
  Assets:US:ETrade:Cash                                 100 USD
  Assets:US:ETrade:GLD
"""
        )


@pytest.mark.parametrize(
    ("query_string", "name"),
    [
        ("balances from year = 2014", "balances"),
        ("select sum(day)", "sum"),
        ("journal from year = 2014 and month = 1", "journal"),
        (
            "select day, position, units(position), balance, payee, tags"
            " from year = 2014 and month = 1",
            "misc",
        ),
        (".help", "help"),
    ],
)
def test_api_query_result(
    query_string: str,
    name: str,
    test_client: FlaskClient,
    snapshot: SnapshotFunc,
) -> None:
    response = test_client.get(
        "/long-example/api/query",
        query_string={"query_string": query_string},
    )
    data = assert_api_success(response)
    snapshot(data, name=name, json=True)


def test_api_query_result_types(
    test_client: FlaskClient,
) -> None:
    query_string = (
        "select day, position, units(position), balance, payee, tags, "
        "entry, meta from year = 2014 and month = 1"
    )
    response = test_client.get(
        "/long-example/api/query",
        query_string={"query_string": query_string},
    )
    assert_api_success(response)


def test_api_query_result_error(test_client: FlaskClient) -> None:
    response = test_client.get(
        "/long-example/api/query",
        query_string={"query_string": "nononono"},
    )
    msg = assert_api_error(response)
    assert "Query parse error: syntax error" in msg


def test_api_commodities_empty(
    test_client: FlaskClient,
) -> None:
    response = test_client.get(
        "/long-example/api/commodities?time=3000",
    )
    data = assert_api_success(response)
    assert not data


def test_api_journal_page_not_found(
    test_client: FlaskClient,
) -> None:
    response = test_client.get(
        "/long-example/api/journal_page?page=1000&order=desc"
    )
    assert_api_error(response, status=HTTPStatus.NOT_FOUND)


def test_api_filter_error(
    test_client: FlaskClient,
) -> None:
    response = test_client.get(
        "/long-example/api/commodities?time=20",
    )
    assert_api_error(response, status=HTTPStatus.BAD_REQUEST)


@pytest.mark.parametrize(
    ("name", "url"),
    [
        ("commodities", "/long-example/api/commodities"),
        ("journal", "/example/api/journal"),
        ("income_statement", "/long-example/api/income_statement?time=2014"),
        ("narrations", "/long-example/api/narrations"),
        ("trial_balance", "/long-example/api/trial_balance?time=2014"),
        ("balance_sheet", "/long-example/api/balance_sheet"),
        (
            "balance_sheet_with_cost",
            "/long-example/api/balance_sheet?conversion=at_value",
        ),
        ("dashboard", "/long-example/api/dashboard"),
        (
            "account_report_off_by_one_journal",
            (
                "/off-by-one/api/account_report"
                "?interval=day&conversion=at_value&a=Assets"
            ),
        ),
        (
            "account_report_off_by_one",
            (
                "/off-by-one/api/account_report"
                "?interval=day&conversion=at_value&a=Assets&r=balances"
            ),
        ),
        ("options", "/long-example/api/options"),
    ],
)
def test_api(
    test_client: FlaskClient,
    snapshot: SnapshotFunc,
    name: str,
    url: str,
) -> None:
    response = test_client.get(url)
    data = assert_api_success(response)
    assert data
    snapshot(data, name=name, json=True)
