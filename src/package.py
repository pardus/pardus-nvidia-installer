#!//usr/bin/env python3
import gi
import os
import apt
import sys
import subprocess
from gi.repository import GLib, Gio

cache = apt.Cache()


def update():
    cache.update()
    # res = subprocess.getoutput("apt update")


def main():
    args = sys.argv
    if len(args) > 1:
        if args[1] == "update":
            update()
    else:
        print("no argument passed on")


def get_pkg_info(package_name: str):
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
