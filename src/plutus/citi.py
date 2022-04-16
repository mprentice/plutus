"""A module for processing Citi DoubleCash credit card statements.

Attempts to lookup a ledger expense Account to assign the transaction to.
Defaults to Account("Expenses:Unknown"), which can be overridden by setting the
environment variable PLUTUS_CITI_UNKNOWN_ACCOUNT. See
DoubleCashLedgerAccountConfig for other available overrides.

Usage:

    >>> statement = DoubleCashStatement.from_csv("statement.csv")
    >>> for transaction in statement.ledger_transactions():
    ...     print(f"{transaction}")

"""

import csv
import io
import pkgutil
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import (
    ClassVar,
    Dict,
    Generator,
    Optional,
    Sequence,
    Set,
    TextIO,
    Tuple,
    Union,
)

from attr import define, field, frozen
from decouple import config  # type: ignore

from .ledger import USD, Account, Entry, Transaction, TransactionStatus
from .utils import negate


@frozen
class AccountFactory:
    """Factory for creating default accounts.

    From named environment variables (via config) or defaults.

    Args:
        key (str): environment variable name
        default (str): default to use if environment variable not set
        prefix (str): key prefix, default is "PLUTUS_CITI_"
    """

    key: str
    default: str
    prefix: str = "PLUTUS_CITI_"

    def __call__(self) -> Account:
        """Create and return the Account or a default account."""
        return Account(config(f"{self.prefix}{self.key}", default=self.default))


@frozen
class DoubleCashLedgerAccountConfig:
    """Default ledger accounts to use for Citi DoubleCash transactions.

    attribute               | environment variable          | default
    ------------------------+-------------------------------+--------------------------
    asset_account           | PLUTUS_CITI_ASSET_ACCOUNT     | Assets:Checking
    liability_account       | PLUTUS_CITI_LIABILITY_ACCOUNT | Liabilities:CC:DoubleCash
    points_account          | PLUTUS_CITI_POINTS_ACCOUNT    | Expenses:Points
    unknown_expense_account | PLUTUS_CITI_UNKNOWN_ACCOUNT   | Expenses:Unknown
    """

    asset_account: Account = field(
        factory=AccountFactory("ASSET_ACCOUNT", "Assets:Checking"), converter=Account
    )
    liability_account: Account = field(
        factory=AccountFactory("LIABILITY_ACCOUNT", "Liabilities:CC:DoubleCash"),
        converter=Account,
    )
    points_account: Account = field(
        factory=AccountFactory("POINTS_ACCOUNT", "Expenses:Points"), converter=Account
    )
    unknown_expense_account: Account = field(
        factory=AccountFactory("UNKNOWN_ACCOUNT", "Expenses:Unknown"), converter=Account
    )


@frozen
class DoubleCashLedgerAccountLookup:
    """Database to lookup ledger Account to use.

    Lookup is based on Citi DoubleCash transaction description.
    """

    _db: ClassVar[Optional[Sequence[Tuple[re.Pattern, Account]]]] = None

    @property
    def db(self) -> Sequence[Tuple[re.Pattern, Account]]:
        """Lookup database.

        The database is an ordered sequence of tuples, where the first element
        is a regular expressions pattern to match and the second element is the
        ledger Account to return.
        """
        if self._db is None:
            csv_s = pkgutil.get_data(__package__, "data/citi_doublecash_accounts.csv")
            assert csv_s
            csv_io = io.StringIO(csv_s.decode("UTF-8"))
            self.load_csv(csv_io)
        assert self._db
        return self._db

    def lookup(self, description: str) -> Account:
        """Lookup transaction description and return the ledger Account.

        Raises:
            KeyError: if description can't be matched to an Account
        """
        for pattern, account in self.db:
            if pattern.match(description):
                return account
        raise KeyError(f'No matching account found for "{description}"')

    def __getitem__(self, key: str) -> Account:
        return self.lookup(key)

    @classmethod
    def _load_csv(cls, iostream: TextIO):
        reader = csv.DictReader(iostream)
        cls._db = tuple(
            (re.compile(d["pattern"], flags=re.IGNORECASE), Account(name=d["account"]))
            for d in reader
        )

    @classmethod
    def load_csv(cls, csvfile: Union[str, Path, TextIO], encoding: str = "UTF-8"):
        """Open and load a CSV containing the database of patterns and accounts.

        The file or TextIO must have a header row with the column headers
        "pattern" and "account." Example:

        pattern,account
        ^CAR WASH,Expenses:Auto
        ...

        Args:
            csvfile (str | Path | TextIO): path object to CSV file
            encoding (str): file encoding, default is UTF-8

        """
        if isinstance(csvfile, str):
            with open(csvfile, "r", encoding=encoding) as f:
                cls._load_csv(f)
        elif isinstance(csvfile, Path):
            with csvfile.open("r", encoding=encoding) as f:
                cls._load_csv(f)
        else:
            cls._load_csv(csvfile)


@frozen
class DoubleCashTransaction:
    """Represents a single transaction in a Citi DoubleCash statement.

    Args:
        status (str): Transaction status, usually "Cleared"
        post_date (date): Transaction post date
        description (str): Transaction description
        debit (Decimal | None): debit amount
        credit (Decimal | None): credit amount
    """

    status: str
    post_date: date
    description: str
    debit: Optional[Decimal] = None
    credit: Optional[Decimal] = None

    _config: DoubleCashLedgerAccountConfig = field(
        factory=DoubleCashLedgerAccountConfig
    )
    _db: DoubleCashLedgerAccountLookup = field(factory=DoubleCashLedgerAccountLookup)

    @classmethod
    def from_statement(cls, row: Dict[str, str]) -> "DoubleCashTransaction":
        """Read transaction from Citi DoubleCash statement row.

        Row is a dict with keys "Status," "Date," "Description," "Debit," and
        "Credit."

        Args:
            row (Dict[str, str]): statement row dict

        Returns: DoubleCashTransaction
        """
        status = row["Status"].strip()
        post_date = datetime.strptime(row["Date"], "%m/%d/%Y").date()
        description = row["Description"]
        debit = Decimal(row["Debit"]) if row["Debit"] else None
        credit = Decimal(row["Credit"]) if row["Credit"] else None
        return cls(
            status=status,
            post_date=post_date,
            description=description,
            debit=debit,
            credit=credit,
        )

    def ledger_transaction(self) -> Transaction:
        """Return a ledger transaction from Citi DoubleCash transaction.

        Returns:
            Transaction: a ledger Transaction, with entry accounts filled
                         in by matching the description.
        """
        is_cleared = self.status.lower() == "cleared"
        t = Transaction(
            post_date=self.post_date,
            description=self.description,
            status=TransactionStatus.CLEARED if is_cleared else None,
        )
        if self.debit:
            # Expense
            cc_entry = Entry(
                account=self._config.liability_account, amount=USD(negate(self.debit))
            )
            try:
                account = self._db[self.description]
            except KeyError:
                account = self._config.unknown_expense_account
            other_entry = Entry(account=account, amount=USD(self.debit))
        elif self.credit:
            # Payment
            cc_entry = Entry(
                account=self._config.liability_account,
                amount=USD(negate(self.credit)),
            )
            if "statement credit" in self.description.lower():
                account = self._config.points_account
            elif "payment thank you" in self.description.lower():
                account = self._config.asset_account
            else:
                try:
                    account = self._db[self.description]
                except KeyError:
                    account = self._config.unknown_expense_account
            other_entry = Entry(account=account, amount=USD(self.credit))
        t.add_entry(cc_entry)
        t.add_entry(other_entry)
        t.check_entries()
        return t


@define
class DoubleCashStatement:
    """A Citi DoubleCash statement is a set of transactions.

    Args:
        transactions (Set[DoubleCashTransaction]): set() by default
    """

    transactions: Set[DoubleCashTransaction] = field(factory=set)

    def add_transaction(self, transaction: DoubleCashTransaction):
        """Add transaction to the statement."""
        self.transactions.add(transaction)

    @classmethod
    def from_csv(
        cls, csvfile: Union[str, Path, TextIO], encoding: str = "UTF-8"
    ) -> "DoubleCashStatement":
        """Create a statement from a Citi DoubleCash statement csv file.

        Usage:
            >>> filename = "/path/to/statement.csv"
            >>> statement = DoubleCashStatement.from_csv(filename)
            >>> for t in statement.ledger_transactions():
            ...     print(f"{t}")

        Args:
            csvfile (str | Path | TextIO): CSV file handle or file name
            encoding (str): CSV file encoding, default is UTF-8

        Returns: DoubleCashStatement
        """
        if isinstance(csvfile, (Path, str)):
            with open(csvfile, "r", encoding=encoding) as f:
                return cls._read_doublecash_transactions(f)
        return cls._read_doublecash_transactions(csvfile)

    @classmethod
    def _read_doublecash_transactions(cls, iostream: TextIO):
        statement = cls()
        for d in csv.DictReader(iostream):
            statement.add_transaction(DoubleCashTransaction.from_statement(d))
        return statement

    def ledger_transactions(self) -> Generator[Transaction, None, None]:
        """Iterate over a Citi DoubleCash statement to get ledger transactions.

        Yields:
            Transaction: ledger transactions translated from Citi
                         DoubleCash transactions
        """
        for txn in sorted(self.transactions, key=lambda t: t.post_date):
            yield txn.ledger_transaction()
