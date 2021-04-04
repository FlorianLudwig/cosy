from typing import Set

import typer

import cosy.project
import cosy.install


app = typer.Typer()


@app.command()
def list(run_only: bool = False):
    """List all system dependencies required by project's python packages"""
    project = cosy.project.find()
    for dep in project_deps(project, run_only):
        typer.echo(dep)


def project_deps(project: cosy.project.Base, run_only: bool = False) -> Set[str]:
    """Returns a set of all system dependencies required by python packages"""
    system = cosy.install.System.get_current()
    python_dependencies = project.get_packages_list()
    sys_deps = set()
    for package in python_dependencies:
        deps_to_install = system.python_pkg_deps(package, run_only)
        sys_deps.update(deps_to_install)

    return sys_deps
