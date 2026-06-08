import os
import apt
import json
import locale
import apt_pkg
from locale import gettext as _

apt_pkg.init_system()
APPNAME_CODE = "pardus-nvidia-installer"
TRANSLATION_PATH = "/usr/share/locale"
locale.bindtextdomain(APPNAME_CODE, TRANSLATION_PATH)
locale.textdomain(APPNAME_CODE)
nvidia_pci_id = "10DE"
nvidia_pci_id_int = 0x10DE
nvidia_devices_yaml_path = "/../data/nvidia-pci.yaml"
nvidia_devices_json_path = "/../data/nvidia-pci.json"
nouveau = "xserver-xorg-video-nouveau"

dest = "/etc/apt/sources.list.d/nvidia-drivers.list"

_cache_instance = None


def _cache():
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = apt.Cache()
    return _cache_instance


def reopen_cache():
    global _cache_instance
    _cache_instance = apt.Cache()


class NvidiaDriver:
    def __init__(self, package, version, type, repo, installed=False):
        self.package = package
        self.version = version
        self.type = type
        self.repo = repo
        self.installed = installed

    def __str__(self) -> str:
        return f"package:{self.package}, version:{self.version}, type:{self.type}, repo:{self.repo}, installed:{self.installed}"

    def __eq__(self, other):
        if not isinstance(other, NvidiaDriver):
            return NotImplemented
        return (self.package, self.version, self.repo) == (
            other.package, other.version, other.repo
        )

    def __hash__(self):
        return hash((self.package, self.version, self.repo))


class NvidiaDevice:
    def __init__(
        self,
        vendor_id: int = None,
        vendor_name: str = None,
        device_id: int = None,
        device_name: str = None,
        driver_name: str = None,
        driver_version: str = None,
        is_secondary_gpu: bool = True,
    ):
        self.vendor_id = vendor_id
        self.vendor_name = vendor_name
        self.vendor_id_str = int2hex(self.vendor_id)

        self.device_id = device_id
        self.device_name = device_name
        self.device_id_str = int2hex(self.device_id)

        self.driver_name = driver_name
        self.driver_version = driver_version
        self.is_secondary_gpu = is_secondary_gpu


def source():
    return os.path.isfile(dest)


def get_pci_ids():
    pci_ids_path = "/usr/share/misc/pci.ids"
    if not os.path.isfile(pci_ids_path):
        return {}
    with open(pci_ids_path, "r") as f:
        pci_ids = f.readlines()
    devices = {}
    cur_vendor = None
    for line in pci_ids:
        if line.startswith("#") or line.strip() == "":
            continue
        if not line.startswith("\t"):
            try:
                vendor_id, vendor_name = line.strip().split(" ", 1)
                vendor_id = int(vendor_id, 16)
            except ValueError:
                cur_vendor = None
                continue
            devices[vendor_id] = {
                "vendor_id": vendor_id,
                "vendor_name": vendor_name.strip(),
                "devices": {},
            }
            cur_vendor = vendor_id
        else:
            if cur_vendor is None:
                continue
            try:
                device_id, device_name = line.strip().split(" ", 1)
                device_id = int(device_id, 16)
            except ValueError:
                continue
            devices[cur_vendor]["devices"][device_id] = device_name.strip()
    return devices


def graphics():
    pci_dev_path = "/sys/bus/pci/devices/"
    pci_ids = get_pci_ids()
    devices = []
    for paths, dirs, files in os.walk(pci_dev_path):
        if dirs:
            for dir in dirs:
                vp = os.path.join(pci_dev_path, dir, "vendor")
                vc_raw = readfile(vp)
                if vc_raw is None:
                    continue
                try:
                    vc = int(vc_raw, 16)
                except (TypeError, ValueError):
                    continue
                if vc != nvidia_pci_id_int:
                    continue

                sp = os.path.join(pci_dev_path, dir, "class")
                sc = readfile(sp)

                if sc is None or not sc.startswith("0x03"):
                    continue
                # Secondary boot_vga is "1" only on the primary
                # and absent on 3D controllers
                bv = readfile(os.path.join(pci_dev_path, dir, "boot_vga"))
                st = (bv != "1")

                dp = os.path.join(pci_dev_path, dir, "device")
                dc_raw = readfile(dp)
                if dc_raw is None:
                    continue
                try:
                    dc = int(dc_raw, 16)
                except (TypeError, ValueError):
                    continue

                vendor_entry = pci_ids.get(vc, {})
                vn = vendor_entry.get("vendor_name", "NVIDIA")
                dn = vendor_entry.get("devices", {}).get(
                    dc, f"NVIDIA Device {dc:04X}"
                )

                drv_c = None
                drv_ver_c = None

                drv_p = os.path.join(pci_dev_path, dir, "driver", "module")
                if os.path.islink(drv_p):
                    orig_drv_p = os.readlink(drv_p)
                    drv_c = os.path.basename(orig_drv_p)
                    drv_ver_p = os.path.join(drv_p, "version")
                    drv_ver_c = readfile(drv_ver_p)
                devices.append(NvidiaDevice(vc, vn, dc, dn, drv_c, drv_ver_c, st))

    return devices


def get_package_info(package_name):
    cache = _cache()
    if package_name not in cache:
        return {}
    package = cache[package_name]
    versions = package.versions
    ver_list = {}
    for version in versions:
        origins = version.origins
        for orig in origins:
            if orig.origin not in ver_list.keys() and len(orig.origin) > 1:
                ver_list[orig.origin] = version.version
            else:
                if orig.origin in ver_list.keys():
                    result = apt_pkg.version_compare(
                        ver_list[orig.origin], version.version
                    )
                    if result < 0:
                        ver_list[orig.origin] = version.version
    return ver_list


def readfile(filepath):
    content = None
    if os.path.isfile(filepath):
        with open(filepath, "r") as f:
            content = f.read().strip()
    return content


def is_pkg_installed(driver, version=None):
    cache = _cache()
    if driver not in cache:
        return False
    installed = cache[driver].installed
    if installed is None:
        return False
    if version is None:
        return True
    return installed.version == version


def drivers(gpus=None):
    drivers = []
    if gpus is None:
        gpus = graphics()
    if len(gpus) < 1:
        return drivers
    with open(os.path.dirname(__file__) + nvidia_devices_json_path, "r") as f:
        parsed_nvidia_drivers = json.loads(f.read())
    nouveau_ver = get_pkg_ver(nouveau)
    drivers.append(
        NvidiaDriver(
            nouveau,
            nouveau_ver,
            _("Open Source Driver"),
            get_package_origin(nouveau, nouveau_ver),
            is_pkg_installed(nouveau, nouveau_ver),
        ),
    )

    for driver in parsed_nvidia_drivers:
        if any(gpu.device_id_str in parsed_nvidia_drivers[driver]
               for gpu in gpus):
            driver_lists = get_package_info(driver)
            for origin in driver_lists:
                version = driver_lists[origin]
                drivers.append(
                    NvidiaDriver(
                        driver,
                        version,
                        _("Proprietary Driver"),
                        origin,
                        is_pkg_installed(driver, version),
                    )
                )

    return drivers


def get_package_origin(package_name, package_version=None):
    if not package_version:
        return None
    pkg = _cache()[package_name]
    for ver in pkg.versions:
        if ver.version != package_version:
            continue
        for orig in ver.origins:
            if orig.origin:
                return orig.origin
    return None


def newest_pkg_ver(pkg):
    return _cache()[pkg].versions[0].version


def int2hex(num):
    if num is None:
        return None
    return f"{num:04X}"


def get_pkg_ver(pkg):
    pkg_obj = _cache()[pkg]
    installed = pkg_obj.installed
    if installed is not None:
        return installed.version
    return pkg_obj.versions[0].version
