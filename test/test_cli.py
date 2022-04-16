import pytest
from click.testing import CliRunner

from plutus.cli import import_


def test_import_doublecash(tmp_path, doublecash_statement_csv):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        with open("doublecash_statement.csv", "w") as f:
            f.write(doublecash_statement_csv.read())
        result = runner.invoke(import_, ["citi-doublecash", "doublecash_statement.csv"])
        assert result.exit_code == 0
        assert len(result.output.split("\n")) > 20
