import pkg_resources  # type: ignore

import plutus


def test_version():
    """Ensure setuptools and package versions are in sync."""
    assert plutus.__version__ == pkg_resources.require(plutus.__package__)[0].version
