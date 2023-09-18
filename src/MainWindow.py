import gi
import os
import apt
import yaml
import nvidia
import package
import subprocess

gi.require_version("Gtk", "3.0")
gi.require_version("Polkit", "1.0")
from states import pkg_ins_progress, PackageProgressState
from gi.repository import Gtk, GObject, Polkit, GLib


cache = apt.Cache()
act_id = "tr.org.pardus.pkexec.pardus-nvidia-installer"

drivers = {"current": "nvidia-driver", "470": "nvidia-tesla-470-driver"}


class MainWindow(object):
    def __init__(self, application):
        pkg_ins_progress = PackageProgressState()
        pkg_ins_progress.add_observer(self.on_progress_state_changed)

        self.ui_interface_file = os.path.dirname(__file__) + "/../ui/ui.glade"
        try:
            self.gtk_builder = Gtk.Builder.new_from_file(self.ui_interface_file)
            self.gtk_builder.connect_signals(self)
        except GObject.GError:
            print("Error while creating user interface from glade file")
            return False

        self.ui_gpu_box = self.getUI("ui_gpu_box")
        self.ui_main_window = self.getUI("ui_main_window")
        self.ui_cur_sel_drv_lbl = self.getUI("ui_cur_selected_drv_label")

        self.ui_os_drv_lbl = self.getUI("ui_opensource_driver_label")
        self.ui_os_drv_n_lbl = self.getUI("ui_opensource_driver_name_label")
        self.ui_os_drv_rb = self.getUI("ui_opensource_driver_radio_button")
        self.ui_os_drv_v_lbl = self.getUI("ui_opensource_driver_version_label")

        self.ui_nv_drv_lbl = self.getUI("ui_proprietary_driver_label")
        self.ui_nv_drv_n_lbl = self.getUI("ui_proprietary_driver_name_label")
        self.ui_nv_drv_rb = self.getUI("ui_proprietary_driver_radio_button")
        self.ui_nv_drv_v_lbl = self.getUI("ui_proprietary_driver_version_label")

        self.ui_apply_btn = self.getUI("ui_apply_chg_button")
        self.ui_cancel_btn = self.getUI("ui_cancel_button")
        self.lock_btn = self.getUI("lock_btn")
        self.ui_status_label = self.getUI("ui_status_label")

        self.root_permission = None
        if Polkit:
            try:
                self.root_permission = Polkit.Permission.new_sync(act_id, None, None)
            except GLib.GError:
                pass

        if self.root_permission is not None:
            self.root_permission.connect(
                "notify::allowed", self.on_root_permission_changed
            )

        self.lock_btn.connect("notify::permission", self.on_root_permission_changed)
        prem = Polkit.Permission.new_sync(act_id, None, None)
        self.lock_btn.set_permission(prem)

        self.ui_os_drv_rb.connect("toggled", self.on_drv_toggled, "nouveau")
        self.ui_nv_drv_rb.connect(
            "toggled", self.on_drv_toggled, "Nvidia Proprietary Driver"
        )

        self.ui_main_window.set_application(application)
        self.ui_main_window.set_title("Pardus Nvidia Installer")

        self.nvidia_device = nvidia.find_device()
        print("nvidia device = ", self.nvidia_device)

        if self.nvidia_device != None:
            name = self.nvidia_device["name"]
            pci = self.nvidia_device["pci"]
            cur_drv = self.nvidia_device["cur_driver"]
            dev_info_box = self.fun_create_gpu_box(name, pci, cur_drv)
            self.ui_gpu_box.pack_start(dev_info_box, True, True, 5)
        self.ui_gpu_box.show_all()

        self.os_drv_pkg = "xserver-xorg-video-nouveau"
        self.pkg_os_info = package.get_pkg_info(self.os_drv_pkg)
        self.pkg_nv_info = package.get_pkg_info(drivers[self.nvidia_device["driver"]])

        markup = self.fun_make_label_markup(
            "Selected Driver", self.nvidia_device["cur_driver"] + " (Currently In Use) "
        )
        self.ui_cur_sel_drv_lbl.set_markup(markup)

        markup = self.fun_make_label_markup("Name", self.pkg_os_info["name"])
        self.ui_os_drv_n_lbl.set_markup(markup)

        markup = self.fun_make_label_markup("Version", self.pkg_os_info["ver"])
        self.ui_os_drv_v_lbl.set_markup(markup)

        markup = self.fun_make_label_markup(
            "Description", "Open Source Driver", color="mediumspringgreen"
        )
        self.ui_os_drv_lbl.set_markup(markup)

        markup = self.fun_make_label_markup("Name", self.pkg_nv_info["name"])
        self.ui_nv_drv_n_lbl.set_markup(markup)

        markup = self.fun_make_label_markup("Version", self.pkg_nv_info["ver"])
        self.ui_nv_drv_v_lbl.set_markup(markup)

        markup = self.fun_make_label_markup(
            "Description", "Proprietary Driver", color="dodgerblue"
        )

        self.ui_nv_drv_lbl.set_markup(markup)

    def getUI(self, object_name: str):
        return self.gtk_builder.get_object(object_name)

    def fun_create_gpu_box(self, name: str, pci: str, cur_drv: str):
        box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 13)
        vendor_markup = self.fun_make_label_markup(
            "Device Vendor", "Nvidia Corporation"
        )
        name_markup = self.fun_make_label_markup("Device Model", name)
        pci_markup = self.fun_make_label_markup("PCI", pci)
        drv_markup = self.fun_make_label_markup("Current Driver In Use", cur_drv)

        vendor_label = Gtk.Label(xalign=0)
        vendor_label.set_markup(vendor_markup)

        name_label = Gtk.Label(xalign=0)
        name_label.set_markup(name_markup)

        pci_label = Gtk.Label(xalign=0)
        pci_label.set_markup(pci_markup)

        driver_label = Gtk.Label(xalign=0)
        driver_label.set_markup(drv_markup)

        box.pack_start(vendor_label, True, True, 0)
        box.pack_start(name_label, True, True, 0)
        box.pack_start(pci_label, True, True, 0)
        box.pack_start(driver_label, True, True, 0)
        return box

    def fun_make_label_markup(self, label: str, desc: str, color: str = None):
        if color:
            return f'<span> <b>{label}: </b> <span foreground="{color}">{desc}</span> </span>'
        else:
            return f"<span> <b>{label}: </b> <span>{desc}</span> </span>"

    def on_drv_toggled(self, radio_button: Gtk.RadioButton, name: str):
        if radio_button.get_active():
            markup_desc = name
            drv_in_use = self.fun_is_driver_in_use(name)
            self.ui_apply_btn.set_sensitive(not drv_in_use)
            if drv_in_use:
                markup_desc = name + " (Currently In Use) "
            markup = self.fun_make_label_markup("Selected Driver", markup_desc)
            self.ui_cur_sel_drv_lbl.set_markup(markup)
            print(self.fun_is_driver_in_use(name))

    def fun_is_driver_in_use(self, driver: str):
        return self.nvidia_device["cur_driver"] == driver

    def on_progress_state_changed(value):
        lbl_txt = f"xx Installing: %{value}"
        print(lbl_txt)
        # self.ui_status_label.set_label(lbl_txt)

    def on_root_permission_changed(self, permission, blank):
        permission = self.lock_btn.get_permission()
        try:
            if permission:
                allowed = permission.get_allowed()
                if allowed:
                    cur_path = os.path.dirname(__file__)
                    pkg_file = "/package.py"

                    def pkexec_cb(src, cdn):
                        print("callback pkexec")

                    pid, _, _, _ = GLib.spawn_async(
                        [
                            "/usr/bin/pkexec",
                            cur_path + pkg_file,
                            "install",
                            "htop",
                        ],
                        flags=GLib.SPAWN_SEARCH_PATH
                        | GLib.SPAWN_LEAVE_DESCRIPTORS_OPEN
                        | GLib.SPAWN_DO_NOT_REAP_CHILD,
                    )

                    GLib.child_watch_add(GLib.PRIORITY_DEFAULT, pid, pkexec_cb)
        except GLib.GError:
            print("now allowed")
