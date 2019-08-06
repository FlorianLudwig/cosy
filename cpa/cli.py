"""Console script for cpa."""
from __future__ import annotations

import sys
import os
import subprocess
import typing

import click
import tomlkit


def find_project_root(path: str = ".") -> str:
    path = os.path.abspath(path)
    files_in_folder = os.listdir(path)
    if ".git" in files_in_folder or "pyproject.toml" in files_in_folder:
        return path

    parent = os.path.join(path, os.path.pardir)
    parent = os.path.abspath(parent)
    if parent == path:
        raise AttributeError("project root not found")

    return find_project_root(parent)


class Project:
    def __init__(self, path: str):
        self.path = path
        config_path = os.path.join(path, "pyproject.toml")
        self.config = tomlkit.document()
        if os.path.exists(config_path):
            with open(config_path) as config_fo:
                config_data = config_fo.read()
            self.config = tomlkit.loads(config_data)

    @classmethod
    def find(cls) -> Project:
        path = find_project_root()
        return cls(path)

    def metadata(self) -> dict:
        return self.config["tool"]["cpa"]


@click.group()
def main(args=None):
    """Console script for cpa."""

    return 0


class CommandResult(typing.NamedTuple):
    output: str
    returncode: int


def run(cmd) -> CommandResult:
    cmd = ["pipenv", "run"] + cmd
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return CommandResult(proc.stdout.read(), proc.wait())


@main.command()
def new():
    """create new project"""
    raise NotImplementedError()


@main.command()
def update():
    """update current project"""
    raise NotImplementedError()


@main.command()
def dist():
    """create distributables"""
    raise NotImplementedError()


@main.command()
def publish():
    """publish to pypi"""
    raise NotImplementedError()


@main.command()
def test() -> None:
    """run tests"""
    project = Project.find()
    conf = project.metadata()
    module = conf["name"]

    cmd = ["black", "--check", "."]
    style_res = run(cmd)

    cmd = ["pylint", module]
    pylint_res = run(cmd)

    cmd = [
        "mypy",
        "--no-incremental",
        "--ignore-missing-imports",
        "--warn-unreachable",
        "--check-untyped-defs",
        module,
    ]
    mypy_res = run(cmd)

    ret_code = 0
    if style_res.returncode != 0:
        click.echo(f"== style check failed with code {style_res.returncode} ==")
        click.echo(style_res.output)
        ret_code = ret_code | 1

    if pylint_res.returncode != 0:
        click.echo(f"== pylint failed with code {pylint_res.returncode} ==")
        click.echo(pylint_res.output)
        ret_code = ret_code | 2

    if mypy_res.returncode != 0:
        click.echo(f"== mypy failed with code {mypy_res.returncode} ==")
        click.echo(mypy_res.output)
        ret_code = ret_code | 4

    sys.exit(ret_code)


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
