"""Miscellaneous utility methods for plutus."""

from decimal import Decimal


def negate(d: Decimal) -> Decimal:
    """Return the Decimal negation of its input."""
    return d * Decimal("-1.0")
