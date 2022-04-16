import io

import pytest


@pytest.fixture
def doublecash_statement_csv() -> io.StringIO:
    return io.StringIO(
        "\n".join(
            [
                "Status,Date,Description,Debit,Credit",
                'Cleared,03/21/2022,"NETFLIX.COM",17.99,',
                'Cleared,03/19/2022,"SHAWS",30.77,',
                'Cleared,03/16/2022,"PAYMENT THANK YOU",,-2000.05',
                'Cleared,03/07/2022,"LOWES",41.98,',
                'Cleared,02/28/2022,"TARGET",,-7.99',
                'Cleared,02/27/2022,"Cash rewards statement credit",,-50.00',
            ]
        )
    )
