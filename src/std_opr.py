import gi
from gi.repository import GLib, Gio


def on_process_stdout(src, cond, prg_bar):
    if cond == GLib.IO_HUP:
        return False
    line = src.readline()
    if "dlstatus" in line:
        prc = float(line.split(":")[2])
        prg_txt = f"Status:: Downloading packages... %{prc:.2f}"
        print(prg_txt)
        prg_bar.set_text(prg_txt)
        prg_frac = float(prc / 100)
        prg_bar.set_fraction(prg_frac)
    if "pmstatus" in line:
        splits = line.split(":")
        pkg = splits[1]
        prc = float(splits[2])
        prg_frac = float(prc / 100)
        prg_txt = f"Status:: Installing package...( {pkg} ) %{prc:.2f}"
        print(prg_txt)
        prg_bar.set_text(prg_txt)
        prg_bar.set_fraction(prg_frac)
    return True


def on_process_stderr(src, cond, ui_obj):
    if cond == GLib.IO_HUP:
        return False
    line = src.readline()
    return True


def on_process_stdext(pid, stat, ui_obj):
    ui_obj.set_fraction(1)
    if stat == 0:
        ui_obj.set_text("Selected driver installed successfully.")

    else:
        ui_obj.set_text("An error occured during installation.")
    return True
