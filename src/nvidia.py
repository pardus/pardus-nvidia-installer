import os
from os.path import isfile
import apt
import json
import shutil
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
nvidia_disable_gpu_path = "/var/cache/pardus-nvidia-installer-disable-gpu"
nvidia_devices_yaml_path = "/../data/nvidia-pci.yaml"
nvidia_devices_json_path = "/../data/nvidia-pci.json"
drivers = {"current": "nvidia-driver", "470": "nvidia-tesla-470-driver"}
nouveau = "xserver-xorg-video-nouveau"

dest = "/etc/apt/sources.list.d/nvidia-drivers.list"
src_list = os.path.dirname(os.path.abspath(__file__) + "../nvidia-drivers.list")
cache = apt.Cache()


class NvidiaDriver:
    def __init__(self, package, version, type, repo, installed=False):
        self.package = package
        self.version = version
        self.type = type
        self.repo = repo
        self.installed = installed

    def __str__(self) -> str:
        return f"package:{self.package}, version:{self.version}, type:{self.type}, repo:{self.repo}, installed:{self.installed}"


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


def toggle_source_list():
    src_state = source()
    if src_state:
        os.remove(dest)
    else:
        shutil.copyfile(src_list, dest)


def get_pci_ids():
    with open("/usr/share/misc/pci.ids", "r") as f:
        pci_ids = f.readlines()
    devices = {}
    cur_vendor = None
    for line in pci_ids:
        if line.startswith("#") or line.strip() == "":
            continue
        if not line.startswith("\t"):
            vendor_id, vendor_name = line.strip().split(" ", 1)
            vendor_id = int(vendor_id, 16)
            devices[vendor_id] = {
                "vendor_id": vendor_id,
                "vendor_name": vendor_name.strip(),
                "devices": {},
            }
            cur_vendor = vendor_id
        else:
            device_id, device_name = line.strip().split(" ", 1)
            device_id = int(device_id, 16)
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
                vc = readfile(vp)
                vc = int(vc, 16)
                vn = pci_ids[vc]["vendor_name"]
                sp = os.path.join(pci_dev_path, dir, "class")
                sc = readfile(sp)
                st = False
                if vc == nvidia_pci_id_int and sc == "0x030000" or sc == "0x030200":
                    if sc == "0x030200" or sc == "0x030000":
                        st = True
                    dp = os.path.join(pci_dev_path, dir, "device")
                    dc = readfile(dp)
                    dc = int(dc, 16)
                    dn = pci_ids[vc]["devices"][dc]

                    drv_c = None
                    drv_ver_c = None

                    drv_p = os.path.join(pci_dev_path, dir, "driver", "module")
                    if os.path.isfile(drv_p):
                        orig_drv_p = os.readlink(drv_p)
                        drv_c = os.path.basename(orig_drv_p)
                        drv_ver_p = os.path.join(drv_p, "version")
                        drv_ver_c = readfile(drv_ver_p)
                    devices.append(NvidiaDevice(vc, vn, dc, dn, drv_c, drv_ver_c, st))

    return devices


def get_package_info(package_name):
    cache = apt.Cache()
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
    print(ver_list)
    return ver_list


def readfile(filepath):
    content = None
    if os.path.isfile(filepath):
        with open(filepath, "r") as f:
            content = f.read().strip()
    return content


def is_pkg_installed(driver, version=None):
    cache = apt.Cache()
    if version:
        return version in str(cache[driver].installed)
    else:
        return cache[driver].is_installed


def drivers():
    drivers = []
    gpus = graphics()
    if len(gpus) < 1:
        return drivers
    with open(os.path.dirname(__file__) + nvidia_devices_json_path, "r") as f:
        parsed_nvidia_drivers = json.loads(f.read())
    drivers.append(
        NvidiaDriver(
            nouveau,
            get_pkg_ver(nouveau),
            _("Open Source Driver"),
            get_package_origin(nouveau, get_pkg_ver(nouveau)),
            is_pkg_installed(nouveau, get_pkg_ver(nouveau)),
        ),
    )
    cache = apt.Cache()

    for gpu in gpus:
        for driver in parsed_nvidia_drivers:
            if gpu.device_id_str in parsed_nvidia_drivers[driver].keys():
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
    cache = apt.Cache()
    pkg = cache[package_name]
    vers = pkg.versions
    if package_version and package_version in str(vers):
        for ver in vers:

            if package_version in str(ver):
                for orig in ver.origins:
                    if orig.origin:
                        return orig.origin
    else:
        pass
        print(vers[0].origins[0].origin)


def newest_pkg_ver(pkg):
    cache = apt.Cache()
    return cache[pkg].versions[0].version


def int2hex(num):
    return str(hex(num)[2:]).upper()


def get_pkg_ver(pkg):
    cache = apt.Cache()
    if is_pkg_installed(pkg):
        installed_version = str(cache[pkg].installed)
        if pkg in installed_version:
            return installed_version.split(f"{pkg}=")[1]
        return installed_version

    else:
        return str(cache[pkg].versions[0].version)
