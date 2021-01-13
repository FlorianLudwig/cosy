from typing import Set
import logging
import sys
import subprocess
import distro

import yaml
import pkg_resources

logger = logging.getLogger(__name__)

PACKAGE_DATA_PATH = pkg_resources.resource_filename('cpa', 'packages.yml')
PACKAGES = yaml.safe_load(open(PACKAGE_DATA_PATH))


class System(object):
    def __init__(self):
        self.build_packages = set()
        self.run_packages = set()

    @classmethod
    def get_current(cls):
        system = distro.linux_distribution()[0]
        if system == 'Fedora':
            return Fedora()
        else:
            return Ubuntu()

    def python_pkg_deps(self, dep, run_only=False) -> Set[str]:
        """Get all system dependencies for a certain python package"""
        stages = ['build', 'run', 'collect']
        build_packages = set()
        run_packages = set()

        package = dep.strip().lower()
        if package in PACKAGES and self.name in PACKAGES[package]:
            deps = PACKAGES[package][self.name]
            run_packages.update(deps.get('run', []))
            if not run_only:
                build_packages.update(deps.get('collect', []))
                build_packages.update(deps.get('build', []))

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
        raise NotImplementedError()

    def remove(self, packages):
        """remove packages if not already installed on pip startup"""
        raise NotImplementedError()


class Fedora(System):
    build_system = ['redhat-rpm-config', 'gcc', 'python3-devel']
    name = 'fedora'

    def __init__(self):
        super(Fedora, self).__init__()
        global dnf
        import dnf
        self.base = None
        self._get_dnf()
        self.initial_packages = self.installed_packages

    def _get_dnf(self):
        if self.base is not None:
            self.base.close()
        self.base = dnf.Base()
        self.base.conf.assumeyes = True
        self.base.read_all_repos()
        self.base.fill_sack(load_system_repo='auto')
        installed = self.base.sack.query().installed()
        self.installed_packages = set(p.name for p in installed.run())

    def install(self, packages):
        """install packages by calling dnf as subprocess"""
        cmd = ['dnf', 'install', '-y']

        for pkg in packages:
            # if pkg not in self.installed_packages:
            cmd.append(pkg)

        if packages:
            subprocess.Popen(cmd).wait()

    def install_api(self, packages):
        """install packages using the dnf python api

        XXX not used because of memory leak, see
        https://bugzilla.redhat.com/show_bug.cgi?id=1461423"""

        for pkg in packages:
            if pkg not in self.installed_packages:
                try:
                    self.base.install(pkg)
                except:
                    print("dnf error finding: " + pkg)
        self.base.resolve()
        self.base.download_packages(self.base.transaction.install_set)
        self.base.do_transaction()
        self._get_dnf()

    def remove(self, packages):
        """remove packages by calling dnf as subprocess"""
        if packages:
            cmd = ['dnf', 'remove'] + list(packages)
            subprocess.Popen(cmd).wait()

    def remove_api(self, packages):
        """using dnf-python

        not used because of memory leak"""
        for pkg in packages:
            self.base.remove(pkg)

        # ensure we are not losing runtime packages
        for pkg in self.run_packages:
            self.base.install(pkg)

        self.base.resolve()
        self.base.do_transaction()
        self._get_dnf()


class Ubuntu(System):
    build_system = ['build-essential']
    name = 'ubuntu'

