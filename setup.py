"""Install with: `python setup.py install' or `pip install'."""
import io
import os
from glob import glob

from setuptools import find_packages, setup  # type: ignore

__version__ = "0.2.0"


def read(*names, **kwargs) -> str:
    """Open and return text of file relative to this file's directory."""
    filename = os.path.join(os.path.dirname(__file__), *names)
    encoding = kwargs.get("encoding", "utf8")
    with io.open(filename, encoding=encoding) as filehandle:
        return filehandle.read()


INSTALL_REQUIRES = [
    "attrs",
    "click",
    "pdfminer.six",
    "money",
    "babel>=2.2",
    "iso4217",
    "python-decouple",
]
TEST_REQUIRES = INSTALL_REQUIRES + [
    "prospector",
    "mypy",
    "flake8",
    "flake8-black",
    "flake8-bugbear",
    "flake8-isort",
    "flake8-comprehensions",
    "flake8-docstrings",
    "pytest",
    "pytest-cov",
    "setuptools",
]
DEV_REQUIRES = TEST_REQUIRES + ["wheel", "importmagic", "epc", "jedi", "isort"]

setup(
    name="plutus",
    version=__version__,
    license="MIT License",
    description=(
        "Swiss army knife toolkit to import financial statements to ledger-cli."
    ),
    long_description=read("README.rst"),
    author="Mike Prentice",
    email="mjp35@cornell.edu",
    packages=find_packages("src"),
    package_dir={"": "src", "plutus": "src/plutus"},
    py_modules=[
        os.path.splitext(os.path.basename(path))[0] for path in glob("src/*.py")
    ],
    include_package_data=True,
    package_data={"plutus": ["data/*.csv"]},
    classifiers=[
        # complete classifier list:
        # http://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Topic :: Office/Business :: Financial :: Accounting",
    ],
    python_requires=">=3.7",
    install_requires=INSTALL_REQUIRES,
    extras_require={"dev": DEV_REQUIRES, "test": TEST_REQUIRES},
    entry_points={
        "console_scripts": [
            "plutus = plutus.cli:cli",
        ]
    },
)
