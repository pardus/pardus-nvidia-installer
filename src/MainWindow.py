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
nouveau = "xserver-xorg-video-nouveau"
driver_packages = {
    "nouveau": "xserver-xorg-video-nouveau",
    "current": "nvidia-driver",
    470: "nvidia-tesla-470-driver",
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

        self.driver_buttons = []
        self.active_driver = ""
        self.ui_gpu_info_box = self.get_ui("ui_gpu_info_box")
        self.ui_gpu_box = self.get_ui("ui_gpu_box")
        self.ui_drv_box = self.get_ui("ui_drv_box")
        self.ui_main_box = self.get_ui("ui_main_box")
        self.ui_main_window = self.get_ui("ui_main_window")
        self.ui_confirm_dialog = self.get_ui("ui_confirm_dialog")

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

        self.nvidia_devices = nvidia.find_device()
        for index, dev in enumerate(self.nvidia_devices):
            name = dev["device"]
            pci = dev["pci"]
            driver = dev["driver"]
            cur_driver = dev["cur_driver"]
            driver_info = package.get_pkg_info(driver)
            drv_in_use = dev["drv_in_use"]

            toggle = self.driver_box(driver, driver_info["name"], driver_info["ver"])

            if drv_in_use:
                cur_driver_ver = dev["cur_driver_ver"]
                info = self.gpu_box(name, pci, cur_driver_ver)
                self.ui_gpu_info_box.pack_start(info, True, True, 5)
                toggle = self.driver_box(
                    driver, driver_info["name"], driver_info["ver"], True
                )
            toggle.connect("toggled", self.on_drv_toggled, driver)
            active = cur_driver == driver
            toggle.set_active(active)
            if active:
                self.active_driver = driver

            self.ui_gpu_box.pack_start(toggle, True, True, 5)
        self.ui_apply_chg_button.set_permission(prem)

        self.ui_main_window.set_application(application)
        self.ui_main_window.set_title("Pardus Nvidia Installer")

        self.ui_main_window.show_all()

    def get_ui(self, object_name: str):
        return self.gtk_builder.get_object(object_name)

    def driver_box(self, drv, drv_name, drv_ver, recommended=False):
        b = Gtk.Builder.new_from_file(
            os.path.dirname(__file__) + "/../ui/driver_toggle.glade"
        )
        btn = b.get_object("ui_radio_button")

        btn.set_name(drv)

        name = b.get_object("ui_name_label")
        markup = self.lbl_markup("Driver", drv_name)
        if recommended:
            markup = self.lbl_markup("Driver", drv_name + "<b> (Recommended)</b>")
        name.set_markup(markup)

        ver = b.get_object("ui_version_label")
        markup = self.lbl_markup("Version", drv_ver)
        ver.set_markup(markup)

        markup = self.lbl_markup("Description", "Proprietary", color="dodgerblue")
        if drv == nouveau:
            markup = self.lbl_markup(
                "Description", "Open Source Driver", color="mediumspringgreen"
            )
        lbl = b.get_object("ui_driver_label")
        lbl.set_markup(markup)
        grp = None
        if len(self.driver_buttons) > 0:
            grp = self.driver_buttons[0]
        btn.join_group(grp)
        self.driver_buttons.append(btn)
        return btn

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
        if radio_button.get_active():
            self.ui_apply_chg_button.set_sensitive(not self.active_driver == name)
            self.toggled_driver = name
            print(self.toggled_driver)

    def is_drv_in_use(self, driver: str):
        return self.active_driver == driver

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
