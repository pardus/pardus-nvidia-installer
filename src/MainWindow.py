import gi
import os
import yaml
import subprocess

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject


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

        lspci_command = "lspci -nn | grep VGA"
        self.device_id = subprocess.getoutput(lspci_command).split(":")[-1][0:4].upper()
        print("device id : ", self.device_id)

        with open(os.path.dirname(__file__) + "/../data/nvidia-pci.yaml", "r") as f:
            self.nvidia_devices = list(yaml.safe_load_all(f))[0]["nvidia"]

        self.supported_driver = self.fun_find_driver()
        print(self.supported_driver)
        self.ui_gpu_brand_label.set_label("Nvidia Corporation")
        self.ui_gpu_model_label.set_label(self.supported_driver["name"])
        self.ui_gpu_pciid_label.set_label(str(self.supported_driver["pci"]))
        self.ui_main_window.show_all()

    def getUI(self, object_name):
        return self.gtk_builder.get_object(object_name)

    def fun_find_driver(self):
        supported_driver = {}
        for drivers in self.nvidia_devices:
            for driver in self.nvidia_devices[drivers]:
                pci = str(driver["pci"])
                if pci == self.device_id:
                    supported_driver = {"driver": drivers}
                    supported_driver.update(driver)
                    return supported_driver
