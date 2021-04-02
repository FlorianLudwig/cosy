"""Console script for create python app."""
from __future__ import annotations

from typing import Set
import sys
import os
import shutil

import click

import cpa.install
import cpa.project


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

    return ret_code


@click.group()
def main(args=None):
    """Console script for cpa."""

    return 0


def project_deps(project: cpa.project.Base, run_only: bool = False) -> Set[str]:
    """Returns a set of all system dependencies required by python packages"""
    system = cpa.install.System.get_current()
    python_dependencies = project.get_packages_list()
    sys_deps = set()
    for package in python_dependencies:
        deps_to_install = system.python_pkg_deps(package, run_only)
        sys_deps.update(deps_to_install)

    return sys_deps


@main.command()
def new():
    """create new project"""
    raise NotImplementedError()


@main.command()
@click.option("--with-sysdeps", "with_sysdeps", is_flag=True)
def install(with_sysdeps):
    """install python dependencies via pipenv/poetry, and insall system dependencies"""
    project = cpa.project.find()
    if with_sysdeps:
        click.echo("Installing system dependencies..")
        system = cpa.install.System.get_current()
        sys_deps = project_deps(project)
        system.install(sys_deps)
        click.echo("Clean up not needed dependencies..")
        system.cleanup()
        click.echo("Complete")
    click.echo(project.install().output)


@main.command()
@click.option("--run-only", "-r", "run_only", is_flag=True)
def sysdeps(run_only):
    """List all system dependencies required by project's python packages"""
    project = cpa.project.find()
    sys_deps = project_deps(project, run_only)
    click.echo(f"These system dependencies need to be installed {sys_deps}")


@main.command()
def update():
    """update current project"""
    raise NotImplementedError()


@main.command()
def dist():
    """create distributables"""
    project = cpa.project.find()

    # TODO ensure project is CLEAN
    _dist(project)


def _dist(project):
    test_result_code = run_tests(project)
    if test_result_code != 0:
        click.secho("Not creating dist due to failing tests", fg="red")
        sys.exit(test_result_code)

    os.chdir(project.path)
    if os.path.exists("dist"):
        shutil.rmtree("dist")

    click.echo(project.run(["python", "setup.py", "sdist"]).output)
    click.echo(project.run(["python", "setup.py", "bdist_wheel"]).output)


@main.command()
def publish():
    """publish to pypi"""
    project = cpa.project.find()

    if not project.metadata().public:
        click.secho("Project not public.  Not uploading to pypi", fg="red")
        sys.exit(1)

    click.secho("Creating distribution")
    _dist(project)
    click.secho("Uploading")
    cmd = ["twine", "upload"] + ["dist/" + name for name in os.listdir("dist")]
    project.run(cmd, capture=False)


@main.command()
def test() -> None:
    """run tests"""
    project = cpa.project.find()
    ret_code = run_tests(project)
    sys.exit(ret_code)


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
