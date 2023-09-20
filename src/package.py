#!//usr/bin/env python3
import os
import apt
import sys
import subprocess

os.environ["DEBIAN_FRONTEND"] = "noninteractive"


def update():
    pass


def install(pkg_name, fd):
    subprocess.call(
        ["apt", "install", "-yq", "-o", f"APT::Status-Fd={fd}", pkg_name],
        env={**os.environ},
    )


def remove():
    pass


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
    args = sys.argv
    if len(args) > 1:
        if args[1] == "update":
            update()
        if args[1] == "install":
            pkg_nm = args[2]
            fd = args[3]
            install(pkg_nm, fd)

    else:
        print("no argument passed on")
