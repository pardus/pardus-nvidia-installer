#!//usr/bin/env python3
import os
import apt
import sys
import subprocess
import shutil
import apt_pkg

apt_pkg.init_system()
os.environ["DEBIAN_FRONTEND"] = "noninteractive"
nouveau = "xserver-xorg-video-nouveau"


nvidia_modprobe_conf = "/etc/modprobe.d/nvidia.conf"
nvidia_modprobed_conf = "/etc/modprobe.d/nvidia.conf.bak"
nouveau_modprobe_conf = "/etc/modprobe.d/nvidia-blacklists-nouveau.conf"
nouveau_modprobed_conf = "/etc/modprobe.d/nvidia-blacklists-nouveau.conf.bak"
nvidia_disable_gpu_path = "/var/cache/pni-disable-gpu"
nvidia_src_file = "nvidia-drivers.list"
dest = "/etc/apt/sources.list.d/nvidia-drivers.list"
src_list = os.path.dirname(__file__) + "/../" + nvidia_src_file


def sys_source():
    return os.path.isfile(dest)


compare_version = apt_pkg.version_compare


def mark_need_reboot():
    with open("/run/pardus-nvi.reboot", "w") as f:
        f.write("1")

def disable_sec_gpu():
    changed = False
    if not os.path.isfile(nvidia_disable_gpu_path):
        with open(nvidia_disable_gpu_path, "a") as f:
            f.write("Secondary GPU Disabled")
        changed = True

    if os.path.isfile(nvidia_modprobe_conf):
        os.rename(nvidia_modprobe_conf, nvidia_modprobed_conf)
        changed = True
    if os.path.isfile(nouveau_modprobe_conf):
        os.rename(nouveau_modprobe_conf, nouveau_modprobed_conf)
        changed = True
    if changed:
        mark_need_reboot()
    return True


def enable_sec_gpu():
    changed = False
    if os.path.isfile(nvidia_disable_gpu_path):
        os.remove(nvidia_disable_gpu_path)
        changed = True
    if os.path.isfile(nvidia_modprobed_conf):
        os.rename(nvidia_modprobed_conf, nvidia_modprobe_conf)
        changed = True
    if os.path.isfile(nouveau_modprobed_conf):
        os.rename(nouveau_modprobed_conf, nouveau_modprobe_conf)
        changed = True
    if changed:
        mark_need_reboot()
    return True

def check_sec_state():
    return not os.path.isfile(nvidia_disable_gpu_path)


def install_nvidia(packages):
    if not packages:
        print("install_nvidia: no packages provided, aborting", file=sys.stderr)
        return False
    cmds = [
        ["apt", "update", "-yq"],
        ["apt", "purge", "-yq", "nvidia-*driver", "nvidia-kernel-*"],
        ["apt", "autoremove", "-yq"],
        ["apt", "install", "-yq", *packages],
    ]
    for cmd in cmds:
        rc = subprocess.call(cmd, env={**os.environ})
        if rc != 0:
            return False
    mark_need_reboot()
    return True


def install_nouveau():
    cmds = [
        ["apt", "purge", "-yq", "nvidia-*driver", "nvidia-kernel-*"],
        ["apt", "purge", "-yq", "xserver-xorg-video-nvidia"],
        ["apt", "autoremove", "-yq"]
    ]
    for cmd in cmds:
        rc = subprocess.call(cmd, env={**os.environ})
        if rc != 0:
            return False
    mark_need_reboot()
    return True

def update():
    if os.path.isfile(dest):
        os.remove(dest)
    else:
        shutil.copyfile(src_list, dest)

    rc = subprocess.call(
        ["apt", "update", "-yq"], env={**os.environ}
    )
    return rc == 0


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
    if len(args) <= 1:
        print("no argument passed on", file=sys.stderr)
        sys.exit(2)

    param1 = args[1]
    if param1 == "nouveau" or param1 == nouveau or param1 == "install-nouveau":
        ok = install_nouveau()
    elif param1 == "update":
        ok = update()
    elif param1 == "disable-sec-gpu":
        ok = disable_sec_gpu()
    elif param1 == "enable-sec-gpu":
        ok = enable_sec_gpu()
    elif param1 == "install-nvidia":
        ok = install_nvidia(args[2:])
    else:
        print("unknown subcommand: {}".format(param1), file=sys.stderr)
        sys.exit(2)

    sys.exit(0 if ok else 1)
