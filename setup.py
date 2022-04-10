#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function

import io
import os
from glob import glob

from setuptools import find_packages, setup  # type: ignore


def read(*names, **kwargs):
    filename = os.path.join(os.path.dirname(__file__), *names)
    encoding = kwargs.get("encoding", "utf8")
    with io.open(filename, encoding=encoding) as fh:
        return fh.read()


INSTALL_REQUIRES = []  # type: ignore
TEST_REQUIRES = INSTALL_REQUIRES + [
    "prospector",
    "mypy",
    "flake8",
    "flake8-mypy",
    "flake8-black",
    "flake8-bugbear",
    "flake8-isort",
    "pytest",
    "pytest-cov",
]
DEV_REQUIRES = TEST_REQUIRES + ["wheel", "importmagic", "epc", "jedi", "isort"]

setup(
    name="plutus",
    version="0.1.0",
    license="MIT License",
    description="Swiss army knife toolkit to import financial statements to ledger-cli.",
    long_description=read("README.rst"),
    author="Mike Prentice",
    email="mjp35@cornell.edu",
    packages=find_packages("src"),
    package_dir={"": "src"},
    py_modules=[
        os.path.splitext(os.path.basename(path))[0] for path in glob("src/*.py")
    ],
    include_package_data=True,
    classifiers=[
        # complete classifier list:
        # http://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
    ],
    python_requires=">=3.7",
    install_requires=INSTALL_REQUIRES,
    extras_require={"dev": DEV_REQUIRES, "test": TEST_REQUIRES},
    entry_points={
        "console_scripts": [
            "plutus = plutus.cli:main",
        ]
    },
)
