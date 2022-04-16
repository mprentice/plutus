import io
from datetime import date
from decimal import Decimal
from functools import partial
from typing import Callable

import pytest

from plutus.citi import (
    DoubleCashLedgerAccountConfig,
    DoubleCashLedgerAccountLookup,
    DoubleCashStatement,
    DoubleCashTransaction,
)
from plutus.ledger import USD, Account, AccountCategory, TransactionStatus
from plutus.utils import negate


@pytest.fixture
def doublecash_ledger_account_config() -> DoubleCashLedgerAccountConfig:
    return DoubleCashLedgerAccountConfig(
        asset_account="Assets:Checking",
        liability_account="Liabilities:CC:DoubleCash",
        points_account="Expenses:Points",
        unknown_expense_account="Expenses:Unknown",
    )


@pytest.fixture
def doublecash_ledger_account_lookup() -> DoubleCashLedgerAccountLookup:
    return DoubleCashLedgerAccountLookup()


def test_doublecash_ledger_account_config(
    doublecash_ledger_account_config: DoubleCashLedgerAccountConfig,
):
    c = doublecash_ledger_account_config
    assert c.asset_account.category == AccountCategory.ASSETS
    assert c.liability_account.category == AccountCategory.LIABILITIES
    assert c.points_account.category == AccountCategory.EXPENSES
    assert c.unknown_expense_account.category == AccountCategory.EXPENSES


def test_doublecash_ledger_account_lookup(
    doublecash_ledger_account_lookup: DoubleCashLedgerAccountLookup,
):
    lookup = doublecash_ledger_account_lookup
    assert lookup["BBQ RESTAURANT"] == Account("Expenses:Dining")


def test_doublecash_ledger_account_lookup_not_exists(
    doublecash_ledger_account_lookup: DoubleCashLedgerAccountLookup,
):
    lookup = doublecash_ledger_account_lookup
    with pytest.raises(KeyError):
        _ = lookup["=$%@#"]
        assert lookup["BBQ RESTAURANT"] == Account("Expenses:Dining")


def test_doublecash_transaction_from_statement():
    t = DoubleCashTransaction.from_statement(
        row={
            "Status": "Cleared",
            "Date": "05/01/2022",
            "Description": "Test transaction",
            "Debit": "15.00",
            "Credit": "",
        }
    )
    assert t.post_date == date(2022, 5, 1)
    assert t.debit == Decimal("15.00")
    assert t.credit is None


@pytest.fixture
def doublecash_txn(
    doublecash_ledger_account_config: DoubleCashLedgerAccountConfig,
    doublecash_ledger_account_lookup: DoubleCashLedgerAccountLookup,
) -> Callable:
    return partial(
        DoubleCashTransaction,
        status="Cleared",
        post_date=date(2022, 5, 1),
        config=doublecash_ledger_account_config,
        db=doublecash_ledger_account_lookup,
    )


def test_doublecash_ledger_transaction_debit_known(
    doublecash_txn: Callable,
    doublecash_ledger_account_config: DoubleCashLedgerAccountConfig,
):
    cfg = doublecash_ledger_account_config
    amt = Decimal("15.00")
    dctxn = doublecash_txn(
        description="BBQ RESTAURANT",
        debit=amt,
        credit=None,
    )
    ledger_txn = dctxn.ledger_transaction()
    assert ledger_txn.status == TransactionStatus.CLEARED
    assert any(
        e.account == Account("Expenses:Dining") and e.amount == USD(amt)
        for e in ledger_txn.entries
    )
    assert any(
        e.account == cfg.liability_account and e.amount == USD(negate(amt))
        for e in ledger_txn.entries
    )


def test_doublecash_ledger_transaction_debit_unknown(
    doublecash_txn: Callable,
    doublecash_ledger_account_config: DoubleCashLedgerAccountConfig,
):
    cfg = doublecash_ledger_account_config
    amt = Decimal("15.00")
    dctxn = doublecash_txn(
        description="=$%@#",
        debit=amt,
        credit=None,
    )
    ledger_txn = dctxn.ledger_transaction()
    assert ledger_txn.status == TransactionStatus.CLEARED
    assert any(
        e.account == cfg.unknown_expense_account and e.amount == USD(amt)
        for e in ledger_txn.entries
    )
    assert any(
        e.account == cfg.liability_account and e.amount == USD(negate(amt))
        for e in ledger_txn.entries
    )


def test_doublecash_ledger_transaction_credit_payment(
    doublecash_txn: Callable,
    doublecash_ledger_account_config: DoubleCashLedgerAccountConfig,
):
    cfg = doublecash_ledger_account_config
    amt = Decimal("15.00")
    dctxn = doublecash_txn(
        description="PAYMENT THANK YOU",
        debit=None,
        credit=negate(amt),
    )
    ledger_txn = dctxn.ledger_transaction()
    assert any(
        e.account == cfg.liability_account and e.amount == USD(amt)
        for e in ledger_txn.entries
    )
    assert any(
        e.account == cfg.asset_account and e.amount == USD(negate(amt))
        for e in ledger_txn.entries
    )


def test_doublecash_ledger_transaction_credit_points(
    doublecash_txn: Callable,
    doublecash_ledger_account_config: DoubleCashLedgerAccountConfig,
):
    cfg = doublecash_ledger_account_config
    amt = Decimal("15.00")
    dctxn = doublecash_txn(
        description="STATEMENT CREDIT",
        debit=None,
        credit=negate(amt),
    )
    ledger_txn = dctxn.ledger_transaction()
    assert any(
        e.account == cfg.liability_account and e.amount == USD(amt)
        for e in ledger_txn.entries
    )
    assert any(
        e.account == cfg.points_account and e.amount == USD(negate(amt))
        for e in ledger_txn.entries
    )


def test_doublecash_ledger_transaction_credit_expense(
    doublecash_txn: Callable,
    doublecash_ledger_account_config: DoubleCashLedgerAccountConfig,
):
    cfg = doublecash_ledger_account_config
    amt = Decimal("15.00")
    dctxn = doublecash_txn(
        description="=$%@#",
        debit=None,
        credit=negate(amt),
    )
    ledger_txn = dctxn.ledger_transaction()
    assert any(
        e.account == cfg.liability_account and e.amount == USD(amt)
        for e in ledger_txn.entries
    )
    assert any(
        e.account == cfg.unknown_expense_account and e.amount == USD(negate(amt))
        for e in ledger_txn.entries
    )


def test_doublecash_statement_from_csv(doublecash_statement_csv: io.StringIO):
    statement = DoubleCashStatement.from_csv(doublecash_statement_csv)
    assert len(statement.transactions) >= 5


def test_doublecash_statement_ledger_transactions(
    doublecash_statement_csv: io.StringIO,
):
    statement = DoubleCashStatement.from_csv(doublecash_statement_csv)
    for txn in statement.ledger_transactions():
        txn.check_entries()
