from __future__ import annotations

from typing import Set, Optional, NamedTuple
import os
import dataclasses
import configparser
import pathlib
import subprocess

import pkg_resources
import tomlkit


# If we find any of these files we assume this is the root folder of a python project
PYTHON_PROJECT_ROOT_FILES = {
    "pyproject.toml",
    "setup.py",
}


def find_project_root(path: pathlib.Path = pathlib.Path(".")) -> pathlib.Path:
    path = path.absolute()
    files_in_folder = set(os.listdir(path))
    if PYTHON_PROJECT_ROOT_FILES.intersection(files_in_folder):
        return path

    parent = path.parent
    if parent == path:
        raise AttributeError("project root not found")

    return find_project_root(parent)


def find(path: pathlib.Path = pathlib.Path(".")) -> Base:
    path = find_project_root(path)
    return get_instance(path)


def get_instance(path) -> Base:
    project_data = ProjectData(path)

    for cls in [Poetry, Pipenv]:
        if cls.supported(project_data):
            return cls(project_data)

    raise AttributeError("not a supported python project")


class ProjectData:
    pyproject: Optional[tomlkit.document] = None

    def __init__(self, path: pathlib.Path) -> None:
        self.path = path

        if self.pyproject_path.is_file():
            tomlkit.document()
            with open(self.pyproject_path) as config_fo:
                config_data = config_fo.read()
            self.pyproject = tomlkit.loads(config_data)

    @property
    def pyproject_path(self) -> pathlib.Path:
        return self.path / "pyproject.toml"

    @property
    def pipfile_path(self) -> pathlib.Path:
        return self.path / "Pipfile"

    @property
    def setuppy_path(self) -> pathlib.Path:
        return self.path / "setup.py"

    @property
    def pylintrc_path(self) -> pathlib.Path:
        project_sepecific_pylintrc = self.path / ".pylintrc"
        if project_sepecific_pylintrc.is_file():
            return project_sepecific_pylintrc

        return pathlib.Path(pkg_resources.resource_filename("cpa", "pylintrc"))


@dataclasses.dataclass
class Config:
    name: str
    public: bool


class Base:
    def __init__(self, project_data: ProjectData):
        self.data = project_data

    @classmethod
    def supported(cls, project_data: ProjectData) -> bool:
        return False

    def metadata(self) -> Config:
        name = None
        public = False

        if self.data.pyproject:
            tool = self.data.pyproject.get("tool", {})
            name = tool.get("poetry", {}).get("name", None)
            name = tool.get("cpa", {}).get("name", name)
            public = tool.get("cpa", {}).get("public", public)

        if name is None:
            raise AttributeError("Could not determine package name")

        metadata = Config(name, public)
        return metadata

    def run(self, cmd, capture=True) -> CommandResult:
        """Run commands in a subprocess"""
        raise NotImplementedError()

    def install(self) -> CommandResult:
        """Install python packages"""
        raise NotImplementedError()

    def get_packages_list(self) -> Set[str]:
        """Returns a list of python packages used by pipenv/poetry"""
        raise NotImplementedError()


class CommandResult(NamedTuple):
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


class Pipenv(Base):
    @classmethod
    def supported(cls, project_data: ProjectData) -> bool:
        if not project_data.pipfile_path.is_file():
            return False

        return project_data.setuppy_path.is_file()

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
        parser.read(os.path.join(self.data.path, "Pipfile"))

        for pkg in parser["packages"]:
            packages_list.append(pkg)
        for pkg in parser["dev-packages"]:
            packages_list.append(pkg)

        return set(packages_list)


class Poetry(Base):
    @classmethod
    def supported(cls, project_data: ProjectData) -> bool:
        if not project_data.pyproject:
            return False

        build_system = project_data.pyproject.get("build-system")

        if not build_system:
            return False

        if "build-backend" not in build_system:
            return False

        return build_system["build-backend"] == "poetry.core.masonry.api"

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
        assert self.data.pyproject
        tool = self.data.pyproject.get("tool", {})
        deps = tool.get("poetry", {}).get("dependencies", {})
        dev_deps = tool.get("poetry", {}).get("dev-dependencies", {})
        packages_list = list(deps.keys()) + list(dev_deps.keys())
        return set(packages_list)
