import gi
import os
import apt

import yaml
import nvidia
import package
import subprocess
import socket
import std_opr

gi.require_version("Gtk", "3.0")
gi.require_version("Polkit", "1.0")


from gi.repository import Gtk, GObject, Polkit, GLib


cache = apt.Cache()
act_id = "tr.org.pardus.pkexec.pardus-nvidia-installer"
socket_path = "/tmp/pardus-nvidia-installer"
drivers = {
        "current": "nvidia-driver", 
        470: "nvidia-tesla-470-driver"
}
pkg_opr = {"purge": ""}


class MainWindow(object):
    def __init__(self, application):
        self.ui_interface_file = os.path.dirname(__file__) + "/../ui/ui.glade"
        try:
            self.gtk_builder = Gtk.Builder.new_from_file(self.ui_interface_file)
            self.gtk_builder.connect_signals(self)
        except GObject.GError:
            print("Error while creating user interface from glade file")
            return False

        self.ui_gpu_box = self.get_ui("ui_gpu_box")
        self.ui_drv_box = self.get_ui("ui_drv_box")
        self.ui_main_box = self.get_ui("ui_main_box")
        self.ui_main_window = self.get_ui("ui_main_window")
        self.ui_cur_sel_drv_lbl = self.get_ui("ui_cur_selected_drv_label")
        self.ui_confirm_dialog = self.get_ui("ui_confirm_dialog")

        self.ui_os_drv_lbl = self.get_ui("ui_opensource_driver_label")
        self.ui_os_drv_n_lbl = self.get_ui("ui_opensource_driver_name_label")
        self.ui_os_drv_rb = self.get_ui("ui_opensource_driver_radio_button")
        self.ui_os_drv_v_lbl = self.get_ui("ui_opensource_driver_version_label")

        self.ui_nv_drv_lbl = self.get_ui("ui_proprietary_driver_label")
        self.ui_nv_drv_n_lbl = self.get_ui("ui_proprietary_driver_name_label")
        self.ui_nv_drv_rb = self.get_ui("ui_proprietary_driver_radio_button")
        self.ui_nv_drv_v_lbl = self.get_ui("ui_proprietary_driver_version_label")

        self.ui_apply_chg_button = self.get_ui("ui_apply_chg_button")
        self.ui_status_label = self.get_ui("ui_status_label")
        self.ui_status_progressbar = self.get_ui("ui_status_progressbar")

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

        self.ui_apply_chg_button.connect(
            "notify::permission", self.on_root_permission_changed
        )
        prem = Polkit.Permission.new_sync(act_id, None, None)
        self.ui_apply_chg_button.set_permission(prem)

        self.ui_os_drv_rb.connect("toggled", self.on_drv_toggled, "nouveau")
        self.ui_nv_drv_rb.connect("toggled", self.on_drv_toggled, "nvidia")

        self.ui_main_window.set_application(application)
        self.ui_main_window.set_title("Pardus Nvidia Installer")

        self.nvidia_device = nvidia.find_device()
        self.toggled_driver = self.nvidia_device["cur_driver"]
        if self.toggled_driver == "nvidia":
            self.ui_nv_drv_rb.set_active(True)
        self.chg_drv_lbl_in_use()

        if self.nvidia_device and self.nvidia_device["driver"] in drivers.keys():
            self.pkg_nv_info = package.get_pkg_info(
                drivers[self.nvidia_device["driver"]]
            )

            name = self.nvidia_device["name"]
            pci = self.nvidia_device["pci"]
            cur_drv = self.nvidia_device["cur_driver"]
            dev_info_box = self.gpu_box(name, pci, cur_drv)
            self.ui_gpu_box.pack_start(dev_info_box, True, True, 5)
            self.os_drv_pkg = "xserver-xorg-video-nouveau"
            self.pkg_os_info = package.get_pkg_info(self.os_drv_pkg)

            markup = self.lbl_markup("Name", self.pkg_os_info["name"])
            self.ui_os_drv_n_lbl.set_markup(markup)

            markup = self.lbl_markup("Version", self.pkg_os_info["ver"])
            self.ui_os_drv_v_lbl.set_markup(markup)

            markup = self.lbl_markup(
                "Description", "Open Source Driver", color="mediumspringgreen"
            )
            self.ui_os_drv_lbl.set_markup(markup)
            markup = self.lbl_markup("Name", self.pkg_nv_info["name"])
            self.ui_nv_drv_n_lbl.set_markup(markup)

            markup = self.lbl_markup("Version", self.pkg_nv_info["ver"])
            self.ui_nv_drv_v_lbl.set_markup(markup)

            markup = self.lbl_markup(
                "Description", "Proprietary Driver", color="dodgerblue"
            )
            self.ui_nv_drv_lbl.set_markup(markup)
        elif self.nvidia_device["driver"] not in drivers.keys():
            self.ui_main_box.remove(self.ui_drv_box)
            lbl = f"Your GPU: {self.nvidia_device['name']} support only support version {self.nvidia_device['driver']}. But this package is not in our repositories."
            label = Gtk.Label(label=lbl)
            self.ui_gpu_box.pack_start(label, True, True, 5)
        else:
            self.ui_main_box.remove(self.ui_drv_box)
            label = Gtk.Label(
                label="There is no compatible device in system.", xalign=0
            )
            self.ui_gpu_box.pack_start(label, True, True, 5)
        self.ui_gpu_box.show_all()

    def get_ui(self, object_name: str):
        return self.gtk_builder.get_object(object_name)

    def gpu_box(self, name: str, pci: str, cur_drv: str):
        box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 13)
        vendor_markup = self.lbl_markup("Device Vendor", "Nvidia")
        name_markup = self.lbl_markup("Device Model", name)
        pci_markup = self.lbl_markup("PCI", pci)
        drv_markup = self.lbl_markup("Current Driver In Use", cur_drv)

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

    def lbl_markup(self, label: str, desc: str, color: str = None):
        if color:
            return f'<span> <b>{label}: </b> <span foreground="{color}">{desc}</span> </span>'
        else:
            return f"<span> <b>{label}: </b> <span>{desc}</span> </span>"

    def on_drv_toggled(self, radio_button: Gtk.RadioButton, name: str):
        markup_desc = name
        drv_in_use = self.is_drv_in_use(name)

        if drv_in_use:
            markup_desc = name + " (Currently In Use) "

        if radio_button.get_active():
            self.ui_apply_chg_button.set_sensitive(not drv_in_use)
            self.ui_cur_sel_drv_lbl.set_markup(markup_desc)
            self.toggled_driver = name
            self.chg_drv_lbl_in_use()

    def is_drv_in_use(self, driver: str):
        return self.nvidia_device["cur_driver"] == driver

    def chg_drv_lbl_in_use(self):
        markup = self.lbl_markup("Current Selected Driver", self.toggled_driver)
        self.ui_cur_sel_drv_lbl.set_markup(markup)

    def on_root_permission_changed(self, permission, blank):
        permission = self.ui_apply_chg_button.get_permission()
        try:
            if permission:
                allowed = permission.get_allowed()
                if allowed:
                    cur_path = os.path.dirname(os.path.abspath(__file__))
                    pkg_file = "/package.py"
                    params = [
                        "/usr/bin/pkexec",
                        cur_path + pkg_file,
                        self.toggled_driver,
                    ]
                    if self.toggled_driver == "nvidia":
                        params.append(drivers[self.nvidia_device["driver"]])

                    res = self.start_prc(
                        params, self.ui_status_progressbar, self.ui_confirm_dialog
                    )
                    self.ui_apply_chg_button.set_sensitive(False)

        except GLib.GError:
            print("now allowed")

    def start_prc(self, params, ui_obj=None, dlg=None):
        pid, std_in, std_out, std_err = GLib.spawn_async(
            params,
            flags=GLib.SpawnFlags.DO_NOT_REAP_CHILD,
            standard_output=True,
            standard_error=True,
        )

        GLib.io_add_watch(
            GLib.IOChannel(std_out),
            GLib.IO_IN | GLib.IO_HUP,
            std_opr.on_process_stdout,
            ui_obj,
            params[-1],
        )
        pid = GLib.child_watch_add(
            GLib.PRIORITY_DEFAULT, pid, std_opr.on_process_stdext, ui_obj, dlg
        )

        return pid
