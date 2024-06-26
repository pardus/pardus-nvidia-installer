#!/usr/bin/env python3
import gi
import sys

from MainWindow import MainWindow

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio, GLib


class Application(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            application_id="tr.org.pardus.pardus-nvidia-installer",
            flags=Gio.ApplicationFlags(8),
            **kwargs
        )
        self.window = None

        self.add_main_option(
            "details",
            ord("d"),
            GLib.OptionFlags(0),
            GLib.OptionArg(1),
            "Details page of application",
            None,
        )

        self.add_main_option(
            "remove",
            ord("r"),
            GLib.OptionFlags(0),
            GLib.OptionArg(1),
            "Remove page of application",
            None,
        )

    def do_activate(self):
        if not self.window:
            self.window = MainWindow(self)
        else:
            self.window.controlArgs()
        self.window.ui_main_window.present()

    def do_command_line(self, command_line):
        options = command_line.get_options_dict()
        options = options.end().unpack()
        self.args = options
        self.activate()
        return 0


app = Application()
app.run(sys.argv)
