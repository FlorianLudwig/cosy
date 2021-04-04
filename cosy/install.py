from typing import Set, List
import logging
import subprocess

import distro
import yaml
import pkg_resources

logger = logging.getLogger(__name__)

PACKAGE_DATA_PATH = pkg_resources.resource_filename("cosy", "packages.yml")
PACKAGES = yaml.safe_load(open(PACKAGE_DATA_PATH))


class System:
    build_system: List[str]
    name: str

    def __init__(self):
        self.initial_packages = set()
        self.build_packages = set()
        self.run_packages = set()

    @classmethod
    def get_current(cls):
        system = distro.linux_distribution()[0]
        if system == "Fedora":
            return Fedora()
        else:
            return Ubuntu()

    def python_pkg_deps(self, dep, run_only=False) -> Set[str]:
        """Get all system dependencies for a certain python package"""
        build_packages = set()
        run_packages = set()

        package = dep.strip().lower()
        if package in PACKAGES and self.name in PACKAGES[package]:
            deps = PACKAGES[package][self.name]
            run_packages.update(deps.get("run", []))
            if not run_only:
                build_packages.update(deps.get("collect", []))
                build_packages.update(deps.get("build", []))

        to_install = set(self.build_system)
        to_install.update(build_packages)
        to_install.update(run_packages)
        self.run_packages.update(run_packages)
        self.build_packages.update(build_packages)
        return to_install

    def cleanup(self):
        """Remove not needed dependencies"""
        to_remove = self.build_packages.union(self.build_system)
        to_keep = self.initial_packages.union(self.run_packages)

        for pkg in to_keep:
            to_remove.discard(pkg)

        self.remove(to_remove)

    def install(self, packages):
        """install given packages"""
        if isinstance(self, Fedora):
            cmd = ["dnf", "install", "-y"]
        elif isinstance(self, Ubuntu):
            cmd = ["apt", "install", "-y"]

        for pkg in packages:
            # if pkg not in self.installed_packages:
            cmd.append(pkg)

        if packages:
            subprocess.Popen(cmd).wait()

    def remove(self, packages):
        """remove packages if not already installed on pip startup"""
        if isinstance(self, Fedora):
            cmd = ["dnf", "remove", "-y"]
        elif isinstance(self, Ubuntu):
            cmd = ["apt", "remove", "-y"]

        if packages:
            cmd = cmd + list(packages)
            subprocess.Popen(cmd).wait()


class Fedora(System):
    build_system = ["redhat-rpm-config", "gcc", "python3-devel"]
    name = "fedora"

    def __init__(self):
        super().__init__()
        # pylint: disable=import-error
        # pylint: disable=import-outside-toplevel
        import dnf

        self.dnf = dnf
        self.base = None
        self._get_dnf()
        self.initial_packages = self.installed_packages

    def _get_dnf(self):
        if self.base is not None:
            self.base.close()
        self.base = self.dnf.Base()
        self.base.conf.assumeyes = True
        self.base.read_all_repos()
        self.base.fill_sack(load_system_repo="auto")
        installed = self.base.sack.query().installed()
        self.installed_packages = set(p.name for p in installed.run())

    def install_api(self, packages):
        """install packages using the dnf python api

        XXX not used because of memory leak, see
        https://bugzilla.redhat.com/show_bug.cgi?id=1461423"""
        # check to pass mypy that none object doesn't have ... attributes
        if self.base:
            for pkg in packages:
                if pkg not in self.installed_packages:
                    try:
                        self.base.install(pkg)
                    except self.dnf.exceptions.Error:
                        print("dnf error finding: " + pkg)
            self.base.resolve()
            self.base.download_packages(self.base.transaction.install_set)
            self.base.do_transaction()
            self._get_dnf()

    def remove_api(self, packages):
        """using dnf-python

        not used because of memory leak"""
        if self.base:
            for pkg in packages:
                self.base.remove(pkg)

            # ensure we are not losing runtime packages
            for pkg in self.run_packages:
                self.base.install(pkg)

            self.base.resolve()
            self.base.do_transaction()
            self._get_dnf()


class Ubuntu(System):
    build_system = ["build-essential"]
    name = "ubuntu"

    def __init__(self):
        super().__init__()

        self.load_installed_packages()
        self.initial_packages = self.installed_packages

    def load_installed_packages(self):
        cmd = ["apt", "list", "--installed"]

        proc = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        assert proc.stdout is not None  # make mypy happy
        outs = proc.stdout.read().decode("utf-8").splitlines()
        deps_list = []
        for dependency in outs:
            if "/" not in dependency:
                continue
            deps_list.append(dependency.split("/")[0])

        self.installed_packages = set(deps_list)
