"""Console script for create python app."""
from __future__ import annotations
import subprocess

from typing import Set
import sys
import os
import shutil
from distro import name
import typer

import cpa.install
import cpa.project
import cpa.cli_sysdeps


def run_tests(project: cpa.project.Base) -> int:
    conf = project.metadata()
    module = conf.name

    # allow syntax new in python 3.6
    cmd = ["black", "--check", "--target-version", "py36", "."]
    style_res = project.run(cmd)

    cmd = ["pylint", f"--rcfile={project.data.pylintrc_path}", module]
    pylint_res = project.run(cmd)

    cmd = [
        "mypy",
        "--no-incremental",
        "--ignore-missing-imports",
        "--warn-unreachable",
        "--check-untyped-defs",
        module,
    ]
    mypy_res = project.run(cmd)

    ret_code = 0
    if style_res.returncode != 0:
        typer.echo(f"== style check failed with code {style_res.returncode} ==")
        typer.echo(style_res.output)
        ret_code = ret_code | 1

    if pylint_res.returncode != 0:
        typer.echo(f"== pylint failed with code {pylint_res.returncode} ==")
        typer.echo(pylint_res.output)
        ret_code = ret_code | 2

    if mypy_res.returncode != 0:
        typer.echo(f"== mypy failed with code {mypy_res.returncode} ==")
        typer.echo(mypy_res.output)
        ret_code = ret_code | 4

    return ret_code


app = typer.Typer()
app.add_typer(cpa.cli_sysdeps.app, name="sysdeps")


@app.command()
def install(
    with_sysdeps: bool = typer.Option(
        False,
        "--with-sysdeps",
        help="automatically install needed system dependencies (with dnf/apt)",
    )
):
    """install python dependencies via pipenv/poetry, and insall system dependencies"""
    project = cpa.project.find()
    if with_sysdeps:
        typer.echo("Installing system dependencies..")
        system = cpa.install.System.get_current()
        sys_deps = cpa.cli_sysdeps.project_deps(project)
        system.install(sys_deps)
        typer.echo("Clean up not needed dependencies..")
        system.cleanup()
        typer.echo("Complete")
    typer.echo(project.install().output)


@app.command()
def dist():
    """create distributables"""
    project = cpa.project.find()

    # TODO ensure project is CLEAN
    _dist(project)


def _dist(project):
    test_result_code = run_tests(project)
    if test_result_code != 0:
        typer.secho("Not creating dist due to failing tests", fg="red")
        sys.exit(test_result_code)

    os.chdir(project.path)
    if os.path.exists("dist"):
        shutil.rmtree("dist")

    typer.echo(project.run(["python", "setup.py", "sdist"]).output)
    typer.echo(project.run(["python", "setup.py", "bdist_wheel"]).output)


@app.command()
def publish():
    """publish to pypi"""
    project = cpa.project.find()

    if not project.metadata().public:
        typer.secho("Project not public.  Not uploading to pypi", fg="red")
        sys.exit(1)

    typer.secho("Creating distribution")
    _dist(project)
    typer.secho("Uploading")
    cmd = ["twine", "upload"] + ["dist/" + name for name in os.listdir("dist")]
    project.run(cmd, capture=False)


@app.command()
def test() -> None:
    """run tests"""
    project = cpa.project.find()
    ret_code = run_tests(project)
    sys.exit(ret_code)


def main():
    app()


if __name__ == "__main__":
    app()  # pragma: no cover
