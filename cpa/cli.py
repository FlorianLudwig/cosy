"""Console script for create python app."""
from __future__ import annotations

from typing import Set, Optional
import sys
import os
import subprocess
import typing
import shutil
import dataclasses
import configparser

import pkg_resources
import click
import tomlkit

import cpa.install


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


@dataclasses.dataclass
class Config:
    name: str
    public: bool


class Project:
    pyproject: Optional[tomlkit.document]

    def __init__(self, path: str):
        self.path = path
        pyproject_path = os.path.join(path, "pyproject.toml")

        if os.path.exists(pyproject_path):
            tomlkit.document()
            with open(pyproject_path) as config_fo:
                config_data = config_fo.read()
            self.pyproject = tomlkit.loads(config_data)

    @classmethod
    def get_project_instance(cls, path):
        files_in_folder = os.listdir(path)
        if "Pipfile.lock" in files_in_folder:
            return PipenvProject
        elif "poetry.lock" in files_in_folder:
            return PoetryProject
        else:
            raise ValueError("unable to detect python project type")

    @classmethod
    def find(cls) -> Project:
        path = find_project_root()
        project = cls.get_project_instance(path)
        return project(path)

    def metadata(self) -> Config:
        name = None
        public = False

        if self.pyproject:
            tool = self.pyproject.get("tool", {})
            name = tool.get("poetry", {}).get("name", None)
            name = tool.get("cpa", {}).get("name", name)
            public = tool.get("cpa", {}).get("public", public)

        if name is None:
            raise AttributeError("Could not determine package name")

        metadata = Config(name, public)
        return metadata

    @property
    def pylintrc(self):
        project_sepecific_pylintrc = os.path.join(self.path, ".pylintrc")
        if os.path.exists(project_sepecific_pylintrc):
            return project_sepecific_pylintrc

        return pkg_resources.resource_filename("cpa", "pylintrc")

    def run(self, cmd, capture=True) -> CommandResult:
        """Run commands in a subprocess"""
        raise NotImplementedError()

    def install(self) -> CommandResult:
        """Install python packages"""
        raise NotImplementedError()

    def get_packages_list(self) -> Set[str]:
        """Returns a list of python packages used by pipenv/poetry"""
        raise NotImplementedError()


class PipenvProject(Project):
    def run(self, cmd, capture=True) -> CommandResult:
        """Run commands in a subprocess"""
        cmd = ["pipenv", "run"] + cmd
        return run(cmd, capture)

    def install(self) -> CommandResult:
        """Install python packages"""
        cmd = ["pipenv", "install", "--ignore-pipfile"]
        return run(cmd)

    def get_packages_list(self) -> Set[str]:
        """Returns a list of python packages used by pipenv"""
        packages_list = []
        parser = configparser.ConfigParser()
        parser.read(os.path.join(self.path, "Pipfile"))

        for pkg in parser["packages"]:
            packages_list.append(pkg)
        for pkg in parser["dev-packages"]:
            packages_list.append(pkg)

        return set(packages_list)


class PoetryProject(Project):
    def run(self, cmd, capture=True) -> CommandResult:
        """Run commands in a subprocess"""
        cmd = ["poetry", "run"] + cmd
        return run(cmd, capture)

    def install(self) -> CommandResult:
        """Install python packages"""
        cmd = ["poetry", "install"]
        return run(cmd)

    def get_packages_list(self) -> Set[str]:
        """Returns a list of python packages used by poetry"""
        packages_list = []
        assert self.pyproject
        tool = self.pyproject.get("tool", {})
        deps = tool.get("poetry", {}).get("dependencies", {})
        dev_deps = tool.get("poetry", {}).get("dev-dependencies", {})
        packages_list = list(deps.keys()) + list(dev_deps.keys())
        return set(packages_list)


def run_tests(project: Project) -> int:
    conf = project.metadata()
    module = conf.name

    # allow syntax new in python 3.6
    cmd = ["black", "--check", "--target-version", "py36", "."]
    style_res = project.run(cmd)

    cmd = ["pylint", f"--rcfile={project.pylintrc}", module]
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


class CommandResult(typing.NamedTuple):
    output: str
    returncode: int


def run(cmd, capture=True) -> CommandResult:
    if capture:
        proc = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        assert proc.stdout is not None  # makes mypy happy
        return CommandResult(proc.stdout.read().decode("utf-8"), proc.wait())
    else:
        proc = subprocess.Popen(cmd)
        return CommandResult("", proc.wait())


def project_deps(project: Project, run_only: bool = False) -> Set[str]:
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
    project = Project.find()
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
    project = Project.find()
    sys_deps = project_deps(project, run_only)
    click.echo(f"These system dependencies need to be installed {sys_deps}")


@main.command()
def update():
    """update current project"""
    raise NotImplementedError()


@main.command()
def dist():
    """create distributables"""
    project = Project.find()

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
    project = Project.find()

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
    project = Project.find()
    ret_code = run_tests(project)
    sys.exit(ret_code)


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
