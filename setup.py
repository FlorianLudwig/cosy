#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open("README.md") as readme_file:
    readme = readme_file.read()

requirements = ["Click>=6.0"]

setup_requirements = ["pytest-runner"]

test_requirements = ["pytest"]

setup(
    author="Florian Ludwig",
    author_email="f.ludwig@greyrook.com",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    description="full life cycle management for python apps and libs",
    entry_points={"console_scripts": ["create-python-app=cpa.cli:main"]},
    install_requires=requirements,
    license="Apache Software License 2.0",
    long_description=readme,
    include_package_data=True,
    keywords="cpa",
    name="cpa",
    packages=find_packages(include=["cpa"]),
    setup_requires=setup_requirements,
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/FlorianLudwig/cpa",
    version="0.1.0",
    zip_safe=False,
)
