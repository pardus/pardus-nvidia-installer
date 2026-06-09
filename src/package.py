#!/usr/bin/env python3
import os
import re
import apt
import sys
import subprocess
import apt_pkg

apt_pkg.init_system()
os.environ["DEBIAN_FRONTEND"] = "noninteractive"
nouveau = "xserver-xorg-video-nouveau"


nvidia_modprobe_conf = "/etc/modprobe.d/nvidia.conf"
nvidia_modprobed_conf = "/etc/modprobe.d/nvidia.conf.bak"
nouveau_modprobe_conf = "/etc/modprobe.d/nvidia-blacklists-nouveau.conf"
nouveau_modprobed_conf = "/etc/modprobe.d/nvidia-blacklists-nouveau.conf.bak"
nvidia_disable_gpu_path = "/var/cache/pni-disable-gpu"
pci_rescan_path = "/sys/bus/pci/rescan"
dest = "/etc/apt/sources.list.d/nvidia-drivers.list"

# Keyring shipped/dearmored by the package (see debian/postinst) and the
# armored source used to (re)build it on demand.
nvidia_keyring = "/usr/share/keyrings/nvidia-drivers.gpg"
nvidia_pub_src = os.path.dirname(__file__) + "/../nvidia.pub"

cuda_repo_base = "https://developer.download.nvidia.com/compute/cuda/repos"

# NVIDIA signs each CUDA repository with a per-distribution key:
#   debian12 -> "cudatools"                 (A4B469963BF863CC, SHA1 self-sig)
#   debian13 -> "Kitmaker (Debian 13 ...)"  (...97A5D4CB8793F200, SHA256)
# Both public keys MUST live in nvidia.pub (postinst dearmors it into the
# keyring); this maps the distro we point apt at to the fingerprint its
# Release file is signed with, so we can verify the keyring before apt runs.
#
# To add a new release (e.g. debian14) you only touch TWO places that must
# stay in sync: add the fingerprint here AND its armored key to nvidia.pub.
# _SUPPORTED_CUDA_MAJORS is derived from this map so it can never drift.
_CUDA_REPO_KEY_FPR = {
    "debian12": "EB693B3035CD5710E231E123A4B469963BF863CC",
    "debian13": "02182E60104FCDC26EAE1B8597A5D4CB8793F200",
}

# Major versions this tool can target, ascending, derived from the key map
# above so there is a single source of truth. Used to clamp the detected
# Debian release onto something NVIDIA actually publishes.
_SUPPORTED_CUDA_MAJORS = tuple(
    sorted(int(d[len("debian"):]) for d in _CUDA_REPO_KEY_FPR)
)

_DEBIAN_CODENAME_MAJOR = {
    "bullseye": 11,
    "bookworm": 12,
    "trixie": 13,
    "forky": 14,
}


def readfile(filepath):
    if not os.path.isfile(filepath):
        return None
    try:
        with open(filepath, "r") as f:
            return f.read().strip()
    except OSError:
        return None


def sys_source():
    return os.path.isfile(dest)


def _debian_major():
    """
    Detection of the Debian base major version.

    Pardus carries its own VERSION_CODENAME (e.g. "yirmibes"), so os-release
    is unreliable for this; /etc/debian_version ("13.5", "trixie/sid", ...)
    is the ground truth for the apt base and is checked first.
    Returns an int, or None when nothing usable is found.
    """
    raw = readfile("/etc/debian_version")
    if raw:
        m = re.match(r"^(\d+)", raw)
        if m:
            return int(m.group(1))
        codename = raw.split("/", 1)[0].strip().lower()
        major = _DEBIAN_CODENAME_MAJOR.get(codename)
        if major:
            return major

    for path in ("/etc/os-release", "/usr/lib/os-release"):
        content = readfile(path)
        if not content:
            continue
        for line in content.splitlines():
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            if key.strip() in ("DEBIAN_CODENAME", "VERSION_CODENAME"):
                codename = val.strip().strip('"').strip("'").lower()
                major = _DEBIAN_CODENAME_MAJOR.get(codename)
                if major:
                    return major
    return None


def cuda_repo_distro():
    """
    Pick the CUDA repo slug ("debian12"/"debian13") for this machine,
    clamped to what NVIDIA actually ships so an unknown future release still
    resolves to the closest available repository instead of a 404.
    """
    major = _debian_major()
    if major is None:
        # Detection failed. "Unknown" almost always means "newer than us"
        # (and older systems carry a readable /etc/debian_version), so bias
        # to the newest supported release: its key uses a modern digest that
        # trixie+ accept, avoiding the SHA1 wall of the oldest repo.
        major = _SUPPORTED_CUDA_MAJORS[-1]
        print(
            "cuda_repo_distro: could not detect Debian base; "
            "defaulting to debian{}".format(major),
            file=sys.stderr,
        )
    elif major < _SUPPORTED_CUDA_MAJORS[0]:
        major = _SUPPORTED_CUDA_MAJORS[0]
    elif major > _SUPPORTED_CUDA_MAJORS[-1]:
        major = _SUPPORTED_CUDA_MAJORS[-1]
    return "debian{}".format(major)


def _nvidia_source_line(distro=None):
    if distro is None:
        distro = cuda_repo_distro()
    return (
        "deb [signed-by={keyring}] {base}/{distro}/x86_64/ /\n".format(
            keyring=nvidia_keyring, base=cuda_repo_base, distro=distro
        )
    )


def _keyring_has_fingerprint(keyring, fingerprint):
    """
    True when `keyring` contains a key with the given fingerprint.
    """
    if not os.path.isfile(keyring):
        return False
    try:
        out = subprocess.run(
            ["gpg", "--no-default-keyring", "--show-keys",
             "--with-colons", "--with-fingerprint", keyring],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        ).stdout.decode("utf-8", "replace")
    except (OSError, ValueError):
        return False
    for line in out.splitlines():
        parts = line.split(":")
        if parts and parts[0] == "fpr" and len(parts) >= 10:
            if parts[9].upper() == fingerprint.upper():
                return True
    return False


def _build_keyring_from_pub():
    """
    (Re)create the apt keyring by dearmoring the shipped nvidia.pub.

    nvidia.pub holds every CUDA signing key this tool supports, so the
    resulting keyring can verify whichever debianNN repo we enable. Written
    atomically with 0644 so apt will actually read it.
    """
    if not os.path.isfile(nvidia_pub_src):
        print(
            "ensure_keyring: armored key source missing: {}".format(
                nvidia_pub_src
            ),
            file=sys.stderr,
        )
        return False
    try:
        with open(nvidia_pub_src, "rb") as src:
            proc = subprocess.run(
                ["gpg", "--dearmor"],
                stdin=src, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
        if proc.returncode != 0 or not proc.stdout:
            print(
                "ensure_keyring: gpg --dearmor failed: {}".format(
                    proc.stderr.decode("utf-8", "replace").strip()
                ),
                file=sys.stderr,
            )
            return False
        os.makedirs(os.path.dirname(nvidia_keyring), exist_ok=True)
        tmp = nvidia_keyring + ".tmp"
        with open(tmp, "wb") as out:
            out.write(proc.stdout)
        os.chmod(tmp, 0o644)
        os.replace(tmp, nvidia_keyring)
        return True
    except OSError as e:
        print(
            "ensure_keyring: failed to build {}: {}".format(
                nvidia_keyring, e
            ),
            file=sys.stderr,
        )
        return False


def ensure_keyring(distro):
    """
    Guarantee the keyring can verify `distro` before apt touches the repo.

    This is what stops the "cuda-keyring"/NO_PUBKEY failure: enabling the
    Debian 13 repo needs the Kitmaker key, which older installs' keyrings
    lack. If the required key is absent we rebuild the keyring from the
    shipped, fully-populated nvidia.pub.
    """
    fpr = _CUDA_REPO_KEY_FPR.get(distro)
    if fpr is None:
        # Unknown distro: nothing to assert, leave the keyring untouched.
        return True
    if _keyring_has_fingerprint(nvidia_keyring, fpr):
        return True
    if not _build_keyring_from_pub():
        return False
    return _keyring_has_fingerprint(nvidia_keyring, fpr)


compare_version = apt_pkg.version_compare


def mark_need_reboot():
    with open("/run/pardus-nvi.reboot", "w") as f:
        f.write("1")


def move_conf_if_dest_absent(src, dst):
    """
    Move `src` to `dst`, but only if `dst` doesn't already exist, so we
    never clobber what's there: a hand-edited conf when enabling, or an
    earlier pre-disable backup when disabling. Returns True if it moved
    """
    if not (os.path.isfile(src) and not os.path.isfile(dst)):
        return False
    try:
        os.replace(src, dst)
        return True
    except OSError as e:
        print(
            "move conf: failed to move {} -> {}: {}".format(src, dst, e),
            file=sys.stderr,
        )
        return False


def disable_sec_gpu():
    changed = False
    if not os.path.isfile(nvidia_disable_gpu_path):
        with open(nvidia_disable_gpu_path, "a") as f:
            f.write("Secondary GPU Disabled")
        changed = True

    if move_conf_if_dest_absent(nvidia_modprobe_conf, nvidia_modprobed_conf):
        changed = True
    if move_conf_if_dest_absent(nouveau_modprobe_conf, nouveau_modprobed_conf):
        changed = True
    if changed:
        mark_need_reboot()
    return True


def rescan_pci():
    """
    Re-add the GPU in the running session without waiting for a reboot

    Clearing the marker only stops the boot script's future removals; the
    device the script already hot-removed stays gone until the bus is
    rescanned. (A reboot brings it back too, since firmware re-enumerates
    from scratch.) Best-effort; failures are non-fatal.
    """
    try:
        with open(pci_rescan_path, "w") as f:
            f.write("1")
    except OSError as e:
        print(
            "enable_sec_gpu: pci rescan failed: {}".format(e),
            file=sys.stderr,
        )


def enable_sec_gpu():
    changed = False
    if os.path.isfile(nvidia_disable_gpu_path):
        os.remove(nvidia_disable_gpu_path)
        changed = True
    if move_conf_if_dest_absent(nvidia_modprobed_conf, nvidia_modprobe_conf):
        changed = True
    if move_conf_if_dest_absent(nouveau_modprobed_conf, nouveau_modprobe_conf):
        changed = True
    # Symmetric inverse of the boot-time PCI hot-remove. Done unconditionally
    # (not gated on `changed`) so a previously removed device is recovered
    # even when the marker/confs were already cleaned up out of band.
    rescan_pci()
    if changed:
        mark_need_reboot()
    return True

def check_sec_state():
    return not os.path.isfile(nvidia_disable_gpu_path)


# install_nvidia runs under pkexec with root privileges. Restrict the
# packages it will install to what this tool legitimately manages:
# kernel headers, NVIDIA proprietary drivers, and the nouveau fallback.
# Anything else (option-injection like "--reinstall", path traversal,
# arbitrary repository packages) must be refused before reaching apt.
_LINUX_HEADERS_RE = re.compile(r"^linux-headers-[a-zA-Z0-9\.\-_+]+$")
_NVIDIA_DRIVER_RE = re.compile(r"^nvidia-[a-zA-Z0-9\-_]+$")


def _is_allowed_package(name):
    if not name or len(name) > 100:
        return False
    if name.startswith("-"):
        return False
    if name == nouveau:
        return True
    if _LINUX_HEADERS_RE.match(name):
        return True
    if _NVIDIA_DRIVER_RE.match(name):
        return True
    return False


def install_nvidia(packages):
    if not packages:
        print("install_nvidia: no packages provided, aborting", file=sys.stderr)
        return False
    for pkg in packages:
        if not _is_allowed_package(pkg):
            print(
                "install_nvidia: refusing unsafe package name: {!r}".format(pkg),
                file=sys.stderr,
            )
            return False
    cmds = [
        ["apt-get", "update", "-yq",
         "-o", "APT::Update::Error-Mode=any"],
        # "--" stops apt from parsing any later argv as an option
        # belt-and-suspenders next to the whitelist above.
        ["apt-get", "install", "-yq", "--", *packages],
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


def restore_modprobe_baks_if_enabled():
    """
    When GPU isn't disabled, put back any modprobe .bak files left
    over from an earlier disable. Skips files the user already restored
    """
    if os.path.isfile(nvidia_disable_gpu_path):
        return

    move_conf_if_dest_absent(nvidia_modprobed_conf, nvidia_modprobe_conf)
    move_conf_if_dest_absent(nouveau_modprobed_conf, nouveau_modprobe_conf)


def install_nouveau():
    restore_modprobe_baks_if_enabled()

    nvidia_pkgs = _installed_nvidia_packages()

    cmds = []
    if nvidia_pkgs:
        cmds.append(["apt-get", "purge", "-yq", *nvidia_pkgs])
    cmds.append(["apt-get", "purge", "-yq", "xserver-xorg-video-nvidia"])
    cmds.append(["apt-get", "autoremove", "-yq"])
    cmds.append(["apt-get", "install", "-yq", nouveau])

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
            distro = cuda_repo_distro()
            if not ensure_keyring(distro):
                raise RuntimeError(
                    "missing signing key for {} repo".format(distro)
                )
            tmp = dest + ".tmp"
            with open(tmp, "w") as f:
                f.write(_nvidia_source_line(distro))
            os.replace(tmp, dest)

        rc = subprocess.call(
            ["apt-get", "update", "-yq",
             "-o", "APT::Update::Error-Mode=any"],
            env={**os.environ},
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
