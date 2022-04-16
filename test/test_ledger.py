from datetime import date
from decimal import Decimal

import pytest
from plutus.ledger import (
    Account,
    AccountCategory,
    CommodityAmount,
    DATE_FORMAT,
    Entry,
    Transaction,
    TransactionStatus,
    USD,
)


@pytest.fixture
def zero_dollars():
    return USD(Decimal(0))


@pytest.fixture
def five_dollars():
    return USD(Decimal(5))


@pytest.fixture
def ten_dollars():
    return USD(Decimal("10.00"))


@pytest.fixture
def less_ten_dollars():
    return USD(Decimal("-10.00"))


def test_usd_class(zero_dollars):
    assert f"{zero_dollars}" == "$0.00"
    large = USD(Decimal(123456.7800))
    assert f"{large}" == "$123,456.78"


@pytest.fixture
def asset():
    return Account("Assets:MyBank:Checking")


@pytest.fixture
def equity():
    return Account("Equity:Opening Balance")


@pytest.fixture
def expense():
    return Account("Expenses:Fine Wines")


@pytest.fixture
def income():
    return Account("Income:Salary:Acme Corp")


@pytest.fixture
def liability():
    return Account("Liabilities:Loans:Mortgage")


def test_accounts(asset, equity, expense, income, liability):
    assert f"{asset}" == asset.name
    assert asset.category == AccountCategory.ASSETS
    assert equity.category == AccountCategory.EQUITY
    assert expense.category == AccountCategory.EXPENSES
    assert income.category == AccountCategory.INCOME
    assert liability.category == AccountCategory.LIABILITIES


@pytest.fixture
def pie():
    return CommodityAmount(amount=Decimal("3.14"), commodity="PIES")


def test_commodity_amount_str(pie):
    assert f"{pie}" == "3.14 PIES"


def test_commodity_amount_add_and_multiply(pie):
    assert pie + pie == pie * 2
    assert pie + pie == 2 * pie


def test_incompatible_commodities_error(pie):
    with pytest.raises(TypeError):
        pie + 4
    with pytest.raises(ValueError):
        pie + CommodityAmount(Decimal(5), "APPLES")


def test_simple_entry(asset):
    entry = Entry(account=asset)


@pytest.fixture
def post_date():
    return date(2022, 4, 1)


def test_complex_entry(asset, pie, five_dollars, ten_dollars, post_date):
    entry = Entry(
        account=asset,
        status=TransactionStatus.CLEARED,
        amount=pie,
        lot_price=five_dollars,
        lot_date=post_date,
        purchase_price=ten_dollars,
    )
    s = (
        f"* {asset}   {pie} {{{five_dollars}}} "
        f"[{post_date.strftime(DATE_FORMAT)}] @ {ten_dollars}"
    )
    assert f"{entry}" == s


@pytest.fixture
def effective_date():
    return date(2022, 4, 3)


@pytest.fixture
def full_transaction(
    asset, expense, liability, less_ten_dollars, five_dollars, post_date, effective_date
):
    code = "#101"
    entry1 = Entry(account=asset, amount=less_ten_dollars)
    entry2 = Entry(account=expense, amount=five_dollars)
    entry3 = Entry(account=liability, amount=five_dollars)
    return Transaction(
        post_date=post_date,
        description="Test transaction",
        entries=frozenset({entry1, entry2, entry3}),
        effective_date=effective_date,
        status=TransactionStatus.CLEARED,
        code=code,
    )


def test_complex_transaction_str(full_transaction, post_date, effective_date):
    ts = f"{full_transaction}"
    pd = post_date.strftime(DATE_FORMAT)
    ed = effective_date.strftime(DATE_FORMAT)
    code = full_transaction.code
    status = full_transaction.status.value
    desc = full_transaction.description
    assert ts.startswith(f"{pd}={ed} {status} ({code}) {desc}")
    entries = sorted(ts.split("\n")[1:])
    assert entries == sorted(f"    {e}" for e in full_transaction.entries)


def test_full_transaction_entries_sum_to_zero(full_transaction):
    assert sum(e.amount.amount for e in full_transaction.entries) == 0


@pytest.fixture
def transaction_with_implied_amount(asset, expense, liability, five_dollars, post_date):
    entry1 = Entry(account=asset)
    entry2 = Entry(account=expense, amount=five_dollars)
    entry3 = Entry(account=liability, amount=five_dollars)
    return Transaction(
        post_date=post_date,
        description="Test transaction",
        entries=frozenset({entry1, entry2, entry3}),
    )


def test_transaction_implied_amount_str(transaction_with_implied_amount, post_date):
    assert f"{transaction_with_implied_amount}".startswith(
        post_date.strftime(DATE_FORMAT)
    )


def test_transaction_implied_amount(transaction_with_implied_amount):
    implied = sum(
        e.amount.amount for e in transaction_with_implied_amount.entries if e.amount
    )
    assert implied == 10


def test_transaction_multi_line_description_error(post_date):
    with pytest.raises(ValueError):
        _t = Transaction(
            post_date=post_date,
            description="Test transaction line 1\nline 2",
        )


def test_full_transaction_sum_not_zero_error(post_date, five_dollars, ten_dollars):
    entry1 = Entry(account=asset, amount=ten_dollars)
    entry2 = Entry(account=expense, amount=five_dollars)
    entry3 = Entry(account=liability, amount=five_dollars)
    with pytest.raises(ValueError):
        t = Transaction(
            post_date=post_date,
            description="Test transaction",
            entries={entry1, entry2, entry3},
        )
        t.check_entries()


def test_too_many_implied_transaction_error(post_date, five_dollars):
    entry1 = Entry(account=asset)
    entry2 = Entry(account=expense)
    entry3 = Entry(account=liability, amount=five_dollars)
    with pytest.raises(ValueError):
        t = Transaction(
            post_date=post_date,
            description="Test transaction",
            entries={entry1, entry2, entry3},
        )
        t.check_entries()
