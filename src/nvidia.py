import os
import apt
import json
import package
import subprocess

nvidia_pci_id = "10DE"
nvidia_devices_yaml_path = "/../data/nvidia-pci.yaml"
nvidia_devices_json_path = "/../data/nvidia-pci.json"
drivers = {"current": "nvidia-driver", "470": "nvidia-tesla-470-driver"}
nouveau = "xserver-xorg-video-nouveau"


class PciDev:
    def __init__(self, vendor: str, device: str, cur_driver: str):
        self.vendor = vendor
        self.device = device
        self.cur_driver = cur_driver

    def __str__(self):
        return f"{self.vendor:04x}:{self.device:04x}"


def get_dev_list():
    pci_dev_path = "/sys/bus/pci/devices/"
    for paths, dirs, files in os.walk(pci_dev_path):
        if dirs:
            for dir in dirs:
                with open(os.path.join(pci_dev_path, dir, "vendor")) as f:
                    vendor_id = f.read().strip()[2:].upper()
                with open(os.path.join(pci_dev_path, dir, "device")) as f:
                    device_id = f.read().strip()[2:].upper()

                drv_mdl = os.path.join(pci_dev_path, dir, "driver", "module")

                try:
                    orig_path = os.readlink(drv_mdl)
                    cur_driver = os.path.basename(orig_path)
                except OSError as e:
                    cur_driver = "Driver Not Found"
                if vendor_id == nvidia_pci_id:
                    yield PciDev(vendor_id, device_id, cur_driver)


def is_drv_installed(driver):
    cache = apt.Cache()
    return cache[driver].is_installed
    cmd = "/sbin/modinfo nvidia-current --field=version"
    return subprocess.getoutput(cmd)


def find_device():
    pci_devices = get_dev_list()
    parsed_nvidia_drivers = json.loads(
        open(os.path.dirname(__file__) + nvidia_devices_json_path, "r").read()
    )
    nvidia_devices = [{"driver": "xserver-xorg-video-nouveau", "drv_in_use": False}]
    for index, pci in enumerate(pci_devices):
        for driver in parsed_nvidia_drivers:
            if pci.device in parsed_nvidia_drivers[driver].keys():
                data = {
                    "pci": pci.device,
                    "device": parsed_nvidia_drivers[driver][pci.device],
                    "cur_driver": pci.cur_driver,
                }
                if index == 0:
                    nvidia_devices[0]["pci"] = pci.device
                    nvidia_devices[0]["device"] = parsed_nvidia_drivers[driver][
                        pci.device
                    ]
                    nvidia_devices[0]["cur_driver"] = pci.cur_driver

                data["driver"] = driver

                cur_drv_info = package.get_pkg_info(driver)
                data["drv_in_use"] = is_drv_installed(driver)
                print(data)

                nvidia_devices.append(data)

    return nvidia_devices
