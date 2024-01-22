import os
import apt
import json

nvidia_pci_id = "10DE"
nvidia_pci_id_int = 0x10DE
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

class NvidiaDevice:
    def __init__(self,vendor_id:int=None,vendor_name:str=None,
                 device_id:str=None,device_name:str=None,
                 driver_name:str=None,driver_version:str=None):
        self.vendor_id = vendor_id
        self.vendor_name = vendor_name

        self.device_id = device_id
        self.device_name = device_name

        self.driver_name = driver_name
        self.driver_version = driver_version
    

def get_pci_ids():
    with open("/usr/share/misc/pci.ids","r") as f:
        pci_ids = f.readlines()
    devices = {}
    cur_vendor = None
    for line in pci_ids:
        if line.startswith("#") or line.strip() == "":
            continue
        if not line.startswith("\t"):
            vendor_id, vendor_name = line.strip().split(" ",1)
            vendor_id = int(vendor_id,16)
            devices[vendor_id] = {
                "vendor_id" : vendor_id,
                "vendor_name" : vendor_name.strip(),
                "devices":{},
            }
            cur_vendor = vendor_id
        else:
            device_id,device_name = line.strip().split(" ",1)
            device_id = int(device_id,16)
            devices[cur_vendor]["devices"][device_id] = device_name.strip()
    return devices

def graphics():
    pci_dev_path = "/sys/bus/pci/devices/"
    pci_ids = get_pci_ids()
    for paths, dirs, files in os.walk(pci_dev_path):
        if dirs:
            for dir in dirs:
                vp = os.path.join(pci_dev_path,dir,"vendor")
                vc = readfile(vp)
                vc = int(vc,16)
                vn = pci_ids[vc]['vendor_name']

                if vc == nvidia_pci_id_int:
                    dp = os.path.join(pci_dev_path,dir,"device")
                    dc = readfile(dp)
                    dc = int(dc,16)
                    dn = pci_ids[vc]["devices"][dc]
                    
                    
                    drv_p = os.path.join(pci_dev_path,dir,"driver","module")
                    orig_drv_p = os.readlink(drv_p)
                    drv_c = os.path.basename(orig_drv_p)
                    drv_ver_p = os.path.join(drv_p,"version")
                    drv_ver_c = readfile(drv_ver_p)
                    yield NvidiaDevice(vc,vn,dc,dn,drv_c,drv_ver_c)

                
def readfile(filepath:str=None):
    content = None
    if os.path.isfile(filepath):
        with open(filepath,"r") as f:
            content = f.read().strip()
    return content

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
                    nvidia_devices[0]["cur_driver"] = nouveau

                if pci.cur_driver == "nouveau":
                    data["cur_driver"] = nouveau
                    data["drv_in_use"] = True
                else:
                    if is_drv_installed(driver):
                        cache = apt.Cache()
                        ap = cache[driver].versions
                        data["cur_driver_ver"] = ap[0]
                        nvidia_devices[0]["cur_driver"] = driver
                        data["cur_driver"] = driver
                        data["drv_in_use"] = True
                    else:
                        data["cur_driver"] = "Not Found"

                data["driver"] = driver

                data["drv_in_use"] = is_drv_installed(driver)
                nvidia_devices.append(data)
    print(nvidia_devices)
    return nvidia_devices
