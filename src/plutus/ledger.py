"""Utilities and classes for working with ledger-cli."""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Dict, Optional, Set, Union

from attr import define, field, frozen
from babel.numbers import format_decimal  # type: ignore
from iso4217 import Currency  # type: ignore
from money import Money  # type: ignore

DATE_FORMAT = "%Y/%m/%d"


class USD(Money):
    """Represents amounts in USD ($)."""

    def __init__(self, amount: Decimal, currency=Currency.usd.code):  # type: ignore
        super().__init__(amount=amount, currency=currency)

    def __str__(self) -> str:
        return self.format("en_US")


class TransactionStatus(Enum):
    """Transaction status enum, cleared (*) or pending (!)."""

    CLEARED = "*"
    PENDING = "!"


class AccountCategory(Enum):
    """Account category enum.

    Account categories are assets, equity, expenses, income, and liabilities.
    """

    ASSETS = "Assets"
    EQUITY = "Equity"
    EXPENSES = "Expenses"
    INCOME = "Income"
    LIABILITIES = "Liabilities"


@frozen
class Account:
    """A ledger account.

    Ledger accounts are in a :-separated hierarchy, e.g.
    Assets:MyBank:Checking.

    Usage:

        >>> acct = Account("Assets:MyBank:Checking")
        >>> print(f"{acct}")
        Assets:MyBank:Checking
        >>> print(f"{acct.category.value}")
        Assets
    """

    name: str

    def __init__(self, name: Union[str, "Account"]):
        if isinstance(name, Account):
            self.__attrs_init__(name.name)  # type: ignore
        else:
            self.__attrs_init__(name)  # type: ignore

    @property
    def category(self) -> AccountCategory:
        """Category of this account."""
        return AccountCategory(self.name.split(":")[0])

    def __str__(self) -> str:
        return self.name


@frozen
class CommodityAmount:
    """Commodity and amount.

    Args:
        amount (Decimal): Quantity of commodity
        commodity (str): Identifier of commodity, equity, stock, etc (e.g. AAPL)
    """

    amount: Decimal
    commodity: str

    def __str__(self) -> str:
        return f"{format_decimal(self.amount, locale='en_US')} {self.commodity}"

    def __add__(self, other: "CommodityAmount") -> "CommodityAmount":
        if not isinstance(other, CommodityAmount):
            raise TypeError(f"Cannot add CommodityAmount with {type(other)}")
        if self.commodity != other.commodity:
            raise ValueError(
                f"Cannot add commodities {self.commodity} and {other.commodity}"
            )
        return self.__class__(
            amount=self.amount + other.amount, commodity=self.commodity
        )

    def __mul__(self, other: Union[int, float, Decimal]) -> "CommodityAmount":
        return self.__class__(
            amount=self.amount * Decimal(other), commodity=self.commodity
        )

    def __rmul__(self, other: Union[int, float, Decimal]) -> "CommodityAmount":
        return self.__class__(
            amount=self.amount * Decimal(other), commodity=self.commodity
        )


@frozen
class Entry:
    """A single transaction entry.

    Args:
        account (Account): The entry's account
        status (Optional[TransactionStatus]): Cleared, pending, or none
        amount (Optional[Union[Money, CommodityAmount]]): Entry amount
        lot_price (Optional[Money]): Lot price
        lot_date (Optional[date]): Lot date
        purchase_price (Optional[Money]): Purchase price
    """

    account: Account = field(converter=Account)
    status: Optional[TransactionStatus] = None
    amount: Optional[Union[Money, CommodityAmount]] = None
    lot_price: Optional[Money] = None
    lot_date: Optional[date] = None
    purchase_price: Optional[Money] = None

    def __str__(self) -> str:
        pieces = []
        if self.status:
            pieces.append(self.status.value)
        pieces.append(str(self.account))
        if self.amount:
            pieces.append(" ")
            pieces.append(str(self.amount))
            if self.lot_price:
                pieces.append("{" + str(self.lot_price) + "}")
            if self.lot_date:
                pieces.append("[" + self.lot_date.strftime(DATE_FORMAT) + "]")
            if self.purchase_price:
                pieces.append(f"@ {self.purchase_price}")
        return " ".join(pieces)


@define
class Transaction:
    """A ledger transaction.

    A transaction is immutable (frozen). Validation logic ensures that entries
    sum to zero (or have one entry with an implied amount), and that the
    description is one line.

    Args:
        post_date (date): Posted date of transaction
        description (str): Short one-line description of transaction
        entries (FrozenSet[Entry]): Transaction entries
        effective_date (Optional[date]): Effective date of transaction
        status (Optional[TransactionStatus]): Cleared, pending, or none
        code (Optional[str]): Transaction code, e.g. check #
    """

    post_date: date
    description: str = field()
    entries: Set[Entry] = field(factory=set)
    effective_date: Optional[date] = None
    status: Optional[TransactionStatus] = None
    code: Optional[str] = None

    @description.validator
    def check_description(self, _attribute, value):
        """Ensure that description is only one line."""
        lines = len(value.split("\n"))
        if lines > 1:
            raise ValueError("Description must be one line (found {lines} lines)")

    def check_entries(self):
        """Ensure that entries sum to 0, or that there is exactly one implied amount.

        Raises:
            ValueError: If entries don't sum to zero, or there is more than
                        one implied amount.
        """
        missing_count = sum(1 for e in self.entries if e.amount is None)
        if missing_count == 0 and any(v.amount != 0 for v in self.net):
            raise ValueError(f"Entries must sum to 0 (sum: {self.net})")
        if missing_count > 1:
            raise ValueError(
                f"Only one entry can have an implied amount ({missing_count} found)"
            )

    @property
    def net(self) -> Set[Union[Money, CommodityAmount]]:
        """Net of transaction entries.

        Returns:
            Net totals as Set[Union[Money, CommodityAmount]].
        """
        net_amounts: Dict[type, Union[Money, CommodityAmount]] = {}
        for e in self.entries:
            if e.amount:
                if isinstance(e.amount, Money):
                    key = e.amount.currency
                else:
                    key = e.amount.commodity
                try:
                    net_amounts[key] += e.amount
                except KeyError:
                    net_amounts[key] = e.amount
        return set(net_amounts.values())

    def add_entry(self, entry: Entry):
        """Add entry to transaction."""
        self.entries.add(entry)

    def __str__(self) -> str:
        pieces = []
        if self.effective_date:
            post_date = self.post_date.strftime(DATE_FORMAT)
            effective_date = self.effective_date.strftime(DATE_FORMAT)
            pieces.append(f"{post_date}={effective_date}")
        else:
            pieces.append(self.post_date.strftime(DATE_FORMAT))
        if self.status:
            pieces.append(self.status.value)
        if self.code:
            pieces.append(f"({self.code})")
        pieces.append(self.description)
        return "\n    ".join([" ".join(pieces)] + [str(e) for e in self.entries])
