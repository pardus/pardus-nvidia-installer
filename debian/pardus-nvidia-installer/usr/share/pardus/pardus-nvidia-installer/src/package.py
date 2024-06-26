#!//usr/bin/env python3
import os
import apt
import sys
import subprocess
import dbus

os.environ["DEBIAN_FRONTEND"] = "noninteractive"


def install_nvidia(nv_drv):
    subprocess.call(
        ["apt", "update", "-yq", "-o", "APT::Status-Fd=1"],
        env={**os.environ},
    )

    subprocess.call(
        ["apt", "remove", "-yq", "-o", "APT::Status-Fd=1", "nvidia-*"],
        env={**os.environ},
    )
    subprocess.call(
        ["apt", "install", "-yq", "-o", "APT::Status-Fd=1", nv_drv],
        env={**os.environ},
    )


def install_nouveau():
    subprocess.call(
        ["apt", "remove", "-yq", "-o", "APT::Status-Fd=1", "nvidia-*"],
        env={**os.environ},
    )


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
        if args[1] == "nouveau":
            print("pkg.py nouveau")
            install_nouveau()
        if args[1] == "nvidia":
            nv_drv = args[2]
            install_nvidia(nv_drv)

    else:
        print("no argument passed on")
