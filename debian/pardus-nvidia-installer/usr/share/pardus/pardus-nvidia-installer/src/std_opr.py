import os
import gi
import dbus
import subprocess

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gio, Gtk


def on_process_stdout(src, cond, prg_bar, last_param):
    if cond == GLib.IO_HUP:
        return False
    line = src.readline()
    print(line)
    # prog_txt = ""
    if "dlstatus" in line or "pmstatus" in line:
        splits = line.split(":")
        prc = float(splits[2])
        txt = splits[3]
        prg_frac = float(prc / 100)
        prog_txt = f"Status %{prc:.2f} :: {txt}"
        prg_bar.set_text(prog_txt)
        prg_bar.set_fraction(prg_frac)
    return True


def on_process_stderr(src, cond, ui_obj):
    if cond == GLib.IO_HUP:
        return False
    line = src.readline()
    return True


def on_process_stdext(pid, stat, ui_obj, dialog):
    ui_obj.set_fraction(1)
    if stat == 0:
        ui_obj.set_text("Selected driver installed successfully.")
        dlg_res = dialog.run()
        if dlg_res == Gtk.ResponseType.OK:
            subprocess.call(
                [
                    "dbus-send",
                    "--system",
                    "--print-reply",
                    "--dest=org.freedesktop.login1",
                    "/org/freedesktop/login1",
                    "org.freedesktop.login1.Manager.Reboot",
                    "boolean:true",
                ]
            )
        elif dlg_res == Gtk.ResponseType.CANCEL:
            pass
        dialog.destroy()
    else:
        ui_obj.set_text("An error occured during installation.")
        return False
