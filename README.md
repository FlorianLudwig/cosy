![MIT licensed](https://img.shields.io/github/license/FlorianLudwig/cosy?style=flat-square)
![Python Version](https://img.shields.io/pypi/pyversions/cosy?style=flat-square)
![supports python wheel](https://img.shields.io/pypi/wheel/cosy?style=flat-square )
[![PyPI](https://img.shields.io/pypi/v/cosy?style=flat-square)](https://pypi.org/project/cosy/)


# Cosy - Code With Style Project Management CLI

 * refered as CPA

## Goal

Full life cycle management for python apps and libs.  Create python boilerplate, develop, update boilerplate and publish.

 * Single point of truth for project parameters


## State

The repository contains a **WIP MVP** to evaliuate different technologies, workflows and user interface.  It's quick and dirty.

**Not suited for production work.**  Major version zero (0.y.z) is for initial development. Anything may change at any time. The public API should not be considered stable.


## Opinionated

The software is based on decisions regarding project structure and
used libraries.

Current decisions (effecting projects managed with cpa, not just cpa's developemt itself):

 * `py.test` to run tests
 * git for version control
 * type annotations are good
 * gitlab ci integration
 * `mypy` (`pytype` to be evaluated)

Limited configurablility in other places:

 * `pipenv` and [poetry](https://poetry.eustace.io/)

Some of them might end up being configurable, some might never be configurable.
Keeping CPA simple might take priority.

## Usage

```
Commands:
  create   create new project
  dist     create distributables
  publish  publish to pypi
  test     run tests
  update   update current project
```


## TODO

 * Explain why
