import gi
import os

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
        self.ui_gpu_memory_label = self.getUI("ui_gpu_memory_label")
        self.ui_gpu_bandwith_label = self.getUI("ui_gpu_bandwith_label")
        self.ui_gpu_busid_label = self.getUI("ui_gpu_busid_label")
        self.ui_gpu_pciid_label = self.getUI("ui_gpu_pciid_label")

        self.ui_main_window.show_all()

    def getUI(self, object_name):
        return self.gtk_builder.get_object(object_name)
