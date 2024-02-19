#!//usr/bin/env python3
import os
import apt
import sys
import subprocess
import shutil
import nvidia

os.environ["DEBIAN_FRONTEND"] = "noninteractive"
nouveau = "xserver-xorg-video-nouveau"

nvidia_disable_gpu_path = "/var/cache/pni-disable-gpu"
nvidia_src_file = "nvidia-drivers.list"
dest = "/etc/apt/sources.list.d/nvidia-drivers.list"
src_list = os.path.dirname(__file__) + "/../" + nvidia_src_file


def sys_source():
    return os.path.isfile(dest)


def disable_sec_gpu():
    if not os.path.isfile(nvidia_disable_gpu_path):
        with open(nvidia_disable_gpu_path,"a") as f:
            f.write("Secondary GPU Disabled")
def enable_sec_gpu():
    if os.path.isfile(nvidia_disable_gpu_path):
        os.remove(nvidia_disable_gpu_path)
        
def check_sec_state():
    if os.path.isfile(nvidia_disable_gpu_path):
        return False
    return True

def toggle_source_list():
    src_state = sys_source()
    if src_state:
        os.remove(dest)
    else:
        shutil.copyfile(src_list, dest)


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


def update():
    if os.path.isfile(dest):
        os.remove(dest)
    else:
        shutil.copyfile(src_list, dest)
    
    subprocess.call(
        ["apt", "update", "-yq", "-o", "APT::Status-Fd=1"], env={**os.environ}
    )


def get_pkg_info(package_name: str):
    cache = apt.Cache()
    pkg = cache[package_name]
    if pkg.is_installed:
        version = pkg.installed.version
        name = pkg.installed.summary
    else:
        version = pkg.versions[0].version
        name = pkg.versions[0].summary

    return {"ver": version, "name": name}


if __name__ == "__main__":
    args = sys.argv
    if len(args) > 1:
        if args[1] == nouveau:
            install_nouveau()
        elif args[1] == "update":
            update()
        elif args[1] == "disable-sec-gpu":
            disable_sec_gpu()
        elif args[1] == "enable-sec-gpu":
            enable_sec_gpu()
        else:
            install_nvidia(args[1])

    else:
        print("no argument passed on")
