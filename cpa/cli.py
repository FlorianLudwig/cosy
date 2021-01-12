"""Console script for create python app."""
from __future__ import annotations

from typing import Set
import sys
import os
import subprocess
import typing
import shutil
import dataclasses
from typing import Optional

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
    def find(cls) -> Project:
        path = find_project_root()
        return cls(path)

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

    def get_packaging_sys(self) -> str:
        files_in_folder = os.listdir(self.path)
        if "Pipfile.lock" in files_in_folder:
            return "pipenv"
        elif "poetry.lock" in files_in_folder:
            return "poetry"


    def python_deps(self) -> Set[str]:
        packages_list = []
        packaging_sys = self.get_packaging_sys()
        if packaging_sys == "pipenv":
            cmd = ["pip", "freeze"]
            res = pipenv_run(cmd)
            packages = set(res.output.splitlines())
            for package in packages:
                # skip editable pacakages
                if package.startswith('-e'):
                    continue
                packages_list.append(package.split("==")[0])
        else:
            tool = self.pyproject.get("tool", {})
            deps = tool.get("poetry", {}).get("dependencies", {})
            dev_deps = tool.get("poetry", {}).get("dev-dependencies", {})
            packages_list = list(deps.keys()) + list(dev_deps.keys())

        return packages_list


def run_tests(project: Project) -> int:
    conf = project.metadata()
    module = conf.name

    # allow syntax new in python 3.6
    cmd = ["black", "--check", "--target-version", "py36", "."]
    style_res = pipenv_run(cmd)

    cmd = ["pylint", f"--rcfile={project.pylintrc}", module]
    pylint_res = pipenv_run(cmd)

    cmd = [
        "mypy",
        "--no-incremental",
        "--ignore-missing-imports",
        "--warn-unreachable",
        "--check-untyped-defs",
        module,
    ]
    mypy_res = pipenv_run(cmd)

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


def pipenv_run(cmd) -> CommandResult:
    cmd = ["pipenv", "run"] + cmd
    return run(cmd)


def run(cmd, capture=True) -> CommandResult:
    if capture:
        proc = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        assert proc.stdout is not None  # makes mypy happy
        return CommandResult(proc.stdout.read().decode("utf-8"), proc.wait())
    else:
        proc = subprocess.Popen(cmd)
        return CommandResult("", proc.wait())


@main.command()
def new():
    """create new project"""
    raise NotImplementedError()


@main.command()
def install():
    """install dependencies via pipenv/poetry"""
    project = Project.find()
    packaging_sys = project.get_packaging_sys()
    if packaging_sys == 'pipenv':
        click.echo(run(["pipenv", "install", "--ignore-pipfile"]).output)
    elif pacakaging_sys == 'poetry':
        click.echo(run(["poetry", "install"]).output)


@main.command()
@click.option("--run-only", "-r", "run_only",  is_flag=True)
def sysdeps(run_only):
    "List all system dependencies required"
    system = cpa.install.System.get_current()
    project = Project.find()
    python_dependencies = project.python_deps()
    sys_deps = set()
    for package in python_dependencies:
        deps_to_install = system.install_python_pkg_deps(package, run_only, install=False)
        sys_deps.update(deps_to_install)
    
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

    click.echo(pipenv_run(["python", "setup.py", "sdist"]).output)
    click.echo(pipenv_run(["python", "setup.py", "bdist_wheel"]).output)


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
    pipenv_run(cmd, capture=False)


@main.command()
def test() -> None:
    """run tests"""
    project = Project.find()
    ret_code = run_tests(project)
    sys.exit(ret_code)


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
