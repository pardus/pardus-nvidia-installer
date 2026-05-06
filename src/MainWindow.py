import gi
import os
import signal
import subprocess
import nvidia
import locale
import platform
import package

gi.require_version("Gtk", "3.0")
gi.require_version("Polkit", "1.0")
gi.require_version('Vte', '2.91')

from gi.repository import Gtk, GObject, GLib, Vte
from locale import gettext as _

APPNAME_CODE = "pardus-nvidia-installer"
TRANSLATIONS_PATH = "/usr/share/locale/"
locale.bindtextdomain(APPNAME_CODE, TRANSLATIONS_PATH)
locale.textdomain(APPNAME_CODE)

is_debug = os.path.isfile("/etc/pardus-nvi.debug")

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
        self.application = application


        self.get_ui("ui_button_reboot_dlg").connect("clicked", self.do_reboot)
        self.get_ui("ui_button_exit_dlg").connect("clicked",
            lambda x: exit(0))

        if os.path.isfile("/run/pardus-nvi.reboot"):
            self.ui_main_window = self.get_ui("ui_window_reboot")
            self.ui_main_window.set_application(application)
            self.ui_main_window.show_all()
            return


        self.driver_buttons = []
        self.active_driver = ""
        self.toggled_driver = ""
        self.drv_arr = []
        self.initial_gpu_driver = ""
        self.initial_sec_gpu_state = False
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
        self.ui_disable_check_button = self.get_ui("ui_disable_check_button")

        self.ui_apply_chg_button.connect("clicked", self.on_apply_button_clicked)
        self.ui_repo_switch = self.get_ui("ui_repo_switch")
        self.ui_repo_switch.set_state(self.state)
        self.ui_repo_switch.connect("state-set", self.on_nvidia_mirror_changed)

        self.ui_about_dialog = self.get_ui("ui_about_dialog")
        self.ui_about_button = self.get_ui("ui_about_button")

        self.ui_info_dialog = self.get_ui("ui_info_dialog")

        self.ui_about_button.connect("clicked", self.on_about_button_clicked)

        self.nvidia_devices = nvidia.graphics()
        self.ui_controller_box = self.get_ui("ui_controller_box")
        self.ui_secondary_gpu_box = self.get_ui("ui_secondary_gpu_box")

        self.ui_main_stack = self.get_ui("ui_main_stack")
        self.ui_nvidia_box = self.get_ui("ui_nvidia_box")
        self.ui_novidia_box = self.get_ui("ui_novidia_box")
        self.ui_disable_check_button.connect(
            "clicked", self.on_disable_checkbox_checked
        )
        self.ui_enable_button = self.get_ui("ui_enable_button")
        self.ui_enable_button.connect("clicked", self.on_enable_button_clicked)

        self.check_secondary_gpu()

        self.apt_opr = ""
        self.create_gpu_drivers()

        self.vte = Vte.Terminal()
        self.update_vte_color(self.vte)
        self.ui_box_vte = self.get_ui("ui_box_vte")
        vte_scrolled = Gtk.ScrolledWindow()
        vte_scrolled.add(self.vte)
        self.ui_box_vte.pack_start(vte_scrolled, True, True, 0)
        self.vte.connect("child-exited", self.on_vte_done)


        self.get_ui("ui_button_reboot").connect("clicked", self.do_reboot)
        self.get_ui("ui_button_exit").connect("clicked",
            lambda x: exit(0))

        self.op_widgets = (
            self.ui_apply_chg_button,
            self.ui_repo_switch,
            self.ui_enable_button,
            self.ui_disable_check_button,
        )

        self.ui_main_window.set_application(application)
        self.ui_main_window.set_title(_("Pardus Nvidia Installer"))
        self.user_disclaimer()
        self.ui_main_window.show_all()


        #self.vte_start(["/bin/bash"])

    def do_reboot(self, widget):
        cmd=[
            "/usr/bin/dbus-send", "--system", "--print-reply",
            "--dest=org.freedesktop.login1", "/org/freedesktop/login1",
            "org.freedesktop.login1.Manager.Reboot", "boolean:true"]
        print(cmd)
        subprocess.run(cmd)


    def on_vte_done(self, vte, status):
        self.get_ui("ui_box_vte_buttons").show_all()
        success = (status == 0)
        reboot_pending = os.path.isfile("/run/pardus-nvi.reboot")
        self.get_ui("ui_button_reboot").set_sensitive(success and reboot_pending)

        for w in self.op_widgets:
            w.set_sensitive(True)
        if success:
            self.ui_apply_chg_button.set_sensitive(False)
        else:
            self.ui_apply_chg_button.set_sensitive(self.check_initials())

        status_label = self.get_ui("ui_vte_status_label")
        if status_label is not None:
            if success:
                markup = '<span foreground="mediumspringgreen">{}</span>'.format(
                    _("Operation completed successfully.")
                )
            else:
                markup = '<span foreground="tomato">{}</span>'.format(
                    _("Operation failed (exit code {code}). Please review the log above.").format(code=status)
                )
            status_label.set_markup(markup)

    def update_vte_color(self, vte):
        style_context = self.ui_main_window.get_style_context()
        background_color= style_context.get_background_color(Gtk.StateFlags.NORMAL);
        foreground_color= style_context.get_color(Gtk.StateFlags.NORMAL);
        vte.set_color_background(background_color)
        vte.set_color_foreground(foreground_color)


    def vte_start(self, params):
        for w in self.op_widgets:
            w.set_sensitive(False)
        self.get_ui("ui_box_vte_buttons").hide()
        self.get_ui("ui_vte_status_label").set_text("")
        self.ui_main_stack.set_visible_child_name("page_vte")
        print(params)
        self.vte.spawn_async(
                Vte.PtyFlags.DEFAULT,
                os.environ['HOME'],
                params,
                None,
                GLib.SpawnFlags.DO_NOT_REAP_CHILD,
                None,
                None,
                -1,
                None,
                None,
                None
            )

    def user_disclaimer(self):
        response = self.ui_info_dialog.run()
        if response != Gtk.ResponseType.OK:
            self.application.quit()
        else:
            self.ui_info_dialog.close()

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
        if len(self.nvidia_devices) == 0 and not is_debug:
            self.ui_main_stack.set_visible_child(self.ui_novidia_box)
        for toggle in self.drv_arr:
            self.ui_gpu_box.remove(toggle)
        self.drv_arr = []
        for nvidia_device in self.nvidia_devices:
            gpu_info = self.gpu_box(nvidia_device.device_name)
            self.ui_gpu_info_box.pack_start(gpu_info, True, True, 5)

        self.nvidia_drivers = nvidia.drivers(gpus=self.nvidia_devices)
        self.filtered_nvidia_drivers = []
        for index, nvidia_driver in enumerate(self.nvidia_drivers):
            print(nvidia_driver)
            if index == 0:
                self.filtered_nvidia_drivers.append(nvidia_driver)
            else:
                if self.state:
                    if nvidia_driver.repo == "NVIDIA":
                        self.filtered_nvidia_drivers.append(nvidia_driver)
                else:
                    self.filtered_nvidia_drivers.append(nvidia_driver)

        self.nvidia_drivers = self.filtered_nvidia_drivers

        for index, nvidia_driver in enumerate(self.nvidia_drivers):
            toggle = self.driver_box(
                nvidia_driver.package,
                nvidia_driver.version,
                nvidia_driver.type,
                nvidia_driver.repo,
            )

            if nvidia_driver.installed:
                self.initial_gpu_driver = nvidia_driver
                self.toggled_driver = nvidia_driver
                self.ui_apply_chg_button.set_sensitive(True)
            toggle.set_active(nvidia_driver.installed)
            toggle.connect("toggled", self.on_drv_toggled, nvidia_driver)
            self.drv_arr.append(toggle)
            self.ui_gpu_box.pack_start(toggle, True, True, 5)
        self.ui_apply_chg_button.set_sensitive(self.check_initials())

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
        self.ui_apply_chg_button.set_sensitive(self.check_initials())

    def on_enable_button_clicked(self, button):
        params = ["/usr/bin/pkexec", cur_path + pkg_file, "enable-sec-gpu"]
        self.vte_start(params)

    def on_apply_button_clicked(self, button):
        print("apply button clicked")
        params = ["/usr/bin/pkexec", cur_path + pkg_file]
        self.apt_opr = None
        dlg_res = None
        disable_request = (
            self.initial_sec_gpu_state
            and self.ui_disable_check_button.get_active()
        )
        if disable_request:
            self.apt_opr = "disable-sec-gpu"
            params.append(self.apt_opr)
            self.vte_start(params)

        else:
            if self.toggled_driver.package == nouveau:
                self.apt_opr = "install-nouveau"
                params.append(self.apt_opr)
            else:
                self.apt_opr = "install-nvidia"
                params += [
                    self.apt_opr,
                    "linux-headers-{}".format(platform.uname().release), "linux-headers-amd64",
                    self.toggled_driver.package
                ]
            self.vte_start(params)

        # self.ui_apply_chg_button.set_sensitive(False)

    def on_about_button_clicked(self, button):
        self.ui_about_dialog.run()
        self.ui_about_dialog.hide()

    def check_initials(self):
        sec_gpu_changes = (
            self.initial_sec_gpu_state
            and self.ui_disable_check_button.get_active()
        )
        driver_changes = self.toggled_driver != self.initial_gpu_driver
        return sec_gpu_changes or driver_changes

    def on_disable_checkbox_checked(self, button):
        self.ui_apply_chg_button.set_sensitive(self.check_initials())

    def on_nvidia_mirror_changed(self, button, state):
        self.state = button.get_active()
        cur_path = os.path.dirname(os.path.abspath(__file__))
        params = ["/usr/bin/pkexec", cur_path + pkg_file, "update"]
        self.apt_opr = "update"
        self.vte_start(params)
