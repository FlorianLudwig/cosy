import pathlib

import cosy.project

BASE = pathlib.Path(__file__).parent
POETRY_TESTPROJECT_PATH = BASE / "testproject_poetry"
PIPENV_TESTPROJECT_PATH = BASE / "testproject_pipenv"

POETRY_TESTPROJECT_DATA = cosy.project.ProjectData(POETRY_TESTPROJECT_PATH)
PIPENV_TESTPROJECT_DATA = cosy.project.ProjectData(PIPENV_TESTPROJECT_PATH)


def test_poetry_detection():
    assert cosy.project.Poetry.supported(POETRY_TESTPROJECT_DATA)
    assert not cosy.project.Poetry.supported(PIPENV_TESTPROJECT_DATA)


def test_pipenv_detection():
    assert cosy.project.Pipenv.supported(PIPENV_TESTPROJECT_DATA)
    assert not cosy.project.Pipenv.supported(POETRY_TESTPROJECT_DATA)
