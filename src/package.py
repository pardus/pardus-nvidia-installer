#!//usr/bin/env python3
import gi
import os
import apt
import sys
import subprocess
from gi.repository import GLib, Gio
from package_progress import CustomAcquireProgress, CustomInstallProgress


def update():
    cache = apt.Cache()
    cache.update()


def install(package_names):
    cache = apt.Cache()
    cache.update()
    cache.open()

    for package_name in package_names:
        if not cache[package_name].is_installed:
            pkg = cache[package_name]
            pkg.mark_install()
    try:
        acq_prs = CustomAcquireProgress()
        ins_prs = CustomInstallProgress()
        cache.commit(acq_prs, ins_prs)
        print(f"package {package_name} installed successfully")

    except Exception as e:
        print(f"error occured while installing package. err: {e}")


def main():
    args = sys.argv
    if len(args) > 1:
        if args[1] == "update":
            update()
        if args[1] == "install":
            install([args[2]])

    else:
        print("no argument passed on")


def get_pkg_info(package_name: str):
    cache = apt.Cache()
    pkg = cache[package_name]
    if pkg.is_installed:
        version = pkg.installed.version
        name = pkg.installed.raw_description
    else:
        version = pkg.versions[0].version
        name = pkg.versions[0].raw_description

    return {"ver": version, "name": name}


if __name__ == "__main__":
    main()
