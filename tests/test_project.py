import pathlib

import cpa.project

BASE = pathlib.Path(__file__).parent
POETRY_TESTPROJECT_PATH = BASE / "testproject_poetry"
PIPENV_TESTPROJECT_PATH = BASE / "testproject_pipenv"

POETRY_TESTPROJECT_DATA = cpa.project.ProjectData(POETRY_TESTPROJECT_PATH)
PIPENV_TESTPROJECT_DATA = cpa.project.ProjectData(PIPENV_TESTPROJECT_PATH)


def test_poetry_detection():
    assert cpa.project.Poetry.supported(POETRY_TESTPROJECT_DATA)
    assert not cpa.project.Poetry.supported(PIPENV_TESTPROJECT_DATA)


def test_pipenv_detection():
    assert cpa.project.Pipenv.supported(PIPENV_TESTPROJECT_DATA)
    assert not cpa.project.Pipenv.supported(POETRY_TESTPROJECT_DATA)
