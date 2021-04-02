from __future__ import annotations

from typing import Set, Optional, Callable
import os
import dataclasses
import configparser
import pathlib

import pkg_resources
import tomlkit


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


class Base:
    def __init__(self, project_data:ProjectData):
        self.data = project_data

    @classmethod
    def supported(cls, project_data:ProjectData) -> bool:
        return False

class Pipenv(Base):
    @classmethod
    def supported(cls, project_data:ProjectData) -> bool:
        if not project_data.pipfile_path.is_file():
            return False
        
        return project_data.setuppy_path.is_file()



class Poetry(Base):

    @classmethod
    def supported(cls, project_data:ProjectData) -> bool:
        if not project_data.pyproject:
            return False

        build_system = project_data.pyproject.get("build-system")

        if not build_system:
            return False

        if "build-backend" not in build_system:
            return False

        return build_system["build-backend"] == "poetry.core.masonry.api"
