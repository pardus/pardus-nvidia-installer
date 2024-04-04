import gi
import os
import apt

import nvidia
import std_opr
import locale
import package

gi.require_version("Gtk", "3.0")
gi.require_version("Polkit", "1.0")


from gi.repository import Gtk, GObject, GLib
from locale import gettext as _

APPNAME_CODE = "pardus-nvidia-installer"
TRANSLATIONS_PATH = "/usr/share/locale/"
locale.bindtextdomain(APPNAME_CODE, TRANSLATIONS_PATH)
locale.textdomain(APPNAME_CODE)


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

cur_path = os.path.dirname(os.path.abspath(__file__))
pkg_file = "/package.py"


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
        self.toggled_driver = ""
        self.state = nvidia.source()
        self.ui_gpu_info_box = self.get_ui("ui_gpu_info_box")
        self.ui_gpu_box = self.get_ui("ui_gpu_box")
        self.ui_drv_box = self.get_ui("ui_drv_box")
        self.ui_main_box = self.get_ui("ui_main_box")
        self.ui_main_window = self.get_ui("ui_main_window")
        self.ui_confirm_dialog = self.get_ui("ui_confirm_dialog")

        self.ui_info_stack = self.get_ui("ui_info_stack")
        self.ui_disabled_gpu_box = self.get_ui("ui_disabled_gpu_box")
        self.ui_enabled_gpu_box = self.get_ui("ui_enabled_gpu_box")

        self.ui_apply_chg_button = self.get_ui("ui_apply_chg_button")

        
        self.ui_status_label = self.get_ui("ui_status_label")
        self.ui_status_progressbar = self.get_ui("ui_status_progressbar")
        self.ui_apply_chg_button.connect("clicked", self.on_apply_button_clicked)
        self.ui_repo_switch = self.get_ui("ui_repo_switch")
        self.ui_repo_switch.set_state(self.state)
        self.ui_repo_switch.connect("state-set", self.on_nvidia_mirror_changed)
        # self.ui_pardus_src_button = self.get_ui("ui_pardus_src_button")
        # self.ui_pardus_src_button.connect("clicked", self.on_nvidia_mirror_changed)
        # self.ui_nvidia_src_button = self.get_ui("ui_nvidia_src_button")
        # self.ui_nvidia_src_button.connect("clicked", self.on_nvidia_mirror_changed)
        self.ui_about_dialog = self.get_ui("ui_about_dialog")
        self.ui_about_button = self.get_ui("ui_about_button")
        self.ui_downgrade_dialog = self.get_ui("ui_downgrade_dialog")
        self.ui_upgrade_dialog = self.get_ui("ui_upgrade_dialog")
        self.ui_about_button.connect("clicked", self.on_about_button_clicked)

        self.nvidia_devices = nvidia.graphics()
        self.ui_controller_box = self.get_ui("ui_controller_box")
        self.ui_secondary_gpu_box = self.get_ui("ui_secondary_gpu_box")
        self.ui_disable_check_button = self.get_ui("ui_disable_check_button")
        self.ui_main_stack = self.get_ui("ui_main_stack")
        self.ui_nvidia_box = self.get_ui("ui_nvidia_box")
        self.ui_novidia_box = self.get_ui("ui_novidia_box")
        self.ui_disable_check_button.connect(
            "clicked", self.on_disable_checkbox_checked
        )
        self.ui_enable_button = self.get_ui("ui_enable_button")
        self.ui_enable_button.connect("clicked", self.on_enable_button_clicked)
        self.initial_sec_gpu_state = False
        self.initial_gpu_driver = ""
        self.check_secondary_gpu()
        self.drv_arr = []

        self.apt_opr = ""
        self.create_gpu_drivers()

        self.ui_main_window.set_application(application)
        self.ui_main_window.set_title(_("Pardus Nvidia Installer"))

        self.ui_main_window.show_all()

        # self.ui_nvidia_src_button.set_sensitive(not state)
        # self.ui_pardus_src_button.set_sensitive(state)

    def check_secondary_gpu(self):
        self.initial_sec_gpu_state = package.check_sec_state()
        if self.initial_sec_gpu_state:
            self.ui_info_stack.set_visible_child(self.ui_enabled_gpu_box)
        else:
            self.ui_info_stack.set_visible_child(self.ui_disabled_gpu_box)

        for dev in self.nvidia_devices:
            if not dev.is_secondary_gpu:
                self.ui_controller_box.remove(self.ui_disable_check_button)
                break

    def create_gpu_drivers(self):
        if len(self.nvidia_devices) == 0:
            self.ui_main_stack.set_visible_child(self.ui_novidia_box)
        for toggle in self.drv_arr:

            self.ui_gpu_box.remove(toggle)
        self.drv_arr = []
        for nvidia_device in self.nvidia_devices:
            gpu_info = self.gpu_box(nvidia_device.device_name)
            self.ui_gpu_info_box.pack_start(gpu_info, True, True, 5)

        self.nvidia_drivers = nvidia.drivers()
        for index, nvidia_driver in enumerate(self.nvidia_drivers):
            toggle = self.driver_box(
                nvidia_driver.package,
                nvidia_driver.version,
                nvidia_driver.type,
                nvidia_driver.repo,
            )

            drv_state = nvidia.is_pkg_installed(
                nvidia_driver.package, nvidia_driver.version
            )
            if drv_state:
                self.initial_gpu_driver = nvidia_driver
                self.toggled_driver = nvidia_driver
                self.ui_apply_chg_button.set_sensitive(True)
            toggle.set_active(drv_state)
            toggle.connect("toggled", self.on_drv_toggled, nvidia_driver)
            self.drv_arr.append(toggle)
            self.ui_gpu_box.pack_start(toggle, True, True, 5)

    def get_ui(self, object_name: str):
        return self.gtk_builder.get_object(object_name)

    def driver_box(self, drv_name, drv_ver, drv_type, drv_repo):
        b = Gtk.Builder.new_from_file(
            os.path.dirname(__file__) + "/../ui/driver_toggle.glade"
        )
        btn = b.get_object("ui_radio_button")

        btn.set_name(drv_name)

        name = b.get_object("ui_name_label")
        markup = self.lbl_markup(_("Driver"), drv_name)
        if drv_name == nouveau:
            markup = self.lbl_markup(_("Driver"), drv_name)
        name.set_markup(markup)

        ver = b.get_object("ui_version_label")
        markup = self.lbl_markup(_("Version"), drv_ver)
        ver.set_markup(markup)

        markup = self.lbl_markup(_("Description"), drv_type, color="dodgerblue")
        if drv_name == nouveau:
            markup = self.lbl_markup(
                _("Description"), drv_type, color="mediumspringgreen"
            )
        lbl = b.get_object("ui_driver_label")
        lbl.set_markup(markup)

        repo = b.get_object("ui_repo_label")
        markup = self.lbl_markup("Repo", drv_repo)
        repo.set_markup(markup)

        grp = None
        if len(self.driver_buttons) > 0:
            grp = self.driver_buttons[0]
        btn.join_group(grp)
        self.driver_buttons.append(btn)
        return btn

    def gpu_box(self, device_name):
        box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 13)

        name_label = Gtk.Label(xalign=0)
        name_label.set_markup(f"<b>{device_name}</b>")

        box.pack_start(name_label, True, True, 0)
        return box

    def lbl_markup(self, label, desc, color=None):
        if color:
            return f'<span> <b>{label}: </b> <span foreground="{color}">{desc}</span> </span>'
        else:
            return f"<span> <b>{label}: </b> <span>{desc}</span> </span>"

    def on_drv_toggled(self, radio_button, driver):
        if radio_button.get_active():
            self.toggled_driver = driver
           # self.ui_apply_chg_button.set_sensitive(self.check_initials())

    def on_enable_button_clicked(self, button):
        params = ["/usr/bin/pkexec", cur_path + pkg_file, "enable-sec-gpu"]
        std_opr.start_prc(self, params)

    def on_apply_button_clicked(self, button):
        print("apply button clicked")
        params = ["/usr/bin/pkexec", cur_path + pkg_file]
        self.apt_opr = None
        dlg_res = None
        
        if self.initial_sec_gpu_state == self.ui_disable_check_button.get_active():
            self.apt_opr = "disable-sec-gpu"
        if self.apt_opr != 'disable-sec-gpu' and self.toggled_driver.package != nouveau:

            if self.initial_gpu_driver.repo == 'pardus' and self.toggled_driver == 'nvidia':
                dlg_res = self.ui_upgrade_dialog.run()
            else:
                dlg_res = self.ui_downgrade_dialog.run()

            self.ui_downgrade_dialog.close()
            self.ui_upgrade_dialog.close()
            if dlg_res == Gtk.ResponseType.OK:
                params.append(self.toggled_driver.package)

        if len(params) != 2:
            std_opr.start_prc(self, params)
        #self.ui_apply_chg_button.set_sensitive(False)

    def on_about_button_clicked(self, button):
        self.ui_about_dialog.run()

    def check_initials(self):
        sec_gpu_changes = False
        if self.ui_disable_check_button.get_active() == self.initial_sec_gpu_state:
            sec_gpu_changes = True
        driver_changes = False
        if self.toggled_driver != self.initial_gpu_driver:
            driver_changes = True
        return sec_gpu_changes or driver_changes

    def on_disable_checkbox_checked(self, button):
        pass
        #self.ui_apply_chg_button.set_sensitive(self.check_initials())

    def on_nvidia_mirror_changed(self, button, state):
        cur_path = os.path.dirname(os.path.abspath(__file__))
        params = ["/usr/bin/pkexec", cur_path + pkg_file, "update"]
        self.apt_opr = "update"
        std_opr.start_prc(self, params)
