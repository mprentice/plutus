from plutus.cli import main

def test_main():
    assert main("-v") is None
    assert main("-vv") is None
