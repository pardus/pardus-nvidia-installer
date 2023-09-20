import gi
import os
import apt
import yaml
import nvidia
import package
import subprocess
import socket


gi.require_version("Gtk", "3.0")
gi.require_version("Polkit", "1.0")

from process_std import std
from gi.repository import Gtk, GObject, Polkit, GLib


cache = apt.Cache()
act_id = "tr.org.pardus.pkexec.pardus-nvidia-installer"
socket_path = "/tmp/pardus-nvidia-installer"
drivers = {"current": "nvidia-driver", "470": "nvidia-tesla-470-driver"}


class MainWindow(object):
    def __init__(self, application):
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

        self.ui_cancel_btn = self.getUI("ui_cancel_button")
        self.ui_apply_chg_button = self.getUI("ui_apply_chg_button")
        self.ui_status_label = self.getUI("ui_status_label")
        self.ui_status_progressbar = self.getUI("ui_status_progressbar")

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
            dev_info_box = self.gpu_box(name, pci, cur_drv)
            self.ui_gpu_box.pack_start(dev_info_box, True, True, 5)
        self.ui_gpu_box.show_all()

        self.os_drv_pkg = "xserver-xorg-video-nouveau"
        self.pkg_os_info = package.get_pkg_info(self.os_drv_pkg)
        self.pkg_nv_info = package.get_pkg_info(drivers[self.nvidia_device["driver"]])

        markup = self.lbl_markup(
            "Selected Driver", self.nvidia_device["cur_driver"] + " (Currently In Use) "
        )
        self.ui_cur_sel_drv_lbl.set_markup(markup)

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

    def getUI(self, object_name: str):
        return self.gtk_builder.get_object(object_name)

    def gpu_box(self, name: str, pci: str, cur_drv: str):
        box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 13)
        vendor_markup = self.lbl_markup("Device Vendor", "Nvidia Corporation")
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
            markup_desc = name
            drv_in_use = self.is_drv_in_use(name)
            self.ui_apply_btn.set_sensitive(not drv_in_use)
            if drv_in_use:
                markup_desc = name + " (Currently In Use) "
            markup = self.lbl_markup("Selected Driver", markup_desc)
            self.ui_cur_sel_drv_lbl.set_markup(markup)
            print(self.is_drv_in_use(name))

    def is_drv_in_use(self, driver: str):
        return self.nvidia_device["cur_driver"] == driver

    def on_root_permission_changed(self, permission, blank):
        permission = self.ui_apply_chg_button.get_permission()
        try:
            if permission:
                allowed = permission.get_allowed()
                if allowed:
                    cur_path = os.path.dirname(os.path.abspath(__file__))
                    pkg_file = "/package.py"
                    print(cur_path + pkg_file)
                    params = [
                        "/usr/bin/pkexec",
                        cur_path + pkg_file,
                        "install",
                        "android-studio",
                    ]
                    self.start_prc(params, 1)
        except GLib.GError:
            print("now allowed")

    def on_process_stdout(self, src, cond):
        if cond == GLib.IO_HUP:
            return False
        line = src.readline()
        print(line)
        if "dlstatus" in line:
            prc = float(line.split(":")[2])
            prg_txt = f"Status:: Downloading packages..."
            self.ui_status_progressbar.set_text(prg_txt)
            prg_frac = float(prc / 200.00)
            print("frac: ", prg_frac)
            self.ui_status_progressbar.set_fraction(prg_frac)

        if "pmstatus" in line:
            splits = line.split(":")
            pkg = splits[1]
            prc = float(splits[2])
            prg_frac = float(0.5 + (prc / 200))
            print("frac: ", prg_frac)

            prg_txt = f"Status:: Installing package...( {pkg} )"
            self.ui_status_progressbar.set_text(prg_txt)
            self.ui_status_progressbar.set_fraction(prg_frac)

        return True

    def on_process_stderr(self, src, cond):
        if cond == GLib.IO_HUP:
            return False
        line = src.readline()
        print("mw err: ", line)
        return True

    def on_process_stdext(self, pid, stat):
        if stat == 0:
            self.ui_status_progressbar.set_text(
                "Selected driver installed successfully."
            )
            self.ui_status_progressbar.set_fraction(1)
        else:
            self.ui_status_progressbar.set_text("An error occured during installation.")
            self.ui_status_progressbar.set_fraction(1)
        return True

    def start_prc(self, params, fd):
        pid, std_in, std_out, std_err = GLib.spawn_async(
            params + [str(fd)],
            flags=GLib.SpawnFlags.DO_NOT_REAP_CHILD,
            standard_output=True,
            standard_error=True,
        )
        print("mw pid:", pid)
        print("mw stdout: ", std_out)
        print("mw stdout type: ", type(std_out))
        if fd == 1:
            GLib.io_add_watch(
                GLib.IOChannel(std_out),
                GLib.IO_IN | GLib.IO_HUP,
                self.on_process_stdout,
            )
        elif fd == 2:
            GLib.io_add_watch(
                GLib.IOChannel(std_err),
                GLib.IO_IN | GLib.IO_HUP,
                self.on_process_stderr,
            )
        GLib.child_watch_add(GLib.PRIORITY_DEFAULT, pid, self.on_process_stdext)
        return pid
