import os
import yaml

nvidia_pci_id = 0x10DE
nvidia_devices_yaml_path = "/../data/nvidia-pci.yaml"
drivers = {"current": "nvidia-driver", "470": "nvidia-tesla-470-driver"}


class PciDev:
    def __init__(self, vendor: int, device: int, cur_driver: str):
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
                    vendor_id = int(f.read(), 16)
                with open(os.path.join(pci_dev_path, dir, "device")) as f:
                    device_id = int(f.read(), 16)

                drv_mdl = os.path.join(pci_dev_path, dir, "driver", "module")

                try:
                    orig_path = os.readlink(drv_mdl)
                    cur_driver = os.path.basename(orig_path)
                except OSError as e:
                    cur_driver = "Driver Not Found"

                if vendor_id == nvidia_pci_id:
                    print(cur_driver)
                    yield PciDev(vendor_id, device_id, cur_driver)


def parse_devices(path: str):
    # path = "/../data/nvidia-pci.yaml"
    with open(os.path.dirname(__file__) + path, "r") as f:
        nvidia_devices = list(yaml.safe_load_all(f))[0]["nvidia"]

    pci_map = {}
    for drivers in nvidia_devices:
        for driver in nvidia_devices[drivers]:
            pci_map[int(str(driver["pci"]), 16)] = {
                "name": driver["name"],
                "driver": drivers,
            }
    return pci_map


def find_device():
    pci_devices = get_dev_list()
    parsed_nvidia_devices = parse_devices(nvidia_devices_yaml_path)
    for pci in pci_devices:
        if parsed_nvidia_devices[pci.device] != None:
            nvidia_dev = parsed_nvidia_devices[pci.device]
            nvidia_dev["pci"] = str(pci)
            nvidia_dev["cur_driver"] = pci.cur_driver
            return nvidia_dev
