from decimal import Decimal

from plutus.utils import negate


def test_negate_zero():
    assert negate(Decimal(0)) == Decimal(0)


def test_negate():
    assert negate(Decimal("1.99")) == Decimal("-1.99")
