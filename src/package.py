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
        ["apt-get", "update", "-yq"],
        ["apt-get", "install", "-yq", *packages],
        ["apt-get", "autoremove", "-yq"],
    ]
    for cmd in cmds:
        rc = subprocess.call(cmd, env={**os.environ})
        if rc != 0:
            return False
    mark_need_reboot()
    return True


def _installed_nvidia_packages():
    """
    Names of currently-installed packages whose name starts with
    'nvidia-'. apt does not glob argv (no shell), so we must pass a
    concrete list.
    """
    try:
        cache = apt.Cache()
    except Exception as e:
        print(
            "install_nouveau: failed to open apt cache: {}".format(e),
            file=sys.stderr,
        )
        return []
    names = []
    for pkg in cache:
        try:
            if pkg.is_installed and pkg.name.startswith("nvidia-"):
                names.append(pkg.name)
        except Exception:
            continue
    return names


def install_nouveau():
    nvidia_pkgs = _installed_nvidia_packages()

    cmds = []
    if nvidia_pkgs:
        cmds.append(["apt", "purge", "-yq", *nvidia_pkgs])
    cmds.append(["apt", "purge", "-yq", "xserver-xorg-video-nvidia"])
    cmds.append(["apt", "autoremove", "-yq"])
    cmds.append(["apt", "install", "-yq", nouveau])

    for cmd in cmds:
        rc = subprocess.call(cmd, env={**os.environ})
        if rc != 0:
            return False
    mark_need_reboot()
    return True

def update():
    backup = dest + ".prev"
    had = os.path.isfile(dest)
    try:
        if had:
            os.replace(dest, backup)
        else:
            shutil.copyfile(src_list, dest)

        rc = subprocess.call(
            ["apt", "update", "-yq"], env={**os.environ}
        )
        if rc != 0:
            raise RuntimeError("apt update failed with rc={}".format(rc))

        if had and os.path.isfile(backup):
            os.remove(backup)
        return True

    except Exception as e:
        print(
            "update: rolling back due to error: {}".format(e),
            file=sys.stderr,
        )
        if had:
            if os.path.isfile(backup):
                os.replace(backup, dest)
        else:
            if os.path.isfile(dest):
                os.remove(dest)
        return False


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
