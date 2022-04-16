"""Plutus, the god of wealth.

Swiss army knife toolkit to import financial statements to ledger-cli.
"""

import click
from pdfminer.high_level import extract_text

from .citi import DoubleCashStatement


@click.group()
def cli():
    """Swiss army knife toolkit to import financial statements to ledger-cli."""


@cli.command(name="import")
@click.argument("source", type=click.Choice(["schwab", "citi-doublecash"]))
@click.argument("infile", type=click.Path(exists=True), metavar="<file>")
def import_(source: str, infile: str):
    """Import source file for output to ledger."""
    if source.lower() == "schwab":
        if infile.lower().endswith(".pdf"):
            text = extract_text(infile)
            print(text)
    elif source.lower() == "citi-doublecash":
        if infile.lower().endswith(".csv"):
            statement = DoubleCashStatement.from_csv(infile)
            for transaction in statement.ledger_transactions():
                print(f"{transaction}")
                print()
