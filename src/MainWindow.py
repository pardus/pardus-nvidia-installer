import gi
import os
import yaml

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject

nvidia_pci_id = "10de"
nvidia_devices_yaml_path = "/../data/nvidia-pci.yaml"


class PciDev:
    def __init__(self, vendor, device):
        self.vendor = vendor
        self.device = device

    def __str__(self):
        return f"{self.vendor:04x}:{self.device:04x}"


def fun_pci_dev_list():
    pci_dev_path = "/sys/bus/pci/devices/"
    for paths, dirs, files in os.walk(pci_dev_path):
        if dirs:
            for dir in dirs:
                with open(os.path.join(pci_dev_path, dir, "vendor")) as f:
                    vendor_id = int(f.read(), 16)
                with open(os.path.join(pci_dev_path, dir, "device")) as f:
                    device_id = int(f.read(), 16)
                if vendor_id == int(nvidia_pci_id, 16):
                    yield PciDev(vendor_id, device_id)


def parse_nvidia_devices(path):
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


def find_nvidia_device():
    pci_devices = fun_pci_dev_list()
    parsed_nvidia_devices = parse_nvidia_devices(nvidia_devices_yaml_path)
    nvidia_devices = []
    for pci in pci_devices:
        if parsed_nvidia_devices[pci.device] != None:
            nvidia_dev = parsed_nvidia_devices[pci.device]
            nvidia_dev["pci"] = str(pci)
            nvidia_devices.append(nvidia_dev)
    return nvidia_devices


def nvidia_driver_package(driver_name):
    drivers = {"current": "nvidia-driver", "470": "nvidia-tesla-470-driver"}
    return drivers[driver_name]


class MainWindow(object):
    def __init__(self, application):
        # Importing Glade file for MainWindow
        self.ui_interface_file = os.path.dirname(__file__) + "/../ui/ui.glade"
        try:
            self.gtk_builder = Gtk.Builder.new_from_file(self.ui_interface_file)
            self.gtk_builder.connect_signals(self)
        except GObject.GError:
            print("Error while creating user interface from glade file")
            return False

        self.ui_main_window = self.getUI("ui_main_window")
        self.ui_main_window.set_application(application)
        self.ui_main_window.set_title("Pardus Nvidia Installer")

        self.ui_gpu_brand_label = self.getUI("ui_gpu_brand_label")
        self.ui_gpu_model_label = self.getUI("ui_gpu_model_label")
        self.ui_gpu_pciid_label = self.getUI("ui_gpu_pciid_label")
        self.nvidia_device = find_nvidia_device()[0]

        if self.nvidia_device != None:
            self.ui_gpu_brand_label.set_label("Nvidia Corporation")
            self.ui_gpu_model_label.set_label(self.nvidia_device["name"])
            self.ui_gpu_pciid_label.set_label(self.nvidia_device["pci"])

    def getUI(self, object_name):
        return self.gtk_builder.get_object(object_name)
