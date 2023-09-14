import gi
import os
import apt
import yaml

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject, GLib

cache = apt.Cache()


nvidia_pci_id = 0x10DE
nvidia_devices_yaml_path = "/../data/nvidia-pci.yaml"
drivers = {"current": "nvidia-driver", "470": "nvidia-tesla-470-driver"}


class PciDev:
    def __init__(self, vendor: int, device: int):
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
                if vendor_id == nvidia_pci_id:
                    yield PciDev(vendor_id, device_id)


def parse_nvidia_devices(path: str):
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
    for pci in pci_devices:
        if parsed_nvidia_devices[pci.device] != None:
            nvidia_dev = parsed_nvidia_devices[pci.device]
            nvidia_dev["pci"] = str(pci)
            return nvidia_dev


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

        self.ui_gpu_box = self.getUI("ui_gpu_box")
        self.ui_main_window = self.getUI("ui_main_window")

        self.ui_os_drv_lbl = self.getUI("ui_opensource_driver_label")
        self.ui_os_drv_n_lbl = self.getUI("ui_opensource_driver_name_label")
        self.ui_os_drv_rb = self.getUI("ui_opensource_driver_radio_button")
        self.ui_os_drv_v_lbl = self.getUI("ui_opensource_driver_version_label")

        self.ui_nv_drv_lbl = self.getUI("ui_proprietary_driver_label")
        self.ui_nv_drv_n_lbl = self.getUI("ui_proprietary_driver_name_label")
        self.ui_nv_drv_rb = self.getUI("ui_proprietary_driver_radio_button")
        self.ui_nv_drv_v_lbl = self.getUI("ui_proprietary_driver_version_label")

        self.ui_main_window.set_application(application)
        self.ui_main_window.set_title("Pardus Nvidia Installer")

        self.nvidia_device = find_nvidia_device()
        print(self.nvidia_device)

        if self.nvidia_device != None:
            name = self.nvidia_device["name"]
            pci = self.nvidia_device["pci"]
            dev_info_box = self.fun_create_gpu_box(name, pci)
            self.ui_gpu_box.pack_start(dev_info_box, True, True, 5)
        self.ui_gpu_box.show_all()

        self.os_drv_pkg = "xserver-xorg-video-nouveau"
        self.pkg_os_info = self.fun_check_apt_pkg(self.os_drv_pkg)
        self.pkg_nv_info = self.fun_check_apt_pkg(drivers[self.nvidia_device["driver"]])

        markup = self.fun_make_label_markup("Name: ", self.pkg_os_info["name"])
        self.ui_os_drv_n_lbl.set_markup(markup)

        markup = self.fun_make_label_markup("Version: ", self.pkg_os_info["ver"])
        self.ui_os_drv_v_lbl.set_markup(markup)

        markup = self.fun_make_label_markup("Name: ", self.pkg_nv_info["name"])
        self.ui_nv_drv_n_lbl.set_markup(markup)

        markup = self.fun_make_label_markup("Version: ", self.pkg_nv_info["ver"])
        self.ui_nv_drv_v_lbl.set_markup(markup)

        print(self.pkg_nv_info)
        print(self.pkg_os_info)

    def getUI(self, object_name: str):
        return self.gtk_builder.get_object(object_name)

    def fun_check_apt_pkg(self, package_name: str):
        pkg = cache[package_name]
        if pkg.is_installed:
            version = pkg.installed.version
            name = pkg.installed.raw_description
        else:
            version = pkg.versions[0].version
            name = pkg.versions[0].raw_description

        return {"ver": version, "name": name}

    def fun_create_gpu_box(self, name: str, pci: str):
        box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 13)
        vendor_markup = self.fun_make_label_markup(
            "Device Vendor: ", "Nvidia Corporation"
        )  # (f"<span> <b>Device Vendor: </b> <span>Nvidia Corporation</span> </span>")
        name_markup = self.fun_make_label_markup("Device Model: ", name)
        # f"<span> <b>Device Model: </b> <span>{name}</span> </span>"
        pci_markup = self.fun_make_label_markup("PCI: ", pci)
        # f"<span> <b>PCI: </b> <span>{pci}</span> </span>"
        vendor_label = Gtk.Label(xalign=0)
        vendor_label.set_markup(vendor_markup)

        name_label = Gtk.Label(xalign=0)
        name_label.set_markup(name_markup)

        pci_label = Gtk.Label(xalign=0)
        pci_label.set_markup(pci_markup)

        box.pack_start(vendor_label, True, True, 0)
        box.pack_start(name_label, True, True, 0)
        box.pack_start(pci_label, True, True, 0)
        return box

    def fun_make_label_markup(self, label: str, desc: str):
        return f"<span> <b>{label}: </b> <span>{desc}</span> </span>"
